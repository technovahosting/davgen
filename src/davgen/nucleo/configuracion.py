"""
configuracion.py — _configtotal.ini del proyecto: plantilla, carga y validación.

Principios:
  - La configuración del proyecto vive en _configtotal.ini (sin contraseñas).
  - Los ACCESOS (base de datos, FTP, contraseña inicial del admin) van en dos
    archivos, uno por entorno: _acceso.desarrollo.ini y _acceso.produccion.ini.
    Lo que diga el archivo del entorno elegido se superpone a _configtotal.ini.
    Un proyecto de versiones anteriores, con todo en _configtotal.ini, sigue
    funcionando igual (se pasa a dos archivos con `davgen entornos`).
  - Solo rutas RELATIVAS a la carpeta del proyecto.
  - Parámetros mínimos: [proyecto] y [entrada]. El resto es opcional.
  - Si la config tiene errores, se listan TODOS con instrucciones y el
    generador se detiene pidiendo al usuario que complete el archivo.
  - Valores por defecto NEUTROS: el generador no trae cuentas, correos ni
    identificadores de nadie. Lo que sale del proyecto (BD, FTP, Google) solo
    se activa si el usuario lo configura.
"""
import configparser
import os
import re
import secrets
from typing import Dict, List, Tuple
from . import boveda
from .plantillas import cargar as _plantilla

# davgen NO trae ninguna contraseña de administrador: ni fija ni inventada. La
# escribe quien crea el proyecto ([seguridad] admin_password del archivo de
# accesos, o por teclado cuando davgen la pide) y debe cumplir esto:
ADMIN_PASSWORD_MINIMO = 8


def problema_admin_password(clave: str, admin_email: str = '') -> str:
    """Por qué `clave` no sirve como contraseña inicial del administrador, o ''
    si sirve. Reglas por FORMA: no hay lista de contraseñas en el código."""
    if len(clave) < ADMIN_PASSWORD_MINIMO:
        return f"mínimo {ADMIN_PASSWORD_MINIMO} caracteres"
    if not (any(c.isalpha() for c in clave) and any(c.isdigit() for c in clave)):
        return "debe combinar letras y números"
    if len(set(clave.lower())) < 5:
        return "repite demasiado los mismos caracteres"
    usuario = admin_email.split('@')[0].lower()
    if clave.lower() in (admin_email.lower(), usuario) or (
            len(usuario) >= 4 and clave.lower().startswith(usuario)
            and clave[len(usuario):].isdigit()):
        return "no puede ser el correo del administrador (ni el correo más números)"
    return ''

PLANTILLA = _plantilla('proyecto/configtotal.ini', __name__, 'PLANTILLA')

# flags de [generar] — los 3 primeros activos por defecto (si), el resto no
_FLAGS_GENERAR = ('aplicar_sps', 'produccion', 'front',
                  'form_requests', 'tests', 'componentes_react',
                  'ci', 'openapi', 'export')

# flags que tienen default 'si' cuando la clave no está en el INI
_FLAGS_GENERAR_DEFAULT_SI = frozenset(('aplicar_sps',))


def _es_si(texto: str) -> bool:
    return texto.strip().lower() in ('si', 'sí', 'yes', 'true', '1', 'x')

_RE_MODULO = re.compile(r'^[a-z]{2,6}$')


def generar_password(largo: int = 14) -> str:
    """Contraseña inicial aleatoria: letras y dígitos sin caracteres ambiguos
    (0/O, 1/l/I) para que se pueda copiar a mano sin errores."""
    alfabeto = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    while True:
        clave = ''.join(secrets.choice(alfabeto) for _ in range(largo))
        if (any(c.islower() for c in clave) and any(c.isupper() for c in clave)
                and any(c.isdigit() for c in clave)):
            return clave


ENTORNOS = ('desarrollo', 'produccion')
ENTORNO_DEFECTO = 'desarrollo'
PLANTILLA_ACCESO = _plantilla('proyecto/acceso.ini', __name__, 'PLANTILLA_ACCESO')

