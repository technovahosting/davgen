"""
resumen.py — registro de lo generado, resumen final, manifiesto de
integridad (detecta ediciones manuales del código generado) y decisión
de producción.
"""
import ftplib
import hashlib
import json
import os
from datetime import datetime  # noqa: F401
from .reloj import ahora as _ahora
from typing import Dict, List

from .consola import C, confirmar, dim, error, info, ok, titulo, warn
from .version import VERSION
from .plantillas import cargar as _plantilla


class Registro:
    """Acumula todo lo generado para mostrarlo al final."""

    def __init__(self, base: str):
        self.base = base
        self.items: List[Dict] = []
        self._vistos = set()

    def add(self, categoria: str, ruta) -> None:
        rutas = ruta if isinstance(ruta, list) else [ruta]
        for r in rutas:
            rel = os.path.relpath(r, self.base)
            if (categoria, rel) not in self._vistos:
                self._vistos.add((categoria, rel))
                self.items.append({'categoria': categoria, 'ruta': rel})

    def por_categoria(self) -> Dict[str, List[str]]:
        grupos: Dict[str, List[str]] = {}
        for it in self.items:
            grupos.setdefault(it['categoria'], []).append(it['ruta'])
        return grupos


_SIGUIENTES = _plantilla('despliegue/siguientes_pasos.md', __name__, '_SIGUIENTES')

# ─────────────────────────────────────────────
#  Manifiesto de integridad del código generado
# ─────────────────────────────────────────────
_MANIFIESTO = '.davgen-manifest.json'


def _sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, 'rb') as f:
        for bloque in iter(lambda: f.read(65536), b''):
            h.update(bloque)
    return h.hexdigest()


def verificar_manifiesto(salida: str) -> List[str]:
    """Archivos generados que fueron editados a mano desde la última corrida."""
    ruta = os.path.join(salida, _MANIFIESTO)
    if not os.path.isfile(ruta):
        return []
    try:
        with open(ruta, encoding='utf-8') as f:
            manifiesto = json.load(f)
    except (OSError, ValueError):
        return []
    editados = []
    for rel, hash_previo in manifiesto.get('archivos', {}).items():
        archivo = os.path.join(salida, rel)
        if os.path.isfile(archivo) and _sha256(archivo) != hash_previo:
            editados.append(rel)
    return editados


def escribir_manifiesto(salida: str, reg: 'Registro') -> str:
    archivos = {}
    for it in reg.items:
        ruta = os.path.join(salida, it['ruta'])
        if os.path.isfile(ruta):
            archivos[it['ruta'].replace('\\', '/')] = _sha256(ruta)
    ruta_m = os.path.join(salida, _MANIFIESTO)
    with open(ruta_m, 'w', encoding='utf-8') as f:
        json.dump({'generado': _ahora().strftime('%Y-%m-%d %H:%M'),
                   'archivos': archivos}, f, indent=1, ensure_ascii=False)
    return ruta_m


# ─────────────────────────────────────────────
#  Snapshot del esquema (comando sincronizar)
# ─────────────────────────────────────────────
_SNAPSHOT_ESQUEMA = '.davgen-schema.json'


def snapshot_esquema(tablas: List[Dict]) -> Dict:
    """{tabla: {columna: definición SQL}} — la huella del esquema actual."""
    return {t['tabla']: {c['COLUMN_NAME']: c['SQL_FULL'] for c in t['columnas']}
            for t in tablas}


def leer_snapshot_esquema(salida: str):
    ruta = os.path.join(salida, _SNAPSHOT_ESQUEMA)
    if not os.path.isfile(ruta):
        return None
    try:
        with open(ruta, encoding='utf-8') as f:
            return json.load(f).get('tablas')
    except (OSError, ValueError):
        return None


def escribir_snapshot_esquema(salida: str, tablas: List[Dict]) -> None:
    ruta = os.path.join(salida, _SNAPSHOT_ESQUEMA)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump({'generado': _ahora().strftime('%Y-%m-%d %H:%M'),
                   'tablas': snapshot_esquema(tablas)},
                  f, indent=1, ensure_ascii=False)


def delta_esquema(viejo: Dict, nuevo: Dict) -> List[str]:
    """Diferencias legibles entre dos snapshots; [] si el esquema no cambió."""
    cambios = []
    for t in sorted(set(nuevo) - set(viejo)):
        cambios.append(f"tabla NUEVA: {t}")
    for t in sorted(set(viejo) - set(nuevo)):
        cambios.append(f"tabla ELIMINADA: {t}")
    for t in sorted(set(viejo) & set(nuevo)):
        v, n = viejo[t], nuevo[t]
        for c in sorted(set(n) - set(v)):
            cambios.append(f"{t}: columna nueva `{c}`")
        for c in sorted(set(v) - set(n)):
            cambios.append(f"{t}: columna eliminada `{c}`")
        for c in sorted(k for k in set(v) & set(n) if v[k] != n[k]):
            cambios.append(f"{t}: `{c}` modificada ({v[c]} → {n[c]})")
    return cambios


def resumen_final(ctx: Dict, reg: Registro) -> str:
    titulo("RESUMEN — todo lo generado")
    grupos = reg.por_categoria()
    orden = ['mockup', 'database', 'backend', 'frontend', 'testing',
             'documentacion', '_prompts']
    lineas_md, total = [], 0

    for cat in orden + [c for c in grupos if c not in orden]:
        archivos = grupos.get(cat, [])
        if not archivos:
            continue
        total += len(archivos)
        print(f"  {C.BOLD}{C.CYAN}{cat}{C.RESET}  ({len(archivos)} archivo(s))")
        lineas_md.append(f"\n### {cat} ({len(archivos)} archivos)\n")
        for ruta in sorted(archivos):
            dim(f"· {ruta}")
            lineas_md.append(f"- `{ruta}`")

    print(f"\n  {C.GREEN}{C.BOLD}Total: {total} archivos · "
          f"{len(ctx['tablas'])} entidad(es){C.RESET}")
    print(f"  Carpeta: {os.path.abspath(ctx['salida'])}\n")

    entidades = '\n'.join(
        f"| `{t['entidad']}` | `{t['tabla']}` | {len(t['columnas'])} | {t['origen']} |"
        for t in ctx['tablas'])
    contenido = (
        f"# Resumen de generación — {ctx['nombre']}\n\n"
        f"| Campo | Valor |\n|---|---|\n"
        # v4.36.0 — el RESUMEN no decía con qué versión se generó el proyecto:
        # para saberlo había que abrir un .php y leer su cabecera @generated.
        # Con 10+ proyectos vivos en versiones distintas (4.17 a 4.35), esa era
        # la pregunta más frecuente al retomar cualquiera de ellos.
        f"| Generador | **davgen v{VERSION}** |\n"
        f"| Generado | {_ahora().strftime('%Y-%m-%d %H:%M')} |\n"
        f"| Entrada | {ctx['origen_entrada']} |\n"
        f"| Archivos | {total} |\n\n"
        f"## Entidades\n\n"
        f"| Entidad | Tabla | Columnas | Origen |\n|---|---|---|---|\n{entidades}\n\n"
        f"## Archivos generados\n" + '\n'.join(lineas_md) + '\n\n' + _SIGUIENTES)

    ruta = os.path.join(ctx['salida'], 'RESUMEN.md')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(contenido)
    info(f"Resumen guardado en {ruta}")
    print(f"\n{C.BOLD}{_SIGUIENTES}{C.RESET}")
    return ruta


# ─────────────────────────────────────────────
#  Decisión de producción
# ─────────────────────────────────────────────
def _ftp_mkd_p(ftp: ftplib.FTP, remoto: str) -> None:
    ruta = ''
    for parte in [p for p in remoto.split('/') if p]:
        ruta += '/' + parte
        try:
            ftp.mkd(ruta)
        except ftplib.all_errors:
            pass


def _host_ftp(host: str) -> str:
    """host con esquema/puerto (ftp://host:21/...) → host limpio."""
    h = host.strip()
    for pref in ('ftp://', 'ftps://', 'sftp://'):
        if h.lower().startswith(pref):
            h = h[len(pref):]
    return h.rstrip('/').split('/')[0].split(':')[0]


# Script PHP que descomprime el zip subido y se autoelimina. Se invoca por
# HTTP una vez subido. {token} evita ejecuciones ajenas.
_DESCOMPRIMIR_PHP = _plantilla('despliegue/descomprimir.php', __name__, '_DESCOMPRIMIR_PHP')



