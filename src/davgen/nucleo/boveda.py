"""boveda.py — accesos cifrados dentro del proyecto.

`_acceso.<entorno>.cifrado` guarda el mismo texto que `_acceso.<entorno>.ini`,
cifrado. Se abre con el TOKEN del proyecto; opcionalmente también con una
LLAVE MAESTRA de recuperación, para cuando el token se pierde.

Esquema («sobre» con dos cerraduras), solo con construcciones estándar:

    contenido ──AES-256-GCM──► datos            (clave de datos: 32 bytes al azar)
    clave de datos ──AES-256-GCM──► ranura «token»    (clave = scrypt(token, sal))
    clave de datos ──AES-256-GCM──► ranura «maestra»  (clave = scrypt(llave, sal))   [opcional]

Cambiar el token no vuelve a cifrar el contenido: solo rehace su ranura. Por
eso con la llave maestra se puede poner un token nuevo sin conocer el anterior.

Formato del archivo (texto, apto para git):

    davgen-acceso v1
    entorno: produccion
    kdf: scrypt n=32768 r=8 p=1
    token: <sal>.<nonce>.<clave de datos cifrada>
    maestra: <sal>.<nonce>.<clave de datos cifrada>        (si hay llave maestra)
    datos: <nonce>.<contenido cifrado>

GCM autentica: un token incorrecto y un archivo alterado dan el mismo error.
El nombre del entorno y la cabecera van como datos asociados, así que un
archivo de desarrollo no se puede hacer pasar por el de producción.

Lo que NO hace: no protege un token débil, no borra de forma segura el `.ini`
que se cifra (el sistema de archivos puede conservar restos) y no cifra el
`.env` de Laravel, que necesita la contraseña de la base en claro.
"""
import base64
import hashlib
import os
import secrets
from typing import Dict, Optional, Tuple

CABECERA = 'davgen-acceso v1'
EXTENSION = '.cifrado'
LARGO_MINIMO_TOKEN = 12

# Parámetros de scrypt. ~32 MB y unas décimas de segundo por intento: barato
# para quien conoce el token, caro para quien prueba millones.
N, R, P = 2 ** 15, 8, 1

VARIABLE_TOKEN = 'DAVGEN_TOKEN'
VARIABLE_MAESTRA = 'DAVGEN_LLAVE_MAESTRA'


class ErrorBoveda(Exception):
    """No se pudo abrir o escribir un archivo de accesos cifrado."""


class FaltaToken(ErrorBoveda):
    """El archivo está cifrado y no hay token (ni terminal donde pedirlo)."""


class TokenIncorrecto(ErrorBoveda):
    """Token/llave incorrectos o archivo dañado (GCM no los distingue)."""


def _aesgcm(clave: bytes):
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as e:                           # pragma: no cover
        raise ErrorBoveda("Falta la librería de cifrado: pip install cryptography") from e
    return AESGCM(clave)


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode('ascii')