_AYUDA_ACCESO = {
    'desarrollo': {
        '__TITULO__': 'DESARROLLO (donde se programa y se prueba)',
        '__HOST__': '',
        '__AYUDA_BD__': 'Normalmente el MySQL de tu PC (XAMPP, Laragon, Docker…), que '
                        'debe estar iniciado: host = 127.0.0.1',
        '__AYUDA_FTP__': 'En desarrollo no se publica: dejar vacío.',
    },
    'produccion': {
        '__TITULO__': 'PRODUCCIÓN (el sitio publicado)',
        '__HOST__': '',
        '__AYUDA_BD__': 'La base del hosting. Si se accede desde tu PC, el hosting '
                        'debe permitir la conexión remota desde tu IP.',
        '__AYUDA_FTP__': 'FTP del hosting: adónde se sube el sistema con '
                         '--entorno produccion.',
    },
}


def nombre_acceso(entorno: str) -> str:
    return f'_acceso.{entorno}.ini'


def entorno_actual(entorno: str = '') -> str:
    """Entorno pedido, o el de la variable DAVGEN_ENTORNO, o desarrollo."""
    e = (entorno or os.environ.get('DAVGEN_ENTORNO', '') or ENTORNO_DEFECTO).strip().lower()
    return e if e in ENTORNOS else ENTORNO_DEFECTO


def nombre_cifrado(entorno: str) -> str:
    return f'_acceso.{entorno}{boveda.EXTENSION}'


def acceso_existente(carpeta_proyecto: str, entorno: str) -> Tuple[str, bool]:
    """(nombre del archivo de accesos del entorno, ¿está cifrado?), o ('', False)
    si no existe. Si conviven los dos, manda el `.ini` en claro (es el que se
    está editando); `davgen acceso` avisa de esa situación."""
    if os.path.isfile(os.path.join(carpeta_proyecto, nombre_acceso(entorno))):
        return nombre_acceso(entorno), False
    if os.path.isfile(os.path.join(carpeta_proyecto, nombre_cifrado(entorno))):
        return nombre_cifrado(entorno), True
    return '', False


def hay_entornos(carpeta_proyecto: str) -> bool:
    """True si el proyecto usa archivos de acceso por entorno (en claro o cifrados)."""
    return any(acceso_existente(carpeta_proyecto, e)[0] for e in ENTORNOS)


def nueva_plantilla(admin_password: str = '') -> str:
    """Texto del _configtotal.ini para un proyecto NUEVO (sin accesos)."""
    return PLANTILLA


def nueva_plantilla_acceso(entorno: str, admin_password: str = '') -> str:
    """Texto de _acceso.<entorno>.ini para un proyecto nuevo. La contraseña
    del administrador nace VACÍA: la escribe quien crea el proyecto."""
    texto = PLANTILLA_ACCESO.replace('__ENTORNO__', entorno)
    for marca, valor in _AYUDA_ACCESO[entorno].items():
        texto = texto.replace(marca, valor)
    return texto.replace('__ADMIN_PASSWORD__', admin_password)


def crear_accesos(carpeta_proyecto: str) -> List[str]:
    """Crea los archivos de acceso que falten. Devuelve los creados."""
    creados = []
    for entorno in ENTORNOS:
        ruta = os.path.join(carpeta_proyecto, nombre_acceso(entorno))
        if not acceso_existente(carpeta_proyecto, entorno)[0]:
            with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
                f.write(nueva_plantilla_acceso(entorno))
            creados.append(ruta)
    return creados


_CLAVES_SECRETAS = {('bd', 'password'), ('ftp', 'password'),
                    ('seguridad', 'admin_password')}