def _preparar_env_produccion(ruta_laravel: str, bd: Dict, url: str,
                              ruta_remota: str = '') -> None:
    """Ajusta el .env del proyecto para producción: BD de la nube, APP_URL,
    APP_ENV=production y APP_DEBUG=false. Conserva el APP_KEY existente.
    APP_URL incluye la subcarpeta del backend ({url}/{segmento_ruta_remota})
    para que url() de Laravel genere rutas correctas en el servidor."""
    ruta = os.path.join(ruta_laravel, '.env')
    if not os.path.isfile(ruta):
        ejemplo = os.path.join(ruta_laravel, '.env.example')
        if os.path.isfile(ejemplo):
            __import__('shutil').copy2(ejemplo, ruta)
        else:
            return
    # APP_URL debe incluir la subcarpeta del backend en el hosting
    sub = ruta_remota.strip('/').split('/')[-1] if ruta_remota.strip('/') else ''
    app_url = (f"{url.rstrip('/')}/{sub}" if url and sub
               else url.rstrip('/') if url else 'http://localhost')
    valores = {
        'APP_ENV': 'production', 'APP_DEBUG': 'false',
        'APP_URL': app_url,
        'DB_CONNECTION': 'mysql', 'DB_HOST': bd['host'], 'DB_PORT': bd['puerto'],
        'DB_DATABASE': bd['database'], 'DB_USERNAME': bd['usuario'],
        'DB_PASSWORD': bd['password'],
        # hosting compartido: evitar drivers que requieren tablas propias
        # (sessions/cache/jobs). file + sync no necesitan crear tablas.
        'SESSION_DRIVER': 'file', 'CACHE_STORE': 'file',
        'QUEUE_CONNECTION': 'sync',
    }
    # utf-8-sig, NO utf-8: si el .env se escribió con Set-Content de PowerShell
    # 5.1 lleva BOM, y con BOM la primera clave se lee como '﻿APP_ENV'.
    # Eso no coincide con `valores`, así que la línea vieja quedaba y la nueva
    # se AÑADÍA al final: un .env con la clave duplicada (gana la última, pero
    # es una trampa silenciosa). Mismo problema que rompió VITE_API_URL en
    # un proyecto en producción.
    with open(ruta, encoding='utf-8-sig') as f:
        lineas = f.read().splitlines()
    vistos, salida = set(), []
    for linea in lineas:
        stripped = linea.strip()
        # preservar comentarios y líneas vacías tal cual (sin reemplazar)
        if not stripped or stripped.startswith('#'):
            salida.append(linea)
            continue
        clave = stripped.split('=')[0].strip()
        if clave in valores and clave not in vistos:
            salida.append(f"{clave}={valores[clave]}")
            vistos.add(clave)
        else:
            salida.append(linea)
    salida += [f"{k}={v}" for k, v in valores.items() if k not in vistos]
    salida = con_interruptor_persistentes(salida)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('\n'.join(salida) + '\n')


def con_interruptor_persistentes(lineas: List[str]) -> List[str]:
    """Las líneas de un .env con `DB_PERSISTENT=true` si no traían la clave.

    Es el interruptor de las conexiones persistentes que activa
    bootstrap/app.php. Solo se AGREGA: si el usuario ya la puso en `false`
    (porque su hosting dio el error 1203) no se le vuelve a encender."""
    if any(x.strip().split('=')[0].strip() == 'DB_PERSISTENT' for x in lineas):
        return lineas
    return lineas + ['# Reutilizar las conexiones a MySQL entre peticiones (límite por hora '
                     'del hosting, error 1226). false si aparece el error 1203.',
                     'DB_PERSISTENT=true']


_EXCLUIR_ZIP = {'.git', 'node_modules', '.idea', '.vscode', 'tests'}

# ── Protección de la carpeta publicada ──────────────────────────────────────
# El despliegue en hosting compartido deja el proyecto Laravel COMPLETO dentro
# de una carpeta servida por web (public/ se aplana a la raíz). Sin reglas
# propias, Apache/LiteSpeed sirven como archivos estáticos el .env, los logs
# (con códigos 2FA) y lo que suben los usuarios. Por eso el despliegue lleva:
#   · un bloque de reglas al inicio del .htaccess de la raíz, y
#   · un .htaccess «denegar todo» dentro de cada carpeta interna (segunda
#     barrera: sigue ahí aunque alguien reemplace el de la raíz).
MARCA_PROTECCION = '# davgen:proteccion'
HTACCESS_PROTECCION = _plantilla('despliegue/htaccess_proteccion.txt', __name__,
                                 'HTACCESS_PROTECCION')
CARPETAS_INTERNAS = ('app', 'bootstrap', 'config', 'database', 'lang', 'resources',
                     'routes', 'storage', 'tests', 'vendor')
HTACCESS_DENEGAR = (
    MARCA_PROTECCION + " — carpeta interna de Laravel: nada de aquí se sirve por web.\n"
    "<IfModule mod_authz_core.c>\n    Require all denied\n</IfModule>\n"
    "<IfModule !mod_authz_core.c>\n    Order allow,deny\n    Deny from all\n</IfModule>\n")

# Archivos del proyecto que no hacen falta en producción (y algunos estorban:
# sesiones, caché y subidas de la PC de desarrollo no deben viajar al sitio).
_NO_DESPLEGAR = {'.env.example', 'phpunit.xml', '.editorconfig', '.gitattributes',
                 '.gitignore', 'package.json', 'package-lock.json', 'vite.config.js',
                 'README.md', 'README-SEGURIDAD.md', 'CHANGELOG.md'}
_SOLO_ESTRUCTURA = ('storage/app/', 'storage/framework/cache/',
                    'storage/framework/sessions/', 'storage/framework/views/',
                    'storage/framework/testing/')


def htaccess_protegido(original: str) -> str:
    """`original` (el .htaccess de la raíz) con el bloque de protección al
    inicio. Si ya lo tiene, se reemplaza por la versión actual; el resto del
    archivo (las reglas de Laravel o las del usuario) no se toca."""
    original = original or ''
    if MARCA_PROTECCION in original:
        fin = original.find('# davgen:fin-proteccion')
        if fin >= 0:
            original = original[fin + len('# davgen:fin-proteccion'):].lstrip('\r\n')
    return HTACCESS_PROTECCION.rstrip('\n') + '\n\n' + original


def _no_desplegar(rel: str) -> bool:
    """True si `rel` (con /) no debe ir en el zip de despliegue."""
    nombre = rel.rsplit('/', 1)[-1]
    if rel in _NO_DESPLEGAR:
        return True
    if rel.startswith('storage/logs/') and rel.endswith('.log'):
        return True
    if rel.startswith('database/') and rel.endswith(('.sqlite', '.sqlite3')):
        return True
    if rel.startswith('bootstrap/cache/') and rel.endswith('.php'):
        return True                 # config/rutas cacheadas con datos de ESTA PC
    if rel.startswith(_SOLO_ESTRUCTURA) and nombre != '.gitignore':
        return True                 # se conserva la carpeta, no su contenido local
    return False


def _empaquetar_laravel(ruta_laravel: str, destino_zip: str) -> int:
    """
    Comprime el Laravel completo APLANANDO public/ a la raíz del zip
    (despliegue en subcarpeta de hosting compartido): el front controller
    index.php queda en la raíz con sus rutas corregidas (__DIR__/vendor,
    __DIR__/bootstrap), de modo que {url}/{carpeta}/api/... enruta bien sin
    el prefijo /public. Devuelve el nº de archivos.
    """
    import zipfile
    public = os.path.join(ruta_laravel, 'public')
    n = 0
    con_htaccess = False
    with zipfile.ZipFile(destino_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        # 1 · todo el proyecto MENOS public/ → raíz del zip
        for raiz, dirs, archivos in os.walk(ruta_laravel):
            dirs[:] = [d for d in dirs if d not in _EXCLUIR_ZIP]
            rel_dir = os.path.relpath(raiz, ruta_laravel)
            if rel_dir == 'public' or rel_dir.startswith('public' + os.sep):
                continue
            for nombre in archivos:
                local = os.path.join(raiz, nombre)
                rel = os.path.relpath(local, ruta_laravel).replace('\\', '/')
                if _no_desplegar(rel):
                    continue
                z.write(local, rel)
                n += 1
        # 1b · segunda barrera: «denegar todo» dentro de cada carpeta interna
        for carpeta in CARPETAS_INTERNAS:
            if os.path.isdir(os.path.join(ruta_laravel, carpeta)) and carpeta != 'tests':
                z.writestr(f'{carpeta}/.htaccess', HTACCESS_DENEGAR)
                n += 1
        # 2 · public/* → raíz del zip; index.php con rutas corregidas
        for raiz, _dirs, archivos in os.walk(public):
            for nombre in archivos:
                local = os.path.join(raiz, nombre)
                rel = os.path.relpath(local, public).replace('\\', '/')
                if rel == 'index.php':
                    with open(local, encoding='utf-8') as f:
                        cont = f.read()
                    cont = (cont
                            .replace("/../vendor/autoload.php", "/vendor/autoload.php")
                            .replace("/../bootstrap/app.php", "/bootstrap/app.php")
                            .replace("/../storage/framework/maintenance.php",
                                     "/storage/framework/maintenance.php"))
                    z.writestr(rel, cont)
                elif rel == '.htaccess':
                    # las reglas de Laravel, precedidas por el bloque de protección
                    with open(local, encoding='utf-8', errors='replace') as f:
                        z.writestr(rel, htaccess_protegido(f.read()))
                    con_htaccess = True
                else:
                    z.write(local, rel)
                n += 1
        if not con_htaccess:
            z.writestr('.htaccess', htaccess_protegido(''))
            n += 1
    return n


def proteger_remoto(cfg_ftp: Dict) -> Dict:
    """Pone la protección en un despliegue que YA está en el servidor (los
    hechos con versiones anteriores no la tienen). Idempotente:
      · raíz: baja el .htaccess, le antepone el bloque y lo vuelve a subir
        (conservando el resto);
      · cada carpeta interna que exista: sube su .htaccess «denegar todo».
    Devuelve {raiz: 'agregada'|'actualizada'|'ya estaba', carpetas: [...], error}."""
    import io
    reporte = {'raiz': '', 'carpetas': [], 'error': ''}
    remota = cfg_ftp['ruta_remota'].rstrip('/')
    try:
        ftp = ftplib.FTP()
        ftp.connect(_host_ftp(cfg_ftp['host']), 21, timeout=60)
        ftp.login(cfg_ftp['usuario'], cfg_ftp['password'])
        ftp.set_pasv(True)
    except (ftplib.all_errors, OSError) as e:
        reporte['error'] = f'FTP no conecta: {e}'
        return reporte
    try:
        trozos = []
        try:
            ftp.retrbinary(f'RETR {remota}/.htaccess', trozos.append)
            actual = b''.join(trozos).decode('utf-8', errors='replace')
        except ftplib.all_errors:
            actual = ''
        nuevo = htaccess_protegido(actual)
        if nuevo == actual:
            reporte['raiz'] = 'ya estaba'
        else:
            ftp.storbinary(f'STOR {remota}/.htaccess', io.BytesIO(nuevo.encode('utf-8')))
            reporte['raiz'] = 'actualizada' if MARCA_PROTECCION in actual else 'agregada'
        for carpeta in CARPETAS_INTERNAS:
            try:
                ftp.cwd(f'{remota}/{carpeta}')
            except ftplib.all_errors:
                continue                          # esa carpeta no existe allá
            ftp.storbinary(f'STOR {remota}/{carpeta}/.htaccess',
                           io.BytesIO(HTACCESS_DENEGAR.encode('utf-8')))
            reporte['carpetas'].append(carpeta)
    except ftplib.all_errors as e:
        reporte['error'] = str(e)
    finally:
        try:
            ftp.quit()
        except ftplib.all_errors:
            pass
    return reporte


def _despliegue_remoto_existe(cfg_ftp: Dict) -> bool:
    """
    True si la carpeta remota YA TIENE un Laravel desplegado (index.php
    presente — entry point del zip aplanado). Solo en ese caso el despliegue
    INCREMENTAL tiene sentido. Si la carpeta existe pero está vacía (hosting
    la pre-crea) devuelve False para forzar el primer despliegue completo.
    """
    host = _host_ftp(cfg_ftp['host'])
    remota = cfg_ftp['ruta_remota'].rstrip('/')
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, 21, timeout=30)
        ftp.login(cfg_ftp['usuario'], cfg_ftp['password'])
        ftp.set_pasv(True)
    except (ftplib.all_errors, OSError):
        return False
    existe = False
    try:
        ftp.cwd(remota)
        # Carpeta existe — verificar que index.php esté (zip fue extraído)
        try:
            ftp.size('index.php')
            existe = True
        except ftplib.all_errors:
            # SIZE no soportado o archivo inexistente; intentar con NLST
            try:
                archivos = ftp.nlst('.')
                existe = any(f == 'index.php' or f.endswith('/index.php')
                             for f in archivos)
            except ftplib.all_errors:
                existe = False
    except ftplib.all_errors:
        existe = False
    try:
        ftp.quit()
    except ftplib.all_errors:
        pass
    return existe


