"""diagnostico.py — requisitos del proyecto y por qué no conecta algo.

Reúne lo que más veces trabó a los proyectos reales (no se podía entrar a
MySQL, el FTP no desplegaba, el botón de Google no aparecía) y lo convierte en
comprobaciones con una causa probable y un «qué hacer» concreto, en vez de un
mensaje de error en inglés del controlador.

Nada de aquí escribe en la base ni en el servidor: abre la conexión, mira y
cierra.
"""
import ftplib
import os
import socket
from typing import Dict, List, Tuple

from . import bd as _bd

# (estado, título, detalle, qué hacer)   estado: 'ok' | 'aviso' | 'falta'
Punto = Tuple[str, str, str, str]


def _host_ftp(host: str) -> str:
    return host.replace('ftp://', '').replace('ftps://', '').strip('/').split('/')[0]


# ── base de datos ───────────────────────────────────────────────────────────
def explicar_error_bd(exc: Exception, datos: Dict) -> Tuple[str, str]:
    """(causa probable, qué hacer) para un error al conectar a MySQL/MariaDB."""
    codigo = exc.args[0] if exc.args and isinstance(exc.args[0], int) else None
    texto = str(exc)
    host = datos.get('host', '')
    local = host in ('localhost', '127.0.0.1', '::1')
    if isinstance(exc, _bd.SinControlador):
        return ('no hay controlador de MySQL instalado', 'pip install pymysql')
    if isinstance(exc, socket.gaierror) or 'getaddrinfo' in texto or 'Name or service' in texto:
        return (f'el nombre «{host}» no se resuelve (DNS)',
                'revisar [bd] host; si la red no resuelve el dominio, usar la IP del servidor')
    if codigo == 2003 or isinstance(exc, (ConnectionRefusedError, TimeoutError, socket.timeout)) \
            or 'timed out' in texto or 'refused' in texto:
        if local:
            return ('MySQL no está iniciado en esta PC (o usa otro puerto)',
                    'iniciar MySQL (XAMPP / Laragon / servicio de Windows) y revisar [bd] puerto')
        return (f'no hay respuesta de {host}:{datos.get("puerto", 3306)}',
                'el hosting debe permitir la conexión REMOTA a MySQL desde tu IP '
                '(panel del hosting → «MySQL remoto»); revisar host, puerto y firewall')
    if codigo == 1045:
        return ('usuario o contraseña rechazados',
                'revisar [bd] usuario y password' + ('' if local else
                 '; en hosting compartido el usuario lleva el prefijo de la cuenta y la '
                 'IP de tu PC debe estar autorizada para ese usuario'))
    if codigo == 1044:
        return (f'el usuario no tiene permisos sobre «{datos.get("database", "")}»',
                'asignar el usuario a esa base (todos los privilegios) en el panel de MySQL')
    if codigo == 1049:
        return (f'la base «{datos.get("database", "")}» no existe',
                'crearla (utf8mb4) o corregir [bd] database')
    limite = _bd.explicar_limite(exc)
    if limite:
        return limite
    return (texto[:160], 'revisar la sección [bd] del archivo de acceso del entorno')


def probar_bd(datos: Dict, timeout: int = 10) -> Punto:
    if not (datos.get('host') and datos.get('usuario') and datos.get('database')):
        return ('aviso', 'Base de datos', 'sin configurar',
                'completar [bd] en el archivo de acceso del entorno')
    try:
        conn = _bd.conectar(datos, timeout=timeout)
    except Exception as e:                          # noqa: BLE001
        causa, hacer = explicar_error_bd(e, datos)
        return ('falta', 'Base de datos', f'no conecta — {causa}', hacer)
    try:
        cur = conn.cursor()
        cur.execute('SELECT VERSION()')
        version = _bd.texto(cur.fetchall()[0][0])
        cur.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s "
                    "AND TABLE_NAME LIKE 'tbl\\_seg\\_%%'", (datos['database'],))
        seg = int(cur.fetchall()[0][0])
    finally:
        conn.close()
    detalle = f"«{datos['database']}» en {datos['host']} · {version}"
    if seg == 0:
        return ('aviso', 'Base de datos', detalle + ' · sin tablas de seguridad',
                'crearlas con `davgen seguridad`')
    return ('ok', 'Base de datos', detalle + f' · {seg} tablas de seguridad', '')