def fijar_en_texto(original: str, seccion: str, clave: str, valor: str) -> str:
    """`original` (texto de un .ini) con `clave = valor` en la sección dada, sin
    tocar nada más (comentarios, orden y finales de línea se conservan). Si la
    clave no existe se agrega al final de su sección; si la sección no existe,
    al final del texto."""
    salto = '\r\n' if '\r\n' in original else '\n'
    lineas = original.replace('\r\n', '\n').split('\n')
    seccion, clave = seccion.lower(), clave.lower()
    actual, fin_seccion, hecho = '', None, False
    for i, linea in enumerate(lineas):
        limpia = linea.strip()
        if limpia.startswith('[') and limpia.endswith(']'):
            actual = limpia[1:-1].strip().lower()
            continue
        if actual != seccion:
            continue
        if limpia:
            fin_seccion = i
        if limpia and limpia[0] not in ';#' and '=' in limpia \
                and limpia.split('=', 1)[0].strip().lower() == clave:
            lineas[i] = f"{clave} = {valor}"
            hecho = True
            break
    if not hecho:
        nueva = f"{clave} = {valor}"
        if fin_seccion is not None:
            lineas.insert(fin_seccion + 1, nueva)
        else:
            while lineas and not lineas[-1].strip():
                lineas.pop()
            lineas += ['', f"[{seccion}]", nueva, '']
    return salto.join(lineas)


def fijar_valor(carpeta_proyecto: str, seccion: str, clave: str, valor: str,
                archivo: str = '_configtotal.ini') -> None:
    """Escribe `clave = valor` en la sección dada de `archivo` (un .ini en
    claro). Para un secreto del entorno usar `guardar_secreto`, que también
    sabe escribir en un archivo cifrado."""
    ruta = os.path.join(carpeta_proyecto, archivo)
    with open(ruta, encoding='utf-8-sig', newline='') as f:
        original = f.read()
    with open(ruta, 'w', encoding='utf-8', newline='') as f:
        f.write(fijar_en_texto(original, seccion, clave, valor))


def guardar_secreto(carpeta_proyecto: str, seccion: str, clave: str, valor: str,
                    entorno: str = '') -> str:
    """Guarda un secreto donde corresponde para el entorno: su archivo de
    accesos (en claro o CIFRADO, que se vuelve a cifrar con el mismo token) o,
    en un proyecto sin entornos, _configtotal.ini. Devuelve el archivo usado."""
    nombre, cifrado = acceso_existente(carpeta_proyecto, entorno_actual(entorno))
    if not nombre:
        fijar_valor(carpeta_proyecto, seccion, clave, valor)
        return '_configtotal.ini'
    if not cifrado:
        fijar_valor(carpeta_proyecto, seccion, clave, valor, archivo=nombre)
        return nombre
    ruta = os.path.join(carpeta_proyecto, nombre)
    token = boveda.token_de(carpeta_proyecto)
    claro = boveda.leer_archivo(ruta, carpeta_proyecto, token)
    with open(ruta, encoding='utf-8') as f:
        sellado = f.read()
    with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
        f.write(boveda.reescribir(sellado, fijar_en_texto(claro, seccion, clave, valor), token))
    return nombre


def tiene_clave(carpeta_proyecto: str, seccion: str, clave: str,
                entorno: str = '') -> bool:
    """True si la clave tiene valor en _configtotal.ini o en el archivo de
    acceso del entorno."""
    ini = leer_ini(carpeta_proyecto, entorno)
    return ini.has_option(seccion, clave) and bool(ini.get(seccion, clave).strip())


def archivo_de_secretos(carpeta_proyecto: str, entorno: str = '') -> str:
    """Nombre del archivo donde vive un secreto del entorno: su archivo de
    accesos (en claro o cifrado) si el proyecto usa entornos, si no
    _configtotal.ini. Para ESCRIBIR, usar `guardar_secreto`."""
    return acceso_existente(carpeta_proyecto, entorno_actual(entorno))[0] or '_configtotal.ini'


# Además de las claves conocidas, se vacía cualquier clave que por su NOMBRE
# sea un secreto, en cualquier sección — también las que el proyecto agregue
# por su cuenta (p. ej. `[portal] token_reporte`). `google_client_id` no entra:
# es público por diseño.
_RE_CLAVE_SECRETA = re.compile(
    r'password|passwd|contrasen|secret|secreto|token|api_?key|clave_?(api|privada|secreta)')