# ─────────────────────────────────────────────
#  Manifiesto de despliegue: qué se subió y con qué hash
# ─────────────────────────────────────────────
_MANIFIESTO_DEPLOY = '.davgen-deploy.json'


def _sha256_generado(ruta: str) -> str:
    """sha256 IGNORANDO la línea `@generated` de la cabecera (lleva fecha y
    versión): así el delta de despliegue solo detecta cambios reales."""
    with open(ruta, 'rb') as f:
        crudo = f.read()
    if b'@generated' in crudo[:400]:
        crudo = b'\n'.join(l for l in crudo.split(b'\n')
                           if b'@generated' not in l)
    return hashlib.sha256(crudo).hexdigest()


def _hashes_generado(carpeta: str) -> Dict[str, str]:
    """{ruta relativa con /: hash normalizado} de todo el código generado."""
    hashes = {}
    for raiz, dirs, archivos in os.walk(carpeta):
        dirs.sort()
        for nombre in sorted(archivos):
            local = os.path.join(raiz, nombre)
            rel = os.path.relpath(local, carpeta).replace('\\', '/')
            try:
                hashes[rel] = _sha256_generado(local)
            except OSError:
                pass
    return hashes


def leer_manifiesto_deploy(salida: str) -> Dict[str, str]:
    ruta = os.path.join(salida, _MANIFIESTO_DEPLOY)
    if not os.path.isfile(ruta):
        return {}
    try:
        with open(ruta, encoding='utf-8') as f:
            return json.load(f).get('archivos', {})
    except (OSError, ValueError):
        return {}


def escribir_manifiesto_deploy(salida: str, hashes: Dict[str, str]) -> None:
    ruta = os.path.join(salida, _MANIFIESTO_DEPLOY)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump({'subido': _ahora().strftime('%Y-%m-%d %H:%M'),
                   'archivos': hashes}, f, indent=1, ensure_ascii=False)


# ─────────────────────────────────────────────
#  Versionado del zip de backend
# ─────────────────────────────────────────────
_VERSIONES_BACKEND = '.davgen-versiones.json'
_DIR_VERSIONES = '_versiones_backend'
_MAX_VERSIONES_LOCALES = 3


def leer_versiones_backend(salida: str) -> Dict:
    ruta = os.path.join(salida, _VERSIONES_BACKEND)
    if not os.path.isfile(ruta):
        return {'version_actual': 0, 'versiones': []}
    try:
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {'version_actual': 0, 'versiones': []}


def escribir_versiones_backend(salida: str, datos: Dict) -> None:
    ruta = os.path.join(salida, _VERSIONES_BACKEND)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=1, ensure_ascii=False)


def _ultimo_hash_subido(datos: Dict) -> str:
    """Hash del último zip efectivamente subido (None si ninguno todavía)."""
    for v in reversed(datos.get('versiones', [])):
        if v.get('subido'):
            return v.get('hash_zip', '')
    return ''


def _marcar_version_subida(salida: str, build: int, url_api: str) -> None:
    datos = leer_versiones_backend(salida)
    for v in datos.get('versiones', []):
        if v.get('build') == build:
            v['subido'] = _ahora().strftime('%Y-%m-%d %H:%M')
            v['url_api'] = url_api
            break
    escribir_versiones_backend(salida, datos)


def _preparar_zip_versionado(ruta_laravel: str, salida: str):
    """
    Genera servicio.zip, lo guarda como versión numerada local y compara su
    hash con el último zip efectivamente subido a la nube.
    Devuelve (ruta_zip, build, n_archivos, hash_zip, es_nuevo).
    es_nuevo=False → contenido idéntico al último subido; se puede omitir.
    """
    import shutil
    import tempfile

    datos = leer_versiones_backend(salida)
    build = datos.get('version_actual', 0) + 1
    hash_ultimo = _ultimo_hash_subido(datos)

    tmp = os.path.join(tempfile.gettempdir(), 'servicio.zip')
    info("Empaquetando el Laravel completo (con vendor) en servicio.zip…")
    n = _empaquetar_laravel(ruta_laravel, tmp)
    mb = os.path.getsize(tmp) / 1024 / 1024
    hash_nuevo = _sha256(tmp)
    es_nuevo = (hash_nuevo != hash_ultimo)

    dir_v = os.path.join(salida, _DIR_VERSIONES)
    os.makedirs(dir_v, exist_ok=True)
    shutil.copy2(tmp, os.path.join(dir_v, f'servicio-v{build}.zip'))

    def _num_v(nombre: str) -> int:
        s = nombre[len('servicio-v'):-len('.zip')]
        return int(s) if s.isdigit() else 0

    zips = sorted(
        [f for f in os.listdir(dir_v)
         if f.startswith('servicio-v') and f.endswith('.zip')],
        key=_num_v)
    for z in zips[:-_MAX_VERSIONES_LOCALES]:
        try:
            os.remove(os.path.join(dir_v, z))
        except OSError:
            pass

    datos['versiones'].append({
        'build': build, 'davgen': VERSION,
        'generado': _ahora().strftime('%Y-%m-%d %H:%M'),
        'hash_zip': hash_nuevo, 'archivos': n,
        'mb': round(mb, 1), 'subido': None,
    })
    datos['version_actual'] = build
    escribir_versiones_backend(salida, datos)
    ok(f"servicio-v{build}.zip listo — {n} archivo(s), {mb:.1f} MB")
    return tmp, build, n, hash_nuevo, es_nuevo


# ─────────────────────────────────────────────
#  Manifiesto de INTEGRIDAD del código generado en su ubicación FINAL
#  (proyecto Laravel real, frontend, scripts SQL) + inventario de objetos
#  de BD esperados (SPs pcru* y vistas vis_*). Lo usa `davgen verificar`
#  para avisar si el usuario editó a mano algo generado.
# ─────────────────────────────────────────────
_MANIFIESTO_INTEGRIDAD = '.davgen-integridad.json'


def _hashes_de(archivos: List[str], raiz_grupo: str) -> Dict[str, str]:
    """{ruta relativa a `raiz_grupo` con /: hash normalizado} de los archivos
    que existen (ignora la línea @generated, igual que el delta de despliegue)."""
    out = {}
    for a in archivos:
        if a and os.path.isfile(a):
            rel = os.path.relpath(a, raiz_grupo).replace('\\', '/')
            out[rel] = _sha256_generado(a)
    return out