# ── FTP ─────────────────────────────────────────────────────────────────────
def explicar_error_ftp(exc: Exception, datos: Dict) -> Tuple[str, str]:
    texto = str(exc)
    host = _host_ftp(datos.get('host', ''))
    if isinstance(exc, socket.gaierror) or 'getaddrinfo' in texto:
        return (f'el nombre «{host}» no se resuelve (DNS)',
                'usar la IP del servidor FTP en [ftp] host (dato del panel del hosting)')
    if isinstance(exc, ftplib.error_perm) and texto.startswith('530'):
        return ('usuario o contraseña del FTP rechazados',
                'revisar [ftp] usuario y password; en hosting compartido el usuario suele '
                'ser «cuenta.usuario» y la contraseña es la de la CUENTA FTP, no la del panel')
    if isinstance(exc, (TimeoutError, socket.timeout, ConnectionRefusedError)) or 'timed out' in texto:
        return (f'no hay respuesta de {host}:21',
                'la red o un firewall bloquea el FTP (probar otra red); confirmar el host')
    if isinstance(exc, ftplib.error_perm) and texto.startswith('550'):
        return ('la carpeta remota no existe todavía', 'es normal antes del primer despliegue')
    return (texto[:160], 'revisar la sección [ftp] del archivo de acceso de producción')


def probar_ftp(datos: Dict, timeout: int = 15) -> Punto:
    if not (datos.get('host') and datos.get('usuario') and datos.get('password')):
        return ('aviso', 'FTP', 'sin configurar',
                'completar [ftp] en _acceso.produccion.ini (solo hace falta para publicar)')
    host = _host_ftp(datos['host'])
    ftp = ftplib.FTP()
    try:
        ftp.connect(host, 21, timeout=timeout)
        ftp.login(datos['usuario'], datos['password'])
        ftp.set_pasv(True)
    except (ftplib.all_errors, OSError) as e:
        causa, hacer = explicar_error_ftp(e, datos)
        return ('falta', 'FTP', f'no conecta — {causa}', hacer)
    try:
        remota = datos.get('ruta_remota') or '/servicio'
        try:
            ftp.cwd(remota)
            desplegado = True
        except ftplib.error_perm:
            desplegado = False
    finally:
        try:
            ftp.quit()
        except ftplib.all_errors:
            pass
    detalle = f"{datos['usuario']}@{host} · {remota} " + (
        'ya tiene un despliegue' if desplegado else 'aún no existe (primer despliegue)')
    url = datos.get('url', '')
    if not url:
        return ('aviso', 'FTP', detalle, 'falta [ftp] url (https://…): se necesita para publicar')
    if url.lower().startswith('http://'):
        return ('aviso', 'FTP', detalle, '[ftp] url con http:// — usar https:// (contenido mixto)')
    return ('ok', 'FTP', detalle, '')