def texto_ejemplo(texto_ini: str) -> str:
    """El mismo .ini SIN secretos, para versionarlo como _configtotal.ejemplo.ini.
    Conserva comentarios, orden y el resto de los valores."""
    seccion, salida = '', []
    for linea in texto_ini.splitlines():
        limpia = linea.strip()
        if limpia.startswith('[') and limpia.endswith(']'):
            seccion = limpia[1:-1].strip().lower()
        elif limpia and limpia[0] not in ';#' and '=' in limpia:
            clave = limpia.split('=', 1)[0].strip().lower()
            if (seccion, clave) in _CLAVES_SECRETAS or _RE_CLAVE_SECRETA.search(clave):
                linea = f"{clave} ="
        salida.append(linea)
    return '\n'.join(salida) + '\n'


def _escribir_un_ejemplo(origen: str, destino: str, contenido: str = None) -> bool:
    if contenido is None:
        with open(origen, encoding='utf-8-sig') as f:
            contenido = f.read()
    nuevo = texto_ejemplo(contenido)
    if os.path.isfile(destino):
        with open(destino, encoding='utf-8-sig') as f:
            if f.read() == nuevo:
                return False
    with open(destino, 'w', encoding='utf-8', newline='\n') as f:
        f.write(nuevo)
    return True


def _tiene_secretos(ruta: str) -> bool:
    with open(ruta, encoding='utf-8-sig') as f:
        texto = f.read()
    return texto_ejemplo(texto) != '\n'.join(texto.splitlines()) + '\n'


def escribir_ejemplo(carpeta_proyecto: str) -> str:
    """Escribe/actualiza las copias SIN secretos para versionar:
    _acceso.<entorno>.ejemplo.ini por cada archivo de acceso y, si
    _configtotal.ini lleva secretos (proyecto sin entornos), su
    _configtotal.ejemplo.ini. Devuelve la ruta del primero que cambió, o ''."""
    cambiados = []
    principal = os.path.join(carpeta_proyecto, '_configtotal.ini')
    ejemplo = os.path.join(carpeta_proyecto, '_configtotal.ejemplo.ini')
    if os.path.isfile(principal) and (os.path.isfile(ejemplo) or _tiene_secretos(principal)):
        if _escribir_un_ejemplo(principal, ejemplo):
            cambiados.append(ejemplo)
    for entorno in ENTORNOS:
        nombre, cifrado = acceso_existente(carpeta_proyecto, entorno)
        if not nombre:
            continue
        origen = os.path.join(carpeta_proyecto, nombre)
        destino = os.path.join(carpeta_proyecto, f'_acceso.{entorno}.ejemplo.ini')
        contenido = None
        if cifrado:
            # solo si el token ya está a mano: no se pide un token para esto
            try:
                contenido = boveda.leer_archivo(
                    origen, carpeta_proyecto, boveda.token_de(carpeta_proyecto, pedir=False))
            except boveda.ErrorBoveda:
                continue
        if _escribir_un_ejemplo(origen, destino, contenido):
            cambiados.append(destino)
    return cambiados[0] if cambiados else ''


_CABECERA_V4 = (
    ('; _configtotal.ini — davgen v4.0',
     '; _configtotal.ini — configuración del proyecto para davgen'),
    ('; Completar este archivo y ejecutar:  python davgen4.py generar',
     '; Completar este archivo y ejecutar:  davgen generar'),
)