def escribir_manifiesto_integridad(salida: str, raiz: str, tablas: List[Dict],
                                   laravel_raiz: str, laravel_archivos: List[str],
                                   front_raiz, front_archivos: List[str],
                                   database_raiz: str,
                                   database_archivos: List[str]) -> str:
    """Registra el hash de TODO lo generado en su ubicación definitiva más los
    SPs/vistas que la BD debe tener. Las raíces se guardan relativas a la raíz
    del proyecto para que el manifiesto sobreviva a mover/renombrar la carpeta."""
    from .esquema import a_clase

    def _relroot(p):
        return os.path.relpath(p, raiz).replace('\\', '/') if p else None

    datos = {
        'generado': _ahora().strftime('%Y-%m-%d %H:%M'),
        'version': VERSION,
        'laravel': {
            'raiz': _relroot(laravel_raiz),
            'archivos': _hashes_de(laravel_archivos, laravel_raiz) if laravel_raiz else {},
        },
        'frontend': {
            'raiz': _relroot(front_raiz),
            'archivos': _hashes_de(front_archivos, front_raiz) if front_raiz else {},
        },
        'database': {
            'raiz': _relroot(database_raiz),
            'archivos': _hashes_de(database_archivos, database_raiz) if database_raiz else {},
            'procedimientos': sorted(f"pcru{a_clase(t['tabla'])}" for t in tablas),
            'vistas': sorted(t['vista'] for t in tablas if t.get('vista')),
        },
    }
    ruta = os.path.join(salida, _MANIFIESTO_INTEGRIDAD)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=1, ensure_ascii=False)
    return ruta


def _tupla_version(v: str):
    """'4.32.15' → (4, 32, 15). Lo no numérico cuenta como 0 (no revienta)."""
    partes = []
    for p in str(v).split('.')[:3]:
        try:
            partes.append(int(p))
        except ValueError:
            partes.append(0)
    while len(partes) < 3:
        partes.append(0)
    return tuple(partes)


def avisar_version_proyecto(salida: str) -> None:
    """Informa con qué versión de davgen se generó este proyecto por última vez
    y si la versión que corre ahora es distinto.

    v4.36.0 — Nace de un problema real: al 2026-08-17 había proyectos vivos
    generados con 4.17.0, 4.23, 4.26, 4.31.6, 4.32.15, 4.34.4 y 4.35.1, y nada
    lo decía al arrancar. Dos consecuencias vistas:
      · un proyecto en producción se generó el 2026-07-21 con v4.34.4
        aunque v4.35.1 ya existía desde el 2026-07-02 (había una versión vieja en
        la carpeta del proyecto) — se perdió el fix de rutas de testing.
      · un proyecto en producción quedó congelado en v4.23 porque v4.26 cambió
        el esquema de forma incompatible; regenerar rompía la BD y los endpoints.
    Este aviso NO bloquea nada: solo pone el dato a la vista antes de generar.
    """
    ruta = os.path.join(salida, _MANIFIESTO_INTEGRIDAD)
    if not os.path.isfile(ruta):
        return                      # primera generación: no hay con qué comparar
    try:
        with open(ruta, encoding='utf-8') as f:
            previa = str(json.load(f).get('version', '')).strip()
    except (OSError, ValueError):
        return
    if not previa:
        return
    if previa == VERSION:
        dim(f"· generado antes con la MISMA versión (v{VERSION})")
        return
    t_previa, t_actual = _tupla_version(previa), _tupla_version(VERSION)

    if t_previa > t_actual:
        # El caso RARO y el único de verdad peligroso: se está corriendo un .exe
        # viejo sobre un proyecto generado con uno más nuevo. Le pasó a
        # un proyecto en producción (generado con v4.34.4 el 2026-07-21,
        # cuando v4.35.1 existía desde el 2026-07-02).
        warn(f"Este proyecto se generó con davgen v{previa}, MÁS NUEVA que la "
             f"que corre ahora (v{VERSION}) — probablemente estés usando un "
             "davgen viejo (pip install -U davgen). Regenerar lo haría RETROCEDER de versión.")
        return

    # Actualizar hacia adelante es lo normal (es para eso que se regenera), así
    # que NO se grita: un aviso que suena en cada corrida enseña a ignorarlo.
    # Se grita solo cuando el salto es grande — ahí sí cambia bastante código.
    salto_grande = (t_actual[0], t_actual[1]) > (t_previa[0], t_previa[1] + 1)
    texto = (f"Este proyecto se generó con davgen v{previa}; ahora corre "
             f"v{VERSION}: el código generado se ACTUALIZA a la versión nueva.")
    if salto_grande:
        warn(texto + " El salto es de varias versiones — si hay "
             "personalizaciones sobre lo generado, correr `davgen comparar` "
             "antes de desplegar.")
    else:
        info(texto)


def verificar_integridad(salida: str, raiz: str,
                         sps_en_bd=None, vistas_en_bd=None):
    """Compara el código generado en su ubicación final contra el manifiesto.
    Devuelve None si no hay manifiesto (nunca se generó), o un dict con, por
    grupo (laravel/frontend/database), las listas ok/modificados/faltantes, y
    el estado en la BD de los SPs/vistas esperados (si se pasaron los conjuntos
    `sps_en_bd`/`vistas_en_bd`)."""
    ruta = os.path.join(salida, _MANIFIESTO_INTEGRIDAD)
    if not os.path.isfile(ruta):
        return None
    try:
        with open(ruta, encoding='utf-8') as f:
            man = json.load(f)
    except (OSError, ValueError):
        return None

    grupos = {}
    for clave in ('laravel', 'frontend', 'database'):
        g = man.get(clave, {})
        raiz_g = os.path.join(raiz, g['raiz'].replace('/', os.sep)) \
            if g.get('raiz') else None
        ok_, modificados, faltantes = [], [], []
        for rel, h in g.get('archivos', {}).items():
            if not raiz_g:
                faltantes.append(rel)
                continue
            archivo = os.path.join(raiz_g, rel.replace('/', os.sep))
            if not os.path.isfile(archivo):
                faltantes.append(rel)
            elif _sha256_generado(archivo) != h:
                modificados.append(rel)
            else:
                ok_.append(rel)
        grupos[clave] = {'raiz': g.get('raiz'), 'ok': sorted(ok_),
                         'modificados': sorted(modificados),
                         'faltantes': sorted(faltantes)}

    db = man.get('database', {})
    sps_esp = db.get('procedimientos', [])
    vistas_esp = db.get('vistas', [])
    bd_info = None
    if sps_en_bd is not None and vistas_en_bd is not None:
        bd_info = {
            'sps_total': len(sps_esp), 'vistas_total': len(vistas_esp),
            'sps_faltantes': sorted(s for s in sps_esp if s not in sps_en_bd),
            'vistas_faltantes': sorted(v for v in vistas_esp if v not in vistas_en_bd),
        }
    return {'generado': man.get('generado'), 'version': man.get('version'),
            'grupos': grupos, 'bd': bd_info,
            'sps_esperados': sps_esp, 'vistas_esperadas': vistas_esp}


def imprimir_verificacion(resultado: Dict) -> int:
    """Imprime el informe de `verificar_integridad` y devuelve el nº total de
    incidencias (0 = todo el código generado intacto)."""
    _ETIQUETA = {'laravel': 'Backend Laravel (servicio\\)',
                 'frontend': 'Frontend React (src\\)',
                 'database': 'Scripts SQL (database\\)'}
    incidencias = 0
    titulo("VERIFICACIÓN DE INTEGRIDAD — ¿se modificó el código generado?")
    info(f"Última generación: {resultado.get('generado', '?')} "
         f"· davgen v{resultado.get('version', '?')}")
    print()
    for clave in ('laravel', 'frontend', 'database'):
        g = resultado['grupos'].get(clave)
        if not g or (not g['ok'] and not g['modificados'] and not g['faltantes']):
            continue
        total = len(g['ok']) + len(g['modificados']) + len(g['faltantes'])
        print(f"  {C.BOLD}{C.CYAN}{_ETIQUETA[clave]}{C.RESET}  "
              f"({total} archivo(s) generados · raíz: {g['raiz']})")
        if not g['modificados'] and not g['faltantes']:
            ok(f"intacto — los {len(g['ok'])} archivo(s) coinciden con lo generado")
        for rel in g['modificados']:
            print(f"    {C.RED}{C.BOLD}MODIFICADO{C.RESET}  {rel}")
            incidencias += 1
        for rel in g['faltantes']:
            print(f"    {C.YELLOW}FALTANTE  {C.RESET} {rel}")
            incidencias += 1
        if g['ok'] and (g['modificados'] or g['faltantes']):
            dim(f"· {len(g['ok'])} archivo(s) intactos")
        print()

    bd = resultado.get('bd')
    print(f"  {C.BOLD}{C.CYAN}Objetos en la base de datos{C.RESET}")
    if bd is None:
        warn("no se pudo conectar a la BD — no se verificaron SPs ni vistas")
    else:
        if not bd['sps_faltantes']:
            ok(f"los {bd['sps_total']} procedimiento(s) pcru* esperados existen")
        else:
            for sp in bd['sps_faltantes']:
                print(f"    {C.RED}{C.BOLD}SP FALTANTE{C.RESET}  {sp}  "
                      f"(¿se ejecutó 03_procedimientos.sql?)")
                incidencias += 1
        if not bd['vistas_faltantes']:
            ok(f"las {bd['vistas_total']} vista(s) vis_* esperadas existen")
        else:
            for v in bd['vistas_faltantes']:
                print(f"    {C.RED}{C.BOLD}VISTA FALTANTE{C.RESET}  {v}")
                incidencias += 1
    print()

    if incidencias == 0:
        ok("INTEGRIDAD OK — nada del código generado fue modificado.")
    else:
        warn(f"{incidencias} incidencia(s): el código generado fue modificado "
             "o faltan objetos.")
        info("El código generado NO se edita (se regenera y se pierde). "
             "Personalizar extendiendo los Services o en la BD (tbl_seg_*); "
             "para restaurar lo modificado, volver a ejecutar `davgen generar`.")
    return incidencias