def _de_b64(s: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(s.encode('ascii'))
    except Exception as e:                             # noqa: BLE001
        raise TokenIncorrecto('archivo dañado') from e


def _derivar(secreto: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(secreto.strip().encode('utf-8'), salt=sal, n=n, r=r, p=p,
                          dklen=32, maxmem=2 ** 27)


def validar_token(token: str) -> str:
    """'' si el token sirve; si no, el motivo."""
    token = (token or '').strip()
    if len(token) < LARGO_MINIMO_TOKEN:
        return f'el token debe tener al menos {LARGO_MINIMO_TOKEN} caracteres'
    if len(set(token)) < 6:
        return 'el token es demasiado repetitivo'
    return ''


def nueva_llave_maestra() -> str:
    """Llave de recuperación aleatoria (160 bits), en grupos fáciles de copiar:
    ABCDE-FGHIJ-…  Se muestra UNA vez; davgen no la guarda en ningún lado."""
    crudo = base64.b32encode(secrets.token_bytes(20)).decode('ascii')
    return '-'.join(crudo[i:i + 4] for i in range(0, len(crudo), 4))


def _normalizar_llave(llave: str) -> str:
    return (llave or '').replace('-', '').replace(' ', '').upper()


def _asociados(entorno: str) -> bytes:
    return f'{CABECERA}|{entorno}'.encode('utf-8')


def _ranura(secreto: str, clave_datos: bytes, entorno: str, etiqueta: str) -> str:
    sal, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    kek = _derivar(secreto, sal, N, R, P)
    cifrada = _aesgcm(kek).encrypt(nonce, clave_datos, _asociados(entorno) + etiqueta.encode())
    return '.'.join(_b64(x) for x in (sal, nonce, cifrada))


def _abrir_ranura(texto_ranura: str, secreto: str, entorno: str, etiqueta: str,
                  kdf: Tuple[int, int, int]) -> bytes:
    try:
        sal, nonce, cifrada = (_de_b64(x) for x in texto_ranura.split('.'))
        kek = _derivar(secreto, sal, *kdf)
        return _aesgcm(kek).decrypt(nonce, cifrada, _asociados(entorno) + etiqueta.encode())
    except TokenIncorrecto:
        raise
    except Exception as e:                             # noqa: BLE001  (InvalidTag, ValueError…)
        raise TokenIncorrecto('token incorrecto o archivo dañado') from e


def _leer_campos(texto: str) -> Dict[str, str]:
    lineas = [x.strip() for x in texto.replace('\r\n', '\n').split('\n') if x.strip()]
    if not lineas or lineas[0] != CABECERA:
        raise ErrorBoveda('no es un archivo de accesos de davgen (o es de una versión '
                          'más nueva: actualizar davgen)')
    campos = {}
    for linea in lineas[1:]:
        clave, _, valor = linea.partition(':')
        campos[clave.strip()] = valor.strip()
    for requerido in ('entorno', 'kdf', 'token', 'datos'):
        if requerido not in campos:
            raise TokenIncorrecto('archivo dañado')
    return campos


def _kdf(campos: Dict[str, str]) -> Tuple[int, int, int]:
    try:
        partes = dict(x.split('=') for x in campos['kdf'].split()[1:])
        n, r, p = int(partes['n']), int(partes['r']), int(partes['p'])
    except Exception as e:                             # noqa: BLE001
        raise TokenIncorrecto('archivo dañado') from e
    if not (2 ** 10 <= n <= 2 ** 20 and 1 <= r <= 32 and 1 <= p <= 16):
        raise TokenIncorrecto('archivo dañado')        # parámetros absurdos: no gastar memoria
    return n, r, p


def _armar(entorno: str, ranura_token: str, ranura_maestra: str, datos: str) -> str:
    lineas = [CABECERA, f'entorno: {entorno}', f'kdf: scrypt n={N} r={R} p={P}',
              f'token: {ranura_token}']
    if ranura_maestra:
        lineas.append(f'maestra: {ranura_maestra}')
    lineas.append(f'datos: {datos}')
    return '\n'.join(lineas) + '\n'


def cifrar(contenido: str, entorno: str, token: str, llave_maestra: str = '') -> str:
    """Texto del archivo cifrado para `contenido`."""
    motivo = validar_token(token)
    if motivo:
        raise ErrorBoveda(motivo)
    clave_datos = secrets.token_bytes(32)
    return _sellar(contenido, entorno, clave_datos,
                   _ranura(token, clave_datos, entorno, 'token'),
                   _ranura(_normalizar_llave(llave_maestra), clave_datos, entorno, 'maestra')
                   if llave_maestra else '')


def _sellar(contenido: str, entorno: str, clave_datos: bytes, ranura_token: str,
            ranura_maestra: str) -> str:
    nonce = secrets.token_bytes(12)
    cifrado = _aesgcm(clave_datos).encrypt(nonce, contenido.encode('utf-8'),
                                           _asociados(entorno) + b'datos')
    return _armar(entorno, ranura_token, ranura_maestra, f'{_b64(nonce)}.{_b64(cifrado)}')


def _clave_de_datos(campos: Dict[str, str], token: str = '', llave_maestra: str = '') -> bytes:
    entorno, kdf = campos['entorno'], _kdf(campos)
    if llave_maestra:
        if 'maestra' not in campos:
            raise ErrorBoveda('este archivo se cifró SIN llave maestra')
        return _abrir_ranura(campos['maestra'], _normalizar_llave(llave_maestra),
                             entorno, 'maestra', kdf)
    return _abrir_ranura(campos['token'], token, entorno, 'token', kdf)


def descifrar(texto: str, token: str = '', llave_maestra: str = '') -> str:
    """Contenido original. Lanza TokenIncorrecto si el token (o la llave) no
    corresponden o el archivo fue alterado."""
    campos = _leer_campos(texto)
    clave_datos = _clave_de_datos(campos, token, llave_maestra)
    try:
        nonce, cifrado = (_de_b64(x) for x in campos['datos'].split('.'))
        return _aesgcm(clave_datos).decrypt(
            nonce, cifrado, _asociados(campos['entorno']) + b'datos').decode('utf-8')
    except TokenIncorrecto:
        raise
    except Exception as e:                             # noqa: BLE001
        raise TokenIncorrecto('token incorrecto o archivo dañado') from e


def reescribir(texto: str, contenido_nuevo: str, token: str) -> str:
    """Mismo archivo con otro contenido (p. ej. tras guardar un secreto nuevo).
    Conserva la clave de datos y las dos ranuras: la llave maestra sigue
    sirviendo sin tener que volver a pedirla."""
    campos = _leer_campos(texto)
    clave_datos = _clave_de_datos(campos, token)
    return _sellar(contenido_nuevo, campos['entorno'], clave_datos, campos['token'],
                   campos.get('maestra', ''))


def cambiar_token(texto: str, token_nuevo: str, token_actual: str = '',
                  llave_maestra: str = '') -> str:
    """Pone un token nuevo. Se autoriza con el token actual o, si se perdió,
    con la llave maestra. El contenido no se vuelve a cifrar."""
    motivo = validar_token(token_nuevo)
    if motivo:
        raise ErrorBoveda(motivo)
    campos = _leer_campos(texto)
    clave_datos = _clave_de_datos(campos, token_actual, llave_maestra)
    return _armar(campos['entorno'], _ranura(token_nuevo, clave_datos, campos['entorno'], 'token'),
                  campos.get('maestra', ''), campos['datos'])


def tiene_llave_maestra(texto: str) -> bool:
    return 'maestra' in _leer_campos(texto)


# ── token de la sesión ──────────────────────────────────────────────────────
_tokens: Dict[str, str] = {}          # raíz del proyecto → token ya validado
_claros: Dict[Tuple[str, float, str], str] = {}     # (ruta, mtime, token) → contenido


def olvidar() -> None:
    """Borra de la memoria tokens y contenidos descifrados (pruebas / fin)."""
    _tokens.clear()
    _claros.clear()


def recordar_token(raiz: str, token: str) -> None:
    _tokens[os.path.normcase(os.path.abspath(raiz))] = token


def token_de(raiz: str, pedir: bool = True) -> str:
    """Token del proyecto: variable DAVGEN_TOKEN, el ya ingresado en esta
    ejecución, o se pide por teclado (sin eco). Lanza FaltaToken si no hay."""
    token = os.environ.get(VARIABLE_TOKEN, '').strip()
    if token:
        return token
    clave = os.path.normcase(os.path.abspath(raiz))
    if clave in _tokens:
        return _tokens[clave]
    from .consola import es_interactiva
    if pedir and es_interactiva():
        import getpass
        token = getpass.getpass('  Token del proyecto (no se muestra): ').strip()
        if token:
            _tokens[clave] = token
            return token
    raise FaltaToken(
        'Los accesos de este proyecto están cifrados y falta el token. Ejecutar en '
        f'una terminal (lo pide) o definir la variable de entorno {VARIABLE_TOKEN}.')


def leer_archivo(ruta: str, raiz: str, token: Optional[str] = None) -> str:
    """Contenido en claro de un `.cifrado`, EN MEMORIA (nunca se escribe)."""
    token = token if token is not None else token_de(raiz)
    marca = (os.path.normcase(os.path.abspath(ruta)), os.path.getmtime(ruta), token)
    if marca not in _claros:
        with open(ruta, encoding='utf-8') as f:
            try:
                _claros[marca] = descifrar(f.read(), token)
            except TokenIncorrecto:
                _tokens.pop(os.path.normcase(os.path.abspath(raiz)), None)
                raise
    return _claros[marca]