def migrar_ini(carpeta_proyecto: str) -> List[str]:
    """Pone al día un _configtotal.ini escrito por davgen 4.x, EN SU LUGAR y
    sin cambiar ningún valor que siga vigente (ni un secreto, ni un comentario
    propio). Devuelve la lista de cambios hechos (vacía = ya estaba al día).

    Qué hace:
      · quita `[seguridad] validar_acceso` y su bloque de comentarios (la
        contraseña de acceso al generador ya no existe);
      · actualiza la cabecera y las menciones al comando `davgen4`;
      · NO agrega claves: las que falten toman el valor por defecto, y
        `davgen actualizar` avisa de las que cambiaron de valor por defecto.
    """
    ruta = os.path.join(carpeta_proyecto, '_configtotal.ini')
    if not os.path.isfile(ruta):
        return []
    with open(ruta, encoding='utf-8-sig', newline='') as f:
        original = f.read()
    salto = '\r\n' if '\r\n' in original else '\n'
    lineas = original.replace('\r\n', '\n').split('\n')
    cambios: List[str] = []

    salida: List[str] = []
    seccion = ''
    for linea in lineas:
        limpia = linea.strip()
        if limpia.startswith('[') and limpia.endswith(']'):
            seccion = limpia[1:-1].strip().lower()
        es_clave = bool(limpia) and limpia[0] not in ';#' and '=' in limpia
        clave = limpia.split('=', 1)[0].strip().lower() if es_clave else ''
        if seccion == 'seguridad' and clave == 'validar_acceso':
            # se va la clave y el bloque de comentarios pegado encima
            while salida and salida[-1].strip().startswith((';', '#')):
                salida.pop()
            cambios.append("[seguridad] validar_acceso eliminado (davgen 5 no "
                           "pide contraseña de acceso)")
            continue
        salida.append(linea)

    texto = '\n'.join(salida)
    for viejo, nuevo in _CABECERA_V4:
        if viejo in texto:
            texto = texto.replace(viejo, nuevo)
            if 'cabecera actualizada' not in ' '.join(cambios):
                cambios.append("cabecera actualizada (ya no dice davgen v4.0)")
    if 'davgen4' in texto:
        texto = texto.replace('davgen4', 'davgen')
        cambios.append("menciones al comando `davgen4` → `davgen`")

    if cambios:
        with open(ruta, 'w', encoding='utf-8', newline='') as f:
            f.write(texto.replace('\n', salto))
    return cambios


# Claves cuyo valor POR DEFECTO cambió entre davgen 4.x y 5: si faltan en un
# .ini heredado, el proyecto se comporta distinto sin que nadie lo haya pedido.
_DEFECTOS_QUE_CAMBIARON = (
    ('generar', 'produccion', 'si', 'no'),
    ('generar', 'front', 'si', 'no'),
    ('seguridad', 'google_auth_activo', 'si', 'no'),
    ('seguridad', 'google_client_id', '(uno fijo)', '(vacío)'),
    ('seguridad', 'owner_email', '(una cuenta fija)', '(vacío)'),
    ('proyecto', 'autor', '(un autor fijo)', '(vacío)'),
)


def claves_con_defecto_distinto(carpeta_proyecto: str) -> List[str]:
    """Avisos por cada clave AUSENTE del .ini cuyo valor por defecto es
    distinto en davgen 5 que en 4.x."""
    ruta = os.path.join(carpeta_proyecto, '_configtotal.ini')
    ini = nuevo_parser()
    try:
        ini.read(ruta, encoding='utf-8-sig')
    except configparser.Error:
        return []
    return [f"[{s}] {c} no está en el .ini: en davgen 4 valía {antes} por "
            f"defecto y ahora {ahora} — escribirla si se usaba"
            for s, c, antes, ahora in _DEFECTOS_QUE_CAMBIARON
            if not ini.has_option(s, c)]


def nuevo_parser() -> configparser.ConfigParser:
    """Parser del .ini. Sin interpolación (un % en una contraseña no rompe) y
    sin comentarios en línea: `password = ab;cd#ef` se lee completo."""
    return configparser.ConfigParser(interpolation=None,
                                     inline_comment_prefixes=None)