def comparar_diferencias(salida: str, raiz: str) -> int:
    """Muestra el diff unificado entre el código generado (copia en
    _backendGenerado/backend/ o /database/) y el archivo en su ubicación
    final. Solo muestra archivos marcados como MODIFICADO por verificar_integridad.
    Devuelve el número de archivos con diferencias."""
    import difflib

    resultado = verificar_integridad(salida, raiz)
    if resultado is None:
        error("No hay manifiesto de integridad (.davgen-integridad.json).")
        info("Ejecutar primero `davgen generar` para crear la línea base.")
        return 0

    titulo("COMPARAR — diff entre código generado y ubicación final")
    info(f"Última generación: {resultado.get('generado', '?')} "
         f"· davgen v{resultado.get('version', '?')}")

    # Dónde vive la copia original generada en _backendGenerado
    _ORIG = {
        'laravel': os.path.join(salida, 'backend'),
        'database': os.path.join(salida, 'database'),
    }
    _ETIQUETA = {
        'laravel': 'Backend Laravel (servicio\\)',
        'frontend': 'Frontend React (src\\)',
        'database': 'Scripts SQL (database\\)',
    }

    total = 0
    for clave in ('laravel', 'frontend', 'database'):
        grupo = resultado['grupos'].get(clave)
        if not grupo:
            continue
        modificados = grupo['modificados']
        faltantes = grupo['faltantes']
        if not modificados and not faltantes:
            continue

        raiz_g_str = grupo.get('raiz', '')
        raiz_g = (os.path.join(raiz, raiz_g_str.replace('/', os.sep))
                  if raiz_g_str else None)

        print(f"\n  {C.BOLD}{C.CYAN}{_ETIQUETA[clave]}{C.RESET}")

        for rel in faltantes:
            print(f"    {C.YELLOW}FALTANTE{C.RESET}  {rel}")
            total += 1

        for rel in modificados:
            print(f"\n  {C.BOLD}{C.RED}MODIFICADO{C.RESET}  {rel}")
            total += 1

            ruta_final = (os.path.join(raiz_g, rel.replace('/', os.sep))
                          if raiz_g else None)
            ruta_orig = (os.path.join(_ORIG[clave], rel.replace('/', os.sep))
                         if clave in _ORIG else None)

            if (ruta_orig and os.path.isfile(ruta_orig)
                    and ruta_final and os.path.isfile(ruta_final)):
                try:
                    with open(ruta_orig, encoding='utf-8', errors='replace') as f:
                        lineas_gen = f.readlines()
                    with open(ruta_final, encoding='utf-8', errors='replace') as f:
                        lineas_fin = f.readlines()
                    diff = list(difflib.unified_diff(
                        lineas_gen, lineas_fin,
                        fromfile=f'generado/{rel}',
                        tofile=f'editado/{rel}',
                        lineterm=''))
                    if diff:
                        for linea in diff[:300]:
                            if linea.startswith('+') and not linea.startswith('+++'):
                                print(f"    {C.GREEN}{linea}{C.RESET}")
                            elif linea.startswith('-') and not linea.startswith('---'):
                                print(f"    {C.RED}{linea}{C.RESET}")
                            else:
                                print(f"    {C.DIM}{linea}{C.RESET}")
                        if len(diff) > 300:
                            warn(f"  … {len(diff) - 300} líneas más omitidas")
                except OSError as exc:
                    warn(f"  No se pudo leer: {exc}")
            else:
                dim("  (copia original no disponible — regenerar para obtener diff)")

    print()
    if total == 0:
        ok("Ningún archivo generado fue modificado — nada que comparar.")
    else:
        warn(f"{total} archivo(s) con diferencias.")
        info("Para restaurar el código generado: volver a ejecutar `davgen generar`.")
        info("Para personalizar sin perder cambios: extender los Services o "
             "usar la BD (tbl_seg_*).")
    return total


def _subir_delta(cfg_ftp: Dict, carpeta_backend: str, salida: str):
    """
    Sube SOLO los archivos generados que cambiaron desde la última subida
    (manifiesto .davgen-deploy.json) y borra del remoto los que ya no se
    generan (tablas eliminadas). Devuelve (exito, detalle).
    """
    actuales = _hashes_generado(carpeta_backend)
    previos = leer_manifiesto_deploy(salida)
    cambiados = [r for r, h in sorted(actuales.items()) if previos.get(r) != h]
    eliminados = [r for r in sorted(previos) if r not in actuales]
    if not cambiados and not eliminados:
        return True, "sin cambios desde la última subida — nada que subir"

    host = _host_ftp(cfg_ftp['host'])
    remota = cfg_ftp['ruta_remota'].rstrip('/')
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, 21, timeout=60)
        ftp.login(cfg_ftp['usuario'], cfg_ftp['password'])
        ftp.set_pasv(True)
    except (ftplib.all_errors, OSError) as e:
        return False, f"FTP no conecta: {e}"

    subidos, errores = 0, []
    nuevo = {r: h for r, h in previos.items() if r in actuales}
    for rel in cambiados:
        partes = rel.split('/')
        rdir = f"{remota}/{'/'.join(partes[:-1])}" if len(partes) > 1 else remota
        try:
            _ftp_mkd_p(ftp, rdir)
            with open(os.path.join(carpeta_backend, *partes), 'rb') as f:
                ftp.storbinary(f'STOR {remota}/{rel}', f)
            subidos += 1
            nuevo[rel] = actuales[rel]
            dim(f"· subido {rel}")
        except (ftplib.all_errors, OSError) as e:
            errores.append(f"{rel}: {e}")
    borrados = 0
    for rel in eliminados:
        try:
            ftp.delete(f"{remota}/{rel}")
            borrados += 1
            dim(f"· borrado del remoto {rel}")
        except ftplib.all_errors:
            pass    # ya no existe en el remoto: igual sale del manifiesto
    try:
        ftp.quit()
    except ftplib.all_errors:
        pass

    escribir_manifiesto_deploy(salida, nuevo)
    detalle = f"delta: {subidos} subido(s)" + \
              (f", {borrados} borrado(s) del remoto" if eliminados else '') + \
              (f", {len(errores)} error(es)" if errores else '')
    for e in errores[:5]:
        dim(f"· {e}")
    return not errores, detalle


# ─────────────────────────────────────────────
#  Archivos de control para comparación incremental
# ─────────────────────────────────────────────
def _es_archivo_control(rel: str) -> bool:
    """True si `rel` (con /) entra en el delta incremental del backend.

    v4.36.0 — AMPLIADO. Antes solo cubría `routes/*.php`, `bootstrap/app.php` y
    `app/Http/Controllers/**`, así que un redespliegue NO subía `app/Services/**`
    (donde vive TODA la lógica: BaseService, los Services por tabla y los
    `Custom/` escritos a mano) ni `app/Providers/**` (donde se registran las
    rutas a medida). El único momento en que esos archivos llegaban al servidor
    era el primer zip completo: después, cambiarlos no desplegaba nada y había
    que subirlos por FTP a mano. Verificado en un proyecto en producción,
    un proyecto en producción y un proyecto en producción.

    Ahora entra todo `app/**` y `routes/**` (PHP) + `bootstrap/app.php`. El
    delta compara hashes: incluir más archivos NO sube más de lo necesario,
    solo deja de OMITIR lo que cambió.
    """
    if rel in ('routes/api.php', 'routes/web.php', 'bootstrap/app.php'):
        return True
    if rel.startswith('routes/') and rel.endswith('.php'):
        return True
    # todo el árbol de la aplicación: Controllers (incl. Custom/), Services
    # (incl. Custom/), Providers, Http/Middleware, Models, Utils…
    if rel.startswith('app/') and rel.endswith('.php'):
        return True
    return False


# Subárboles que davgen NO genera pero que son parte de la app y hay que
# desplegar igual: viven SOLO en el Laravel real, no en el espejo
# `_backendGenerado\backend`, así que recorrer el espejo nunca los ve.
def _es_archivo_propio(rel: str) -> bool:
    """Regla por RUTA de las versiones 4.x (`Custom/` dentro de app y
    `app/Providers/`). Se conserva solo para leer manifiestos de despliegue
    antiguos, que no marcaban los archivos propios."""
    if not rel.endswith('.php'):
        return False
    if rel.startswith('app/Providers/'):
        return True
    return rel.startswith('app/') and '/Custom/' in rel


# Marca que llevan los hashes de código propio en .davgen-deploy.json: permite
# saber, en el siguiente despliegue, que ese archivo NO lo generó davgen y que
# por lo tanto nunca debe borrarse del servidor por no encontrarlo en local.
_MARCA_PROPIO = 'propio:'


def _es_generado(ruta_local: str) -> bool:
    """True si el archivo lleva la cabecera `@generated davgen`."""
    try:
        with open(ruta_local, 'rb') as f:
            return b'@generated davgen' in f.read(600)
    except OSError:
        return False