# ── requisitos del proyecto (sin conectarse a nada) ─────────────────────────
def requisitos(cfg: Dict) -> List[Punto]:
    """Lo que el proyecto necesita para generar y publicar, con su estado."""
    puntos: List[Punto] = []
    entorno = cfg.get('entorno', 'desarrollo')
    acceso = cfg.get('archivo_acceso') or '_configtotal.ini'

    if cfg['tipo'] == 'mockup':
        ruta = cfg.get('ruta_mockup', '')
        if ruta and os.path.isdir(ruta) and not os.path.isfile(os.path.join(ruta, 'index.html')):
            puntos.append(('falta', 'Mockup', f"la carpeta «{cfg['mockup']}» no tiene index.html",
                           'guardar ahí el diseño como index.html'))
        elif ruta and os.path.exists(ruta):
            puntos.append(('ok', 'Mockup', cfg['mockup'], ''))
        else:
            puntos.append(('falta', 'Mockup', 'no encontrado',
                           'copiar el .html a 01-Mockups/ y apuntar [entrada] mockup'))
    else:
        puntos.append(('ok', 'Entrada', 'las tablas se leen de la base de datos', ''))

    datos = cfg['bd']
    if datos.get('host') and datos.get('usuario') and datos.get('database'):
        puntos.append(('ok', 'Base de datos',
                       f"«{datos['database']}» en {datos['host']} (usuario {datos['usuario']})", ''))
    elif cfg['tipo'] == 'bd':
        puntos.append(('falta', 'Base de datos', 'sin configurar',
                       f'completar [bd] en {acceso}'))
    else:
        puntos.append(('aviso', 'Base de datos', 'sin configurar: se genera el código, '
                       'pero los .sql habrá que ejecutarlos a mano', f'completar [bd] en {acceso}'))

    if cfg.get('con_entornos') and entorno != 'produccion':
        puntos.append(('ok', 'FTP', 'no se usa en desarrollo (se publica con --entorno produccion)', ''))
    elif cfg.get('ftp_listo'):
        ftp = cfg['ftp']
        puntos.append(('ok', 'FTP', f"{_host_ftp(ftp['host'])} → {ftp.get('url') or '(falta url)'}", ''))
    else:
        puntos.append(('aviso', 'FTP', 'sin configurar: no se podrá publicar',
                       'completar [ftp] en ' + ('_acceso.produccion.ini' if cfg.get('con_entornos')
                                                else '_configtotal.ini')))

    if cfg.get('google_auth_activo'):
        if cfg.get('google_client_id'):
            puntos.append(('ok', 'Google', 'activo con Client ID propio', ''))
        else:
            puntos.append(('falta', 'Google', 'activo pero SIN Client ID: el botón no aparecerá',
                           'cargar google_client_id (ver CONFIGURAR-GOOGLE-AUTH.md) o apagarlo'))
    return puntos


# (ruta, qué expone, texto que confirma que de verdad se sirvió ese archivo y
#  no la respuesta de la aplicación)
_EXPOSICION = (
    ('.env', 'la contraseña de la base de datos y la clave de la aplicación', b'APP_KEY'),
    ('storage/logs/laravel.log', 'el log (códigos de verificación, errores, correos)', b'.INFO:'),
    ('storage/logs/laravel.log', 'el log (códigos de verificación, errores, correos)', b'.ERROR:'),
    ('composer.json', 'las versiones exactas de las dependencias', b'"require"'),
    ('vendor/composer/installed.json', 'el inventario de dependencias', b'"packages"'),
    ('.env.example', 'la estructura de la configuración', b'APP_KEY'),
)


def probar_exposicion(url_base: str, timeout: int = 15) -> List[Tuple[str, str]]:
    """Pide por web, como lo haría cualquiera, los archivos internos del
    backend publicado. Devuelve [(ruta, qué expone)] de los que SÍ se pueden
    bajar. Lista vacía = la carpeta publicada está protegida."""
    import urllib.error
    import urllib.request
    expuestos, vistos = [], set()
    for ruta, que, firma in _EXPOSICION:
        if ruta in vistos:
            continue
        try:
            pedido = urllib.request.Request(f"{url_base.rstrip('/')}/{ruta}",
                                            headers={'User-Agent': 'davgen-diagnostico'})
            with urllib.request.urlopen(pedido, timeout=timeout) as r:
                cuerpo = r.read(65536)
        except (urllib.error.URLError, OSError, ValueError):
            continue
        if firma in cuerpo:
            expuestos.append((ruta, que))
            vistos.add(ruta)
    return expuestos


def url_backend(ftp: Dict) -> str:
    """URL pública de la carpeta donde se despliega el backend."""
    url = (ftp.get('url') or '').rstrip('/')
    carpeta = (ftp.get('ruta_remota') or '/servicio').strip('/').split('/')[-1]
    return f'{url}/{carpeta}' if url and carpeta else url


INTERFAZ = ("La aplicación que se genera es WEB y adaptable: funciona en celular, "
            "tablet y PC. Trae tema claro y oscuro, y por defecto sigue el del "
            "sistema operativo.")