def leer_ini(carpeta_proyecto: str, entorno: str = '',
             archivo: str = '_configtotal.ini') -> configparser.ConfigParser:
    """_configtotal.ini con los valores NO vacíos del archivo de acceso del
    entorno superpuestos. Lanza configparser.Error si alguno es ilegible y
    boveda.ErrorBoveda si el de accesos está cifrado y no se puede abrir."""
    ini = nuevo_parser()
    ini.read(os.path.join(carpeta_proyecto, archivo), encoding='utf-8-sig')
    nombre, cifrado = acceso_existente(carpeta_proyecto, entorno_actual(entorno))
    if nombre:
        acceso = os.path.join(carpeta_proyecto, nombre)
        extra = nuevo_parser()
        if cifrado:
            # se descifra EN MEMORIA con el token del proyecto (lo pide una vez)
            extra.read_string(boveda.leer_archivo(acceso, carpeta_proyecto))
        else:
            extra.read(acceso, encoding='utf-8-sig')
        for seccion in extra.sections():
            for clave, valor in extra.items(seccion):
                if valor.strip():
                    if not ini.has_section(seccion):
                        ini.add_section(seccion)
                    ini.set(seccion, clave, valor)
    return ini


def cargar(carpeta_proyecto: str, archivo: str = '_configtotal.ini',
           entorno: str = '') -> Tuple[Dict, List[str]]:
    """
    Lee y valida el archivo de configuración (_configtotal.ini).
    Devuelve (config_normalizada, errores).
    Si errores no está vacío, la config NO debe usarse.
    """
    ruta = os.path.join(carpeta_proyecto, archivo)
    errores: List[str] = []

    if not os.path.isfile(ruta):
        return {}, [f"No existe {ruta} — crear el archivo de configuración"]

    entorno = entorno_actual(entorno)
    try:
        # utf-8-sig tolera el BOM que agregan algunos editores de Windows
        ini = leer_ini(carpeta_proyecto, entorno, archivo)
    except configparser.Error as e:
        return {}, [f"{archivo} o {nombre_acceso(entorno)} ilegible: {e}"]

    def valor(seccion, clave, defecto=''):
        try:
            return ini.get(seccion, clave, fallback=defecto).strip()
        except configparser.Error:
            return defecto

    cfg = {
        'carpeta':    os.path.abspath(carpeta_proyecto),
        'ruta_config': ruta,
        'entorno':    entorno,
        'con_entornos': hay_entornos(carpeta_proyecto),
        'archivo_acceso': acceso_existente(carpeta_proyecto, entorno)[0],
        'acceso_cifrado': acceso_existente(carpeta_proyecto, entorno)[1],
        'nombre':     valor('proyecto', 'nombre'),
        'modulo':     valor('proyecto', 'modulo').lower(),
        'autor':      valor('proyecto', 'autor'),
        'tipo':       valor('entrada', 'tipo', 'mockup').lower(),
        'mockup':     valor('entrada', 'mockup', 'mockup'),
        'bd': {
            'host':     valor('bd', 'host'),
            'puerto':   valor('bd', 'puerto', '3306'),
            'usuario':  valor('bd', 'usuario'),
            'password': valor('bd', 'password'),
            'database': valor('bd', 'database'),
        },
        'excluir':    {e.strip().lower()
                       for e in valor('opciones', 'excluir').split(',') if e.strip()},
        'publico':    _parse_publico(valor('opciones', 'publico')),
        # columnas que el dominio gestiona (no editables en el frontend generado)
        'solo_lectura': _parse_tabla_columnas(valor('opciones', 'solo_lectura')),
        # tablas sin botón "Dar de baja" en las páginas generadas
        'sin_baja':   {t.strip().lower()
                       for t in valor('opciones', 'sin_baja').split(',') if t.strip()},
        # tablas de SOLO CONSULTA: la página generada no ofrece alta/edición/baja
        'solo_consulta': {t.strip().lower()
                          for t in valor('opciones', 'solo_consulta').split(',')
                          if t.strip()},
        'middleware': valor('opciones', 'middleware', 'auth:sanctum'),
        # reutilizar las conexiones a MySQL entre peticiones (hosting compartido)
        'conexiones_persistentes': _es_si(
            valor('opciones', 'conexiones_persistentes', 'si') or 'si'),
        # [legal] · textos de privacidad/términos y conservación de datos
        'legal': {
            'responsable':  valor('legal', 'responsable'),
            'contacto':     valor('legal', 'contacto'),
            'jurisdiccion': valor('legal', 'jurisdiccion'),
            'alojamiento':  valor('legal', 'alojamiento'),
            'vigente_desde': valor('legal', 'vigente_desde'),
            'retencion_bitacora_dias': valor('legal', 'retencion_bitacora_dias', '365') or '365',
        },
        'max_archivo_mb': valor('opciones', 'max_archivo_mb', '10'),
        'extensiones_archivo': valor('opciones', 'extensiones_archivo',
                                     'pdf,jpg,jpeg,png,doc,docx,xls,xlsx'),
        # flags de [generar]: principales default si, extras default no
        'generar': {flag: _es_si(valor('generar', flag,
                                       'si' if flag in _FLAGS_GENERAR_DEFAULT_SI else 'no'))
                    for flag in _FLAGS_GENERAR},
        # [seguridad] · admin sembrado + control de acceso Google
        'admin_email':  valor('seguridad', 'admin_email', 'admin@localhost') or 'admin@localhost',
        'admin_nombre': valor('seguridad', 'admin_nombre', 'Administrador') or 'Administrador',
        # '' = todavía no la escribieron (generar y seguridad la exigen)
        'admin_password': valor('seguridad', 'admin_password'),
        'owner_email':  valor('seguridad', 'owner_email', ''),
        'google_auth_activo': _es_si(valor('seguridad', 'google_auth_activo', 'no')),
        'google_client_id':  valor('seguridad', 'google_client_id', ''),
        'google_dominios_permitidos': valor('seguridad', 'google_dominios_permitidos', ''),
        'roles_solo_google': valor('seguridad', 'roles_solo_google', 'cliente'),
        'ftp': {
            'host':        valor('ftp', 'host'),
            'usuario':     valor('ftp', 'usuario'),
            'password':    valor('ftp', 'password'),
            'ruta_remota': valor('ftp', 'ruta_remota', '/servicio'),
            'url':         valor('ftp', 'url'),
        },
    }

    # ── Avisos (no detienen la generación) ────────────────────────────
    avisos: List[str] = []
    cfg['avisos'] = avisos
    problema = (problema_admin_password(cfg['admin_password'], cfg['admin_email'])
                if cfg['admin_password'] else '')
    if problema:
        errores.append(f"[seguridad] admin_password — {problema}")
    if cfg['google_auth_activo'] and not cfg['google_client_id']:
        avisos.append("[seguridad] google_auth_activo = si pero falta "
                      "google_client_id: el botón de Google no aparecerá hasta "
                      "cargar un Client ID propio (ver CONFIGURAR-GOOGLE-AUTH.md).")
    if cfg['con_entornos'] and not cfg['archivo_acceso']:
        avisos.append(f"Falta {nombre_acceso(entorno)}: el entorno «{entorno}» no "
                      "tiene accesos propios (crearlo con `davgen entornos`).")
    if ini.has_option('seguridad', 'validar_acceso'):
        avisos.append("[seguridad] validar_acceso ya no existe (davgen 5 no pide "
                      "contraseña): se puede borrar esa línea.")
    url_ftp = valor('ftp', 'url')
    if url_ftp.lower().startswith('http://'):
        avisos.append("[ftp] url empieza con http:// — si el hosting fuerza "
                      "HTTPS el navegador bloqueará la API (contenido mixto). "
                      "Usar https://.")

    # ── Validación con mensajes accionables ───────────────────────────
    if not cfg['nombre']:
        errores.append("[proyecto] nombre — escribir el nombre del sistema")
    if not _RE_MODULO.match(cfg['modulo']):
        errores.append("[proyecto] modulo — usar 2 a 6 letras minúsculas (ej: con, zap, den)")

    if cfg['tipo'] not in ('mockup', 'bd'):
        errores.append("[entrada] tipo — debe ser 'mockup' o 'bd'")
    elif cfg['tipo'] == 'mockup':
        if not cfg['mockup']:
            errores.append("[entrada] mockup — indicar la ruta relativa al mockup")
        elif os.path.isabs(cfg['mockup']) or '..' in cfg['mockup'].replace('\\', '/').split('/'):
            errores.append("[entrada] mockup — debe ser una ruta RELATIVA dentro de la "
                           "carpeta del proyecto (sin '..' ni unidades)")
        else:
            ruta_mockup = os.path.join(carpeta_proyecto, cfg['mockup'])
            if not os.path.exists(ruta_mockup):
                errores.append(f"[entrada] mockup — no existe '{cfg['mockup']}' dentro del "
                               f"proyecto; copiar ahí el .html o la carpeta del mockup")
            elif os.path.isdir(ruta_mockup) and not os.listdir(ruta_mockup):
                errores.append(f"[entrada] mockup — la carpeta '{cfg['mockup']}' está vacía; "
                               f"copiar ahí el .html o la carpeta del mockup")
            cfg['ruta_mockup'] = ruta_mockup
    else:  # bd
        # password puede ser vacío (ej: root local sin contraseña)
        for clave in ('host', 'usuario', 'database'):
            if not cfg['bd'][clave]:
                errores.append(f"[bd] {clave} — requerido cuando [entrada] tipo = bd")
        if not cfg['bd']['puerto'].isdigit():
            errores.append("[bd] puerto — debe ser numérico (default 3306)")

    if not cfg['max_archivo_mb'].isdigit() or int(cfg['max_archivo_mb']) < 1:
        errores.append("[opciones] max_archivo_mb — debe ser un entero ≥ 1")
    else:
        cfg['max_archivo_mb'] = int(cfg['max_archivo_mb'])

    dias = cfg['legal']['retencion_bitacora_dias']
    if not dias.isdigit():
        errores.append("[legal] retencion_bitacora_dias — debe ser un entero ≥ 0 "
                       "(0 = la bitácora no se borra)")
    else:
        cfg['legal']['retencion_bitacora_dias'] = int(dias)

    cfg['extensiones_archivo'] = [
        e.strip().lower() for e in cfg['extensiones_archivo'].split(',') if e.strip()]
    if not cfg['extensiones_archivo']:
        errores.append("[opciones] extensiones_archivo — indicar al menos una (ej: pdf)")

    # FTP es opcional, pero si se llenó a medias se avisa
    ftp = cfg['ftp']
    llenos = [v for k, v in ftp.items() if k != 'ruta_remota' and v]
    if llenos and (not ftp['host'] or not ftp['usuario'] or not ftp['password']):
        errores.append("[ftp] — está incompleto: llenar host, usuario y password, "
                       "o dejar toda la sección vacía")
    cfg['ftp_listo'] = bool(ftp['host'] and ftp['usuario'] and ftp['password'])

    return cfg, errores


def _parse_publico(texto: str) -> Dict[str, List[str]]:
    resultado = {}
    for parte in (texto or '').split(';'):
        tabla, _, ops = parte.strip().partition(':')
        operaciones = [o.strip() for o in ops.split(',')
                       if o.strip() in ('sel', 'get', 'add')]
        if tabla and operaciones:
            resultado[tabla.strip()] = operaciones
    return resultado


def _parse_tabla_columnas(texto: str) -> Dict[str, List[str]]:
    """'tbl_x:col1,col2 ; tbl_y:col3' → {'tbl_x': ['col1','col2'], ...}"""
    resultado = {}
    for parte in (texto or '').split(';'):
        tabla, _, cols = parte.strip().partition(':')
        columnas = [c.strip().lower() for c in cols.split(',') if c.strip()]
        if tabla and columnas:
            resultado[tabla.strip().lower()] = columnas
    return resultado