def _es_codigo_propio(rel: str, ruta_local: str) -> bool:
    """True si `rel` es código PHP del usuario que el delta debe llevar.

    v5.0.0 — por CONTENIDO, no por nombre de carpeta: es propio todo `.php` de
    `app/**`, `routes/**` o `bootstrap/providers.php` del Laravel real que NO
    lleve la cabecera `@generated davgen`. La regla anterior solo veía
    `app/**/Custom/**` y `app/Providers/**`, y cada proyecto guarda su código
    en un sitio distinto (`routes/Custom/`, `routes/dominio_api.php`,
    `app/Dominio/`, `routes/cliente.php`…): esos archivos no viajaban nunca y
    la API quedaba en 404/500 hasta subirlos a mano.
    Un archivo CON cabecera que ya no está en el espejo es un resto de una
    tabla eliminada: no es propio y no se sube.
    """
    if not rel.endswith('.php'):
        return False
    if not (rel.startswith('app/') or rel.startswith('routes/')
            or rel == 'bootstrap/providers.php'):
        return False
    return not _es_generado(ruta_local)


def _hashes_control(carpeta: str, ruta_laravel: str = ''):
    """Hashes de los archivos que entran al delta, con su ruta LOCAL de origen.

    Dos orígenes, en este orden de prioridad:
      1. `carpeta` — el espejo generado (`_backendGenerado\\backend`): manda,
         porque es exactamente lo que davgen acaba de producir.
      2. `ruta_laravel` — el proyecto Laravel real: aporta SOLO el código propio
         (todo PHP de app/ y routes/ sin cabecera `@generated`) que no existe
         en el espejo. Su hash se guarda con el prefijo `propio:`.

    Devuelve (hashes: {rel: hash}, origenes: {rel: ruta_local_absoluta}).
    """
    hashes, origenes = {}, {}

    def _recorrer(base: str, filtro, marca: str = ''):
        for raiz, dirs, archivos in os.walk(base):
            dirs[:] = sorted(d for d in dirs
                             if d not in ('vendor', 'node_modules', 'storage'))
            for nombre in sorted(archivos):
                local = os.path.join(raiz, nombre)
                rel = os.path.relpath(local, base).replace('\\', '/')
                if rel in hashes or not filtro(rel, local):
                    continue
                try:
                    hashes[rel] = marca + _sha256_generado(local)
                    origenes[rel] = local
                except OSError:
                    pass

    _recorrer(carpeta, lambda rel, _local: _es_archivo_control(rel))
    if ruta_laravel and os.path.isdir(ruta_laravel) \
            and os.path.normcase(os.path.abspath(ruta_laravel)) != \
            os.path.normcase(os.path.abspath(carpeta)):
        _recorrer(ruta_laravel, _es_codigo_propio, _MARCA_PROPIO)
    return hashes, origenes


def _subir_delta_control(cfg_ftp: Dict, carpeta_backend: str, salida: str,
                         ruta_laravel: str = ''):
    """
    Despliegue incremental de `app/**` + `routes/**` + `bootstrap/app.php`
    comparados contra .davgen-deploy.json. Con `ruta_laravel` incluye además el
    código PROPIO (`Custom/`, `Providers/`) que solo existe en el Laravel real.
    Devuelve (exito, detalle).
    """
    actuales, origenes = _hashes_control(carpeta_backend, ruta_laravel)
    previos = leer_manifiesto_deploy(salida)

    cambiados = [r for r, h in sorted(actuales.items()) if previos.get(r) != h]
    # Un archivo que estaba en el manifiesto y ya no existe se borra del remoto.
    # OJO: solo si era de CONTROL (generado). El código propio nunca se borra
    # del servidor por no encontrarlo — puede faltar porque se movió la carpeta.
    eliminados = [r for r in sorted(previos)
                  if r not in actuales and _es_archivo_control(r)
                  and not str(previos[r]).startswith(_MARCA_PROPIO)
                  and not _es_archivo_propio(r)]

    if not cambiados and not eliminados:
        return True, "sin cambios en archivos de control — nada que subir"

    host = _host_ftp(cfg_ftp['host'])
    remota = cfg_ftp['ruta_remota'].rstrip('/')
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, 21, timeout=60)
        ftp.login(cfg_ftp['usuario'], cfg_ftp['password'])
        ftp.set_pasv(True)
    except (ftplib.all_errors, OSError) as e:
        return False, f"FTP no conecta: {e}"

    subidos, errores = 0, []
    nuevo = dict(previos)
    for rel in cambiados:
        partes = rel.split('/')
        rdir = f"{remota}/{'/'.join(partes[:-1])}" if len(partes) > 1 else remota
        try:
            _ftp_mkd_p(ftp, rdir)
            # la ruta local sale de `origenes`: puede ser el espejo generado o
            # el Laravel real (código propio), no siempre carpeta_backend
            with open(origenes[rel], 'rb') as f:
                ftp.storbinary(f'STOR {remota}/{rel}', f)
            subidos += 1
            nuevo[rel] = actuales[rel]
            dim(f"· subido {rel}")
        except (ftplib.all_errors, OSError) as e:
            errores.append(f"{rel}: {e}")
    borrados = 0
    for rel in eliminados:
        try:
            ftp.delete(f"{remota}/{rel}")
            borrados += 1
            dim(f"· borrado del remoto {rel}")
        except ftplib.all_errors:
            pass
    try:
        ftp.quit()
    except ftplib.all_errors:
        pass

    escribir_manifiesto_deploy(salida, nuevo)
    # los despliegues hechos con versiones anteriores no traen la protección
    # de la carpeta publicada: se asegura en cada despliegue (es idempotente)
    prot = proteger_remoto(cfg_ftp)
    if prot['error']:
        errores.append(f"protección de la carpeta publicada: {prot['error']}")
    elif prot['raiz'] != 'ya estaba':
        dim(f"· protección de la carpeta publicada {prot['raiz']} (.htaccess)")
    detalle = f"control: {subidos} subido(s)" + \
              (f", {borrados} borrado(s) del remoto" if eliminados else '') + \
              (f", {len(errores)} error(es)" if errores else '')
    for e in errores[:5]:
        dim(f"· {e}")
    return not errores, detalle


def _subir(cfg_ftp: Dict, carpeta_backend: str):
    """Sube archivo por archivo el código generado (app\\** + routes\\)."""
    host = _host_ftp(cfg_ftp['host'])
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, 21, timeout=30)
        ftp.login(cfg_ftp['usuario'], cfg_ftp['password'])
    except (ftplib.all_errors, OSError) as e:
        return False, 0, [str(e)]

    remota = cfg_ftp['ruta_remota'].rstrip('/')
    trabajos = []
    for raiz, dirs, archivos in os.walk(carpeta_backend):
        dirs.sort()
        for nombre in sorted(archivos):
            local = os.path.join(raiz, nombre)
            rel = os.path.relpath(local, carpeta_backend).replace('\\', '/')
            partes = rel.split('/')
            rdir = f"{remota}/{'/'.join(partes[:-1])}" if len(partes) > 1 else remota
            trabajos.append((local, f"{remota}/{rel}", rdir))

    subidos, errores = 0, []
    for i, (local, remoto, rdir) in enumerate(trabajos, 1):
        try:
            _ftp_mkd_p(ftp, rdir)
            with open(local, 'rb') as f:
                ftp.storbinary(f'STOR {remoto}', f)
            subidos += 1
        except (ftplib.all_errors, OSError) as e:
            errores.append(f"{remoto}: {e}")
    try:
        ftp.quit()
    except ftplib.all_errors:
        pass
    return not errores, subidos, errores


def _subir_zip(cfg_ftp: Dict, ruta_laravel: str, bd: Dict,
               salida: str, no_interactivo: bool = False):
    """
    Primer despliegue: prepara el .env (BD nube + APP_URL), genera el zip
    versionado, lo compara con el último subido y —si son iguales— pregunta
    antes de continuar. Sube servicio.zip + descomprimir.php y dispara la
    extracción por HTTP. Devuelve (exito, mensaje, url_api).
    """
    import secrets
    import tempfile
    import urllib.request

    url = cfg_ftp.get('url', '')
    _preparar_env_produccion(ruta_laravel, bd, url, cfg_ftp.get('ruta_remota', ''))

    # Generar zip versionado y comparar hash con el último subido
    tmp, build, n, _hash, es_nuevo = _preparar_zip_versionado(ruta_laravel, salida)
    mb = os.path.getsize(tmp) / 1024 / 1024

    if not es_nuevo:
        warn(f"servicio-v{build}.zip es IDÉNTICO al último zip subido a la nube.")
        continuar = False
        if not no_interactivo:
            continuar = confirmar(
                "¿Subir de todas formas? (el backend en la nube ya está actualizado)",
                defecto=False)
        if not continuar:
            info(f"Subida omitida — build {build} idéntico al último desplegado.")
            return True, f"omitido — zip idéntico al último subido (build {build})", \
                _url_api_nube(cfg_ftp)

    token = secrets.token_hex(16)
    php = _DESCOMPRIMIR_PHP.replace('{token}', token)
    tmp_php = os.path.join(tempfile.gettempdir(), 'descomprimir.php')
    with open(tmp_php, 'w', encoding='utf-8') as f:
        f.write(php)

    host = _host_ftp(cfg_ftp['host'])
    remota = cfg_ftp['ruta_remota'].rstrip('/')
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, 21, timeout=60)
        ftp.login(cfg_ftp['usuario'], cfg_ftp['password'])
        ftp.set_pasv(True)
    except (ftplib.all_errors, OSError) as e:
        return False, f"FTP no conecta: {e}", ''
    _ftp_mkd_p(ftp, remota)
    # borrar archivos de enrutamiento de un despliegue anterior: si un
    # .htaccess viejo enruta todo a public/, bloquearía descomprimir.php
    for viejo in ('.htaccess', 'index.php'):
        try:
            ftp.delete(f"{remota}/{viejo}")
        except ftplib.all_errors:
            pass
    try:
        info(f"Subiendo servicio-v{build}.zip → {remota} ({mb:.1f} MB, puede tardar)…")
        with open(tmp, 'rb') as f:
            ftp.storbinary(f'STOR {remota}/servicio.zip', f)
        with open(tmp_php, 'rb') as f:
            ftp.storbinary(f'STOR {remota}/descomprimir.php', f)
        ok("servicio.zip y descomprimir.php subidos")
    except (ftplib.all_errors, OSError) as e:
        return False, f"Error al subir: {e}", ''
    finally:
        try:
            ftp.quit()
        except ftplib.all_errors:
            pass

    if not url:
        return True, (f"subido build {build} (sin [ftp] url: ejecutar manualmente "
                      f"{remota}/descomprimir.php?token={token})"), ''
    base = url.rstrip('/')
    sub = remota.strip('/').split('/')[-1] if remota.strip('/') else ''
    base_deploy = f"{base}/{sub}" if sub and sub not in base else base
    url_descomprimir = f"{base_deploy}/descomprimir.php?token={token}"
    info(f"Descomprimiendo en el servidor: {url_descomprimir}")
    url_api = f"{base_deploy}/api"
    try:
        with urllib.request.urlopen(url_descomprimir, timeout=120) as resp:
            cuerpo = resp.read().decode('utf-8', 'replace')[:200]
        ok(f"Descompresión: {cuerpo}")
        _marcar_version_subida(salida, build, url_api)
        return True, f"desplegado build {build} ({n} archivos)", url_api
    except Exception as e:
        return True, (f"subido build {build}; descompresión manual: "
                      f"{url_descomprimir} ({e})"), url_api


def _url_api_nube(cfg_ftp: Dict) -> str:
    """URL de la API desplegada: {url}/{ultima carpeta de ruta_remota}/api."""
    url = (cfg_ftp.get('url') or '').rstrip('/')
    if not url:
        return ''
    sub = (cfg_ftp.get('ruta_remota') or '').strip('/').split('/')[-1]
    return f"{url}/{sub}/api" if sub and sub not in url else f"{url}/api"


# ─────────────────────────────────────────────
#  Versionado del frontend React
# ─────────────────────────────────────────────
_VERSIONES_FRONT = '.davgen-versiones-front.json'


#  Carpetas que NO entran al hash del frontend (no llegan al build, o son
#  salida del build): dependencias, artefactos y metadatos.
_EXCLUIR_FRONT = {'node_modules', 'dist', 'build', '.git', '.vite',
                  'android', 'ios', '.idea', '.vscode'}

#  Archivos de la RAÍZ del proyecto React que cambian el resultado del build.
#  `.env` NO va acá a propósito: `desplegar_frontend` lo REESCRIBE (VITE_API_URL)
#  DESPUÉS de calcular el hash, así que incluirlo daría un cambio falso en cada
#  corrida alterna. La parte que importa (la URL de la API) ya entra al hash por
#  separado, vía `_hash_fuentes_combinado(..., url_api)`.
_RAIZ_FRONT = ('index.html', 'package.json', 'vite.config.js',
               'vite.config.ts', 'tailwind.config.js', 'postcss.config.js')


def _es_fuente_front(rel: str) -> bool:
    """True si `rel` (con /) influye en el build del frontend.

    v4.36.0 — REESCRITO. La versión anterior solo miraba `src/routes.jsx`,
    `src/services/*Service.js` y `src/pages/*.jsx` con `len(partes) == 3`, o sea:

      · `src/routes.jsx` NO EXISTE — el archivo real es
        `src/pages/generados/rutas.jsx`, que con 4 segmentos tampoco entraba.
      · `src/pages/generados/*.jsx` (las páginas CRUD generadas) quedaban FUERA.
      · `src/App.jsx`, `src/components/**`, `src/lib/**`, los `.css` y todo
        `public/**` quedaban FUERA.

    Consecuencia: se cambiaba la app y el hash no se movía, así que el
    despliegue avisaba «fuentes idénticas» y NO subía. Verificado en
    un proyecto en producción (un `public/.htaccess` nuevo) y en
    un proyecto en producción y un proyecto en producción (App.jsx,
    componentes y estilos propios). El único síntoma visible era que la app en
    la nube seguía vieja sin ningún mensaje de error.

    Ahora entra TODO lo que el build consume: `src/**`, `public/**` y los
    archivos de configuración de la raíz.
    """
    partes = rel.split('/')
    if partes[0] in _EXCLUIR_FRONT:
        return False
    if partes[0] in ('src', 'public'):
        return True
    return len(partes) == 1 and rel in _RAIZ_FRONT


def _hashes_front_control(ruta_front: str) -> Dict[str, str]:
    """Hashes de TODO lo que entra al build del frontend (src, public y
    configuración de la raíz). Ver `_es_fuente_front`."""
    hashes = {}
    if not os.path.isdir(ruta_front):
        return hashes
    for raiz, dirs, archivos in os.walk(ruta_front):
        dirs[:] = sorted(d for d in dirs if d not in _EXCLUIR_FRONT)
        for nombre in sorted(archivos):
            local = os.path.join(raiz, nombre)
            rel = os.path.relpath(local, ruta_front).replace('\\', '/')
            if _es_fuente_front(rel):
                try:
                    hashes[rel] = _sha256_generado(local)
                except OSError:
                    pass
    return hashes


def _hash_fuentes_combinado(hashes: Dict[str, str], url_api: str) -> str:
    """Hash único que representa el estado de los fuentes de control + la URL
    de la API destino (si cambia la URL, el frontend necesita recompilarse)."""
    datos = json.dumps({**hashes, '__url_api__': url_api}, sort_keys=True)
    return hashlib.sha256(datos.encode()).hexdigest()


def leer_versiones_front(salida: str) -> Dict:
    ruta = os.path.join(salida, _VERSIONES_FRONT)
    if not os.path.isfile(ruta):
        return {'version_actual': 0, 'versiones': []}
    try:
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {'version_actual': 0, 'versiones': []}


def escribir_versiones_front(salida: str, datos: Dict) -> None:
    ruta = os.path.join(salida, _VERSIONES_FRONT)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=1, ensure_ascii=False)


def _ultimo_hash_front(datos: Dict) -> str:
    for v in reversed(datos.get('versiones', [])):
        if v.get('subido'):
            return v.get('hash_fuentes', '')
    return ''


def _marcar_version_front_subida(salida: str, build: int,
                                  url_front: str, subidos: int) -> None:
    datos = leer_versiones_front(salida)
    for v in datos.get('versiones', []):
        if v.get('build') == build:
            v['subido'] = _ahora().strftime('%Y-%m-%d %H:%M')
            v['url_front'] = url_front
            v['archivos_subidos'] = subidos
            break
    escribir_versiones_front(salida, datos)


def desplegar_frontend(cfg: Dict, ruta_front: str):
    """
    Despliega el React a la nube, A LA MISMA ALTURA que la carpeta del
    backend (raíz del FTP): fija VITE_API_URL a la API en la nube, compara
    TODAS las fuentes del build (src\\**, public\\** y la configuración de la
    raíz) con la última versión subida — si son idénticas pregunta antes de
    compilar. Hace `npm run build` y sube dist/* al directorio PADRE de
    ruta_remota. `ruta_front` = carpeta del proyecto React (con package.json).
    Devuelve (exito, mensaje, url_front).
    """
    import shutil
    import subprocess

    cfg_ftp = cfg['ftp']
    url_api = _url_api_nube(cfg_ftp)
    if not url_api:
        return False, "falta [ftp] url para apuntar el frontend a la nube", ''

    salida = cfg.get('salida', '')
    no_interactivo = cfg.get('_no_interactivo', False)

    # 1 · Comparar fuentes de control con la última versión subida
    if salida:
        datos_v = leer_versiones_front(salida)
        build = datos_v.get('version_actual', 0) + 1
        hash_ultimo = _ultimo_hash_front(datos_v)
        hashes_act = _hashes_front_control(ruta_front)
        hash_nuevo = _hash_fuentes_combinado(hashes_act, url_api)
        es_nuevo = (hash_nuevo != hash_ultimo)

        if not es_nuevo:
            warn("Las fuentes del frontend son IDÉNTICAS a las de la última "
                 "subida (src\\**, public\\**, configuración y VITE_API_URL).")
            continuar = False
            if not no_interactivo:
                continuar = confirmar(
                    "¿Compilar y subir de todas formas? "
                    "(el frontend en la nube ya está actualizado)",
                    defecto=False)
            if not continuar:
                info(f"Subida omitida — frontend build {build} sin cambios.")
                url_front = (cfg_ftp.get('url') or '').rstrip('/') + '/'
                return True, f"omitido — fuentes idénticas a la última subida (build {build})", \
                    url_front

        # Registrar la versión (pendiente de marcar como subida)
        datos_v['versiones'].append({
            'build': build, 'davgen': VERSION,
            'generado': _ahora().strftime('%Y-%m-%d %H:%M'),
            'hash_fuentes': hash_nuevo,
            'archivos_control': len(hashes_act),
            'subido': None,
        })
        datos_v['version_actual'] = build
        escribir_versiones_front(salida, datos_v)
    else:
        build = 0

    # 2 · .env del frontend → API en la nube
    # v4.36.0 — se PRESERVAN las demás claves. Antes se reescribía el archivo
    # entero con una sola línea, así que cualquier VITE_* propia del proyecto
    # (claves de mapas, flags de UI, etc.) desaparecía en cada despliegue y el
    # build salía sin ellas. Se lee con utf-8-sig por el BOM de PowerShell.
    ruta_env = os.path.join(ruta_front, '.env')
    otras = []
    if os.path.isfile(ruta_env):
        try:
            with open(ruta_env, encoding='utf-8-sig') as f:
                otras = [ln for ln in f.read().splitlines()
                         if ln.strip() and not ln.strip().startswith('VITE_API_URL')]
        except OSError:
            otras = []
    with open(ruta_env, 'w', encoding='utf-8') as f:
        f.write('\n'.join([f"VITE_API_URL={url_api}"] + otras) + '\n')
    ok(f"VITE_API_URL={url_api}"
       + (f"  ({len(otras)} otra(s) clave(s) conservada(s))" if otras else ''))

    # 3 · build de producción
    if not shutil.which('npm'):
        return False, "npm no está instalado: no se puede construir el React", ''
    info(f"Construyendo frontend build {build} (npm run build)…")
    r = subprocess.run('npm run build', cwd=ruta_front, shell=True,
                       capture_output=True, text=True, timeout=900)
    dist = os.path.join(ruta_front, 'dist')
    if r.returncode != 0 or not os.path.isdir(dist):
        return False, f"npm run build falló: {(r.stderr or r.stdout)[-300:]}", ''
    ok("dist/ construido")

    # 4 · subir dist/* a la RAÍZ (padre de ruta_remota) por FTP
    host = _host_ftp(cfg_ftp['host'])
    remota = cfg_ftp['ruta_remota'].rstrip('/')
    raiz_remota = remota.rsplit('/', 1)[0] or '/'   # padre de /servicio → /
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, 21, timeout=60)
        ftp.login(cfg_ftp['usuario'], cfg_ftp['password'])
        ftp.set_pasv(True)
    except (ftplib.all_errors, OSError) as e:
        return False, f"FTP no conecta: {e}", ''
    subidos, errores = 0, []
    for base, _dirs, archivos in os.walk(dist):
        rel_dir = os.path.relpath(base, dist).replace('\\', '/')
        destino_dir = raiz_remota if rel_dir == '.' else f"{raiz_remota}/{rel_dir}"
        _ftp_mkd_p(ftp, destino_dir)
        for nombre in archivos:
            local = os.path.join(base, nombre)
            try:
                with open(local, 'rb') as fh:
                    ftp.storbinary(f"STOR {destino_dir}/{nombre}", fh)
                subidos += 1
            except (ftplib.all_errors, OSError) as e:
                errores.append(str(e))
    try:
        ftp.quit()
    except ftplib.all_errors:
        pass
    if errores:
        return False, f"{subidos} subidos, {len(errores)} error(es): {errores[0]}", ''
    url_front = (cfg_ftp.get('url') or '').rstrip('/') + '/'
    if salida and build:
        _marcar_version_front_subida(salida, build, url_front, subidos)
    return True, f"build {build} — {subidos} archivo(s) subidos", url_front


def decidir_frontend(cfg: Dict, no_interactivo: bool, forzar: str = 'preguntar'):
    """Pregunta (o decide por `forzar`) si desplegar el React a la nube."""
    titulo("FRONTEND — ¿desplegar la app React a la nube?")
    decision = forzar
    if decision == 'preguntar':
        if no_interactivo:
            decision = 'no'
            info("Modo no interactivo: el frontend NO se despliega "
                 "(usar --front si).")
        else:
            decision = 'si' if confirmar(
                "¿Desplegar el frontend React a la nube (junto a la carpeta "
                "del backend)?", defecto=False) else 'no'
    if decision != 'si':
        info("El frontend NO se despliega a la nube.")
        return
    ruta_front = cfg.get('ruta_front')
    if not ruta_front:
        warn("No hay proyecto React (04-Front*) para desplegar.")
        return
    if not cfg.get('ftp_listo'):
        warn("Sección [ftp] incompleta — no se puede desplegar el frontend.")
        return
    # propagar no_interactivo a desplegar_frontend vía cfg (sin cambiar firma)
    cfg['_no_interactivo'] = no_interactivo
    exito, detalle, url_front = desplegar_frontend(cfg, ruta_front)
    cfg.pop('_no_interactivo', None)
    (ok if exito else warn)(
        f"Frontend {'DESPLEGADO' if exito else 'con errores'} — {detalle}")
    if exito and url_front:
        info(f"App en: {url_front}  (apunta a la API en /servicio)")
    salida = cfg.get('salida', '')
    if salida:
        estado = ('SÍ — ' if exito else 'ERROR — ') + detalle
        with open(os.path.join(salida, 'RESUMEN.md'), 'a', encoding='utf-8') as f:
            f.write(f"\n## Frontend\n\n| Campo | Valor |\n|---|---|\n"
                    f"| ¿Frontend subido? | **{estado}** |\n"
                    f"| Fecha | {_ahora().strftime('%Y-%m-%d %H:%M')} |\n")


def decidir_produccion(ctx: Dict, cfg: Dict, no_interactivo: bool,
                       forzar: str = 'preguntar') -> None:
    """forzar: 'si' | 'no' | 'preguntar'. Deja constancia en RESUMEN.md."""
    titulo("PRODUCCIÓN — ¿subir el backend?")
    decision = forzar
    if decision == 'preguntar':
        if no_interactivo:
            decision = 'no'
            info("Modo no interactivo: no se sube a producción.")
        else:
            decision = 'si' if confirmar(
                "¿Subir el backend a producción por FTP?", defecto=False) else 'no'

    detalle = ''
    if decision == 'si':
        if not cfg.get('ftp_listo'):
            decision, detalle = 'no', ('sin sección [ftp] completa en config.ini — '
                                       'llenarla y volver a ejecutar con --produccion si')
            warn(f"NO se sube: {detalle}")
        else:
            ruta_laravel = cfg.get('ruta_laravel')
            carpeta_generado = ctx.get('ruta_backend') or \
                os.path.join(ctx['salida'], 'backend')
            if (os.path.isdir(carpeta_generado)
                    and _despliegue_remoto_existe(cfg['ftp'])):
                # la carpeta remota YA tiene el Laravel desplegado:
                # despliegue INCREMENTAL — solo archivos de control
                # (routes/api.php, controllers, services) comparados contra
                # .davgen-deploy.json
                info("La carpeta remota ya tiene un despliegue — delta "
                     "incremental de app\\** + routes\\** (incluye Services, "
                     "Providers y Custom\\ propios)")
                exito, detalle = _subir_delta_control(cfg['ftp'], carpeta_generado,
                                                      ctx['salida'],
                                                      ruta_laravel or '')
                (ok if exito else warn)(
                    f"Backend {'ACTUALIZADO' if exito else 'con errores'} — {detalle}")
                url_api = _url_api_nube(cfg['ftp'])
                if exito and url_api:
                    info(f"API en: {url_api}  (login: POST {url_api}/auth/login)")
            elif ruta_laravel and os.path.isfile(
                    os.path.join(ruta_laravel, 'public', 'index.php')):
                # primer despliegue: Laravel completo en zip versionado → subir
                # → descomprimir en el servidor (omite si es idéntico al último)
                exito, detalle, url_api = _subir_zip(
                    cfg['ftp'], ruta_laravel, cfg['bd'],
                    ctx['salida'], no_interactivo)
                (ok if exito else warn)(
                    f"Backend {'DESPLEGADO' if exito else 'con errores'} — {detalle}")
                if url_api:
                    info(f"API en: {url_api}  (login: POST {url_api}/auth/login)")
                if exito and os.path.isdir(carpeta_generado):
                    # línea base del delta: lo que viaja dentro del zip
                    escribir_manifiesto_deploy(
                        ctx['salida'], _hashes_generado(carpeta_generado))
            else:
                carpeta = ctx.get('ruta_backend') or os.path.join(ctx['salida'], 'backend')
                info(f"Subiendo código generado → {cfg['ftp']['host']}{cfg['ftp']['ruta_remota']}")
                exito, subidos, errores = _subir(cfg['ftp'], carpeta)
                detalle = f"{subidos} archivo(s) subido(s)" + \
                          (f", {len(errores)} error(es)" if errores else '')
                (ok if exito else warn)(
                    f"Backend {'SUBIDO' if exito else 'con errores'} — {detalle}")
                for e in errores[:5]:
                    dim(f"· {e}")
    if decision == 'no' and not detalle:
        detalle = 'decisión del usuario / por defecto'
        info("El backend NO se sube a producción.")
        dim("Para subir después: completar [ftp] en config.ini y ejecutar con --produccion si")

    estado = ('SÍ — ' if decision == 'si' else 'NO — ') + detalle
    with open(os.path.join(ctx['salida'], 'RESUMEN.md'), 'a', encoding='utf-8') as f:
        f.write(f"\n## Producción\n\n| Campo | Valor |\n|---|---|\n"
                f"| ¿Backend subido a producción? | **{estado}** |\n"
                f"| Fecha de decisión | {_ahora().strftime('%Y-%m-%d %H:%M')} |\n")
    color = C.GREEN if decision == 'si' else C.YELLOW
    print(f"\n  {C.BOLD}Backend en producción: {color}"
          f"{'SÍ' if decision == 'si' else 'NO'}{C.RESET}{C.DIM} ({detalle}){C.RESET}\n")
