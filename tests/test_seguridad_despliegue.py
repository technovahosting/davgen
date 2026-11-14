"""Seguridad de lo que se publica: la carpeta desplegada no puede servir por
web el .env, los logs ni los archivos de los usuarios, y el backend generado
lleva los endurecimientos que salieron de las pruebas de ataque."""
import ftplib
import os
import re
import zipfile

from conftest import leer

from davgen.nucleo import diagnostico, resumen

GEN = ('03-Backend', '_backendGenerado', 'backend')
LARAVEL_HTACCESS = ("<IfModule mod_rewrite.c>\n    RewriteEngine On\n"
                    "    RewriteCond %{REQUEST_FILENAME} !-f\n    RewriteRule ^ index.php [L]\n</IfModule>\n")


def _escribir(base, rel, texto='x'):
    ruta = os.path.join(str(base), *rel.split('/'))
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
        f.write(texto)


def _laravel_falso(tmp_path):
    base = tmp_path / 'laravel'
    for rel in ('artisan', 'composer.json', '.env', '.env.example', 'phpunit.xml', 'README.md',
                'app/Models/User.php', 'bootstrap/app.php', 'bootstrap/cache/config.php',
                'bootstrap/cache/.gitignore', 'config/app.php', 'database/database.sqlite',
                'database/migrations/x.php', 'routes/api.php', 'vendor/autoload.php',
                'tests/Feature/XTest.php', 'storage/logs/laravel.log', 'storage/logs/.gitignore',
                'storage/app/archivos/1/contrato.pdf', 'storage/app/.gitignore',
                'storage/framework/sessions/abc123', 'storage/framework/sessions/.gitignore',
                'storage/framework/views/x.php', 'storage/framework/cache/data/y',
                'public/robots.txt', 'public/favicon.ico'):
        _escribir(base, rel)
    _escribir(base, 'public/index.php', "<?php require __DIR__.'/../vendor/autoload.php';\n"
                                        "$app = require_once __DIR__.'/../bootstrap/app.php';\n")
    _escribir(base, 'public/.htaccess', LARAVEL_HTACCESS)
    return str(base)


def _reglas(texto):
    """Las RewriteRule de bloqueo del bloque de protección, como regex."""
    return [re.compile(m.group(1), re.I if 'NC' in m.group(2) else 0)
            for m in re.finditer(r'^\s*RewriteRule\s+(\S+)\s+-\s+\[(F[^\]]*)\]', texto, re.M)]


def _bloqueada(reglas, ruta):
    return any(r.search(ruta) for r in reglas)


# ── el bloque de protección ─────────────────────────────────────────────────
def test_las_reglas_cierran_lo_interno_y_dejan_lo_publico():
    reglas = _reglas(resumen.HTACCESS_PROTECCION)
    assert len(reglas) >= 4
    for ruta in ('.env', '.env.example', '.git/config', 'storage/logs/laravel.log',
                 'storage/app/archivos/1/contrato.pdf', 'vendor/autoload.php',
                 'vendor/composer/installed.json', 'app/Http/Controllers/AuthController.php',
                 'config/database.php', 'bootstrap/cache/config.php', 'database/database.sqlite',
                 'routes/api.php', 'composer.json', 'composer.lock', 'artisan', 'package.json',
                 'phpunit.xml', 'README-SEGURIDAD.md', 'respaldo.sql', 'copia.zip', 'Storage/logs/x.log'):
        assert _bloqueada(reglas, ruta), ruta
    for ruta in ('index.php', 'api/auth/login', 'api/bib/libro/listar', 'robots.txt', 'favicon.ico',
                 '.well-known/acme-challenge/token', 'up', 'api/appointments', 'api/storage-info'):
        assert not _bloqueada(reglas, ruta), ruta


def test_el_bloque_se_antepone_una_sola_vez_y_respeta_lo_demas():
    una = resumen.htaccess_protegido(LARAVEL_HTACCESS)
    assert una.startswith(resumen.MARCA_PROTECCION)
    assert una.endswith(LARAVEL_HTACCESS)                       # las reglas de Laravel, intactas
    assert resumen.htaccess_protegido(una) == una               # idempotente
    assert una.count(resumen.MARCA_PROTECCION) == 1
    propio = "# regla del usuario\nRewriteRule ^viejo$ /nuevo [R=301]\n" + LARAVEL_HTACCESS
    assert resumen.htaccess_protegido(propio).endswith(propio)
    assert resumen.htaccess_protegido('').startswith(resumen.MARCA_PROTECCION)


# ── el zip que se sube ──────────────────────────────────────────────────────
def test_el_zip_de_despliegue_va_protegido_y_sin_restos_de_la_pc(tmp_path):
    destino = str(tmp_path / 'servicio.zip')
    resumen._empaquetar_laravel(_laravel_falso(tmp_path), destino)
    with zipfile.ZipFile(destino) as z:
        nombres = set(z.namelist())
        raiz = z.read('.htaccess').decode('utf-8')
        indice = z.read('index.php').decode('utf-8')
        interno = z.read('storage/.htaccess').decode('utf-8')
    assert raiz.startswith(resumen.MARCA_PROTECCION) and 'RewriteRule ^ index.php [L]' in raiz
    assert "__DIR__.'/vendor/autoload.php'" in indice           # public/ aplanado
    for carpeta in ('app', 'bootstrap', 'config', 'database', 'routes', 'storage', 'vendor'):
        assert f'{carpeta}/.htaccess' in nombres, carpeta
    assert 'Require all denied' in interno
    # lo que la app necesita, viaja
    for rel in ('.env', 'artisan', 'composer.json', 'vendor/autoload.php', 'robots.txt', 'favicon.ico',
                'storage/framework/sessions/.gitignore', 'storage/logs/.gitignore',
                'bootstrap/cache/.gitignore', 'database/migrations/x.php'):
        assert rel in nombres, rel
    # lo que es de la PC de desarrollo, o no hace falta, NO
    for rel in ('.env.example', 'phpunit.xml', 'README.md', 'tests/Feature/XTest.php',
                'database/database.sqlite', 'storage/logs/laravel.log',
                'storage/app/archivos/1/contrato.pdf', 'storage/framework/sessions/abc123',
                'storage/framework/views/x.php', 'storage/framework/cache/data/y',
                'bootstrap/cache/config.php', 'public/index.php'):
        assert rel not in nombres, rel


# ── proteger un despliegue que ya existe ────────────────────────────────────
class _FtpFalso:
    servidor = {}

    def __init__(self):
        self.subidos = []

    def connect(self, *a, **k):
        pass

    def login(self, *a):
        pass

    def set_pasv(self, _v):
        pass

    def quit(self):
        pass

    def retrbinary(self, orden, escribir):
        ruta = orden.split(' ', 1)[1]
        if ruta not in self.servidor:
            raise ftplib.error_perm('550 No such file')
        escribir(self.servidor[ruta].encode('utf-8'))

    def storbinary(self, orden, flujo):
        ruta = orden.split(' ', 1)[1]
        self.servidor[ruta] = flujo.read().decode('utf-8')
        self.subidos.append(ruta)

    def cwd(self, ruta):
        if not any(r.startswith(ruta + '/') for r in self.servidor):
            raise ftplib.error_perm('550 No such directory')

    def mkd(self, _ruta):
        pass

    def delete(self, ruta):
        self.servidor.pop(ruta, None)


def test_proteger_un_despliegue_anterior(monkeypatch):
    _FtpFalso.servidor = {
        '/servicio/.htaccess': LARAVEL_HTACCESS,
        '/servicio/.env': 'DB_PASSWORD=secreto', '/servicio/index.php': '<?php',
        '/servicio/app/Models/User.php': '<?php', '/servicio/storage/logs/laravel.log': 'x',
        '/servicio/vendor/autoload.php': '<?php', '/servicio/config/app.php': '<?php',
    }
    monkeypatch.setattr(resumen.ftplib, 'FTP', _FtpFalso)
    datos = {'host': 'ftp.x.test', 'usuario': 'u', 'password': 'p', 'ruta_remota': '/servicio'}
    rep = resumen.proteger_remoto(datos)
    assert rep['error'] == '' and rep['raiz'] == 'agregada'
    assert rep['carpetas'] == ['app', 'config', 'storage', 'vendor']       # solo las que existen
    s = _FtpFalso.servidor
    assert s['/servicio/.htaccess'].startswith(resumen.MARCA_PROTECCION)
    assert s['/servicio/.htaccess'].endswith(LARAVEL_HTACCESS)
    assert 'Require all denied' in s['/servicio/storage/.htaccess']
    assert s['/servicio/.env'] == 'DB_PASSWORD=secreto'                    # nada más se toca
    assert '/servicio/tests/.htaccess' not in s
    # repetirlo no cambia la raíz
    assert resumen.proteger_remoto(datos)['raiz'] == 'ya estaba'


def test_el_despliegue_incremental_tambien_protege(monkeypatch, tmp_path):
    """Un sitio publicado con una versión anterior queda protegido en su
    siguiente despliegue, sin tener que acordarse de correr nada."""
    _FtpFalso.servidor = {'/servicio/.htaccess': LARAVEL_HTACCESS, '/servicio/app/x.php': '<?php'}
    monkeypatch.setattr(resumen.ftplib, 'FTP', _FtpFalso)
    espejo = tmp_path / 'backend'
    _escribir(espejo, 'app/Services/BaseService.php', '<?php // generado')
    salida = tmp_path / 'salida'
    salida.mkdir()
    exito, _detalle = resumen._subir_delta_control(
        {'host': 'h', 'usuario': 'u', 'password': 'p', 'ruta_remota': '/servicio'},
        str(espejo), str(salida))
    assert exito
    assert _FtpFalso.servidor['/servicio/.htaccess'].startswith(resumen.MARCA_PROTECCION)
    assert '/servicio/app/.htaccess' in _FtpFalso.servidor


def test_url_del_backend_publicado():
    assert diagnostico.url_backend({'url': 'https://x.test/', 'ruta_remota': '/servicio'}) == 'https://x.test/servicio'
    assert diagnostico.url_backend({'url': 'https://x.test', 'ruta_remota': '/a/api2/'}) == 'https://x.test/api2'
    assert diagnostico.url_backend({'url': '', 'ruta_remota': '/servicio'}) == ''


def test_detecta_una_carpeta_expuesta(monkeypatch):
    import io
    import urllib.request
    paginas = {'https://x.test/servicio/.env': b'APP_NAME=X\nAPP_KEY=base64:abc\nDB_PASSWORD=s\n',
               'https://x.test/servicio/composer.json': b'<html>pagina de la app</html>'}

    def abrir(pedido, timeout=0):
        url = pedido.full_url
        if url not in paginas:
            raise urllib.error.HTTPError(url, 403, 'Forbidden', {}, None)
        return io.BytesIO(paginas[url])
    monkeypatch.setattr(urllib.request, 'urlopen', abrir)
    expuestos = diagnostico.probar_exposicion('https://x.test/servicio')
    assert [r for r, _q in expuestos] == ['.env']          # el 200 que no es el archivo no cuenta
    paginas.clear()
    assert diagnostico.probar_exposicion('https://x.test/servicio') == []


# ── endurecimientos del backend generado ────────────────────────────────────
def test_el_backend_generado_lleva_los_endurecimientos(proyecto_generado):
    auth = leer(proyecto_generado, *GEN, 'app', 'Http', 'Controllers', 'AuthController.php')
    # mismo tiempo de respuesta exista o no el correo
    assert 'HASH_SENUELO' in auth and re.search(r"HASH_SENUELO = '\$2y\$12\$[./A-Za-z0-9]{53}'", auth)
    # el código 2FA solo va al log en desarrollo
    assert "if (config('app.debug'))" in auth
    # las sesiones vencen
    assert "Parametro::entero('sesion_minutos', 720)" in auth and 'addMinutes($minutos)' in auth
    sql = leer(proyecto_generado, '03-Backend', '_backendGenerado', 'database', '01_seguridad.sql')
    assert "('sesion_minutos',      '720'" in sql

    ctrl = leer(proyecto_generado, *GEN, 'app', 'Http', 'Controllers', 'bib', 'BibLibroController.php')
    # el id se valida antes de llegar a la base
    assert "$idRecibido = $request->input('pid');" in ctrl and "'Identificador inválido', 422" in ctrl
    # los errores de MySQL no llegan crudos al cliente
    assert 'errorInfo[2]' not in ctrl and ctrl.count('$this->errorBd($e)') >= 1
    base = leer(proyecto_generado, *GEN, 'app', 'Http', 'Controllers', 'BaseController.php')
    assert "$estado === '45000'" in base and "'Error de base de datos'" in base

    arranque = leer(proyecto_generado, *GEN, 'bootstrap', 'app.php')
    assert '$middleware->redirectGuestsTo(fn () => null);' in arranque


def test_el_alta_publica_no_deja_elegir_id_ni_estado(proyecto_nuevo, davgen):
    from davgen.nucleo import configuracion
    configuracion.fijar_valor(proyecto_nuevo, 'opciones', 'publico', 'tbl_bib_libro:sel,add')
    codigo, salida = davgen(proyecto_nuevo, ['generar', '--local'])
    assert codigo == 0, salida
    ctrl = leer(proyecto_nuevo, *GEN, 'app', 'Http', 'Controllers', 'bib', 'BibLibroController.php')
    publico = ctrl[ctrl.index('public function guardarPublico'):]
    assert "$params['pid'] = 0;" in publico and "$params['pactivo'] = 1;" in publico
    rutas = leer(proyecto_nuevo, *GEN, 'routes', 'bib_api.php')
    assert "throttle:publico" in rutas


def test_ningun_sql_se_arma_con_texto_del_usuario():
    """Regla del proyecto: nada de whereRaw / DB::raw / selectRaw con datos de
    la petición en las plantillas PHP."""
    from davgen.nucleo import plantillas
    sospechosos = []
    for ruta in plantillas.listar():
        if not ruta.endswith('.php'):
            continue
        texto = plantillas.cargar(ruta)
        for patron in (r'whereRaw\(', r'selectRaw\(', r'orderByRaw\(', r'havingRaw\(',
                       r'DB::raw\([^)]*\$request',
                       r'\beval\(', r'\bunserialize\(\s*\$request', r'\bextract\(\s*\$request'):
            if re.search(patron, texto):
                sospechosos.append(f'{ruta}: {patron}')
        # en un SQL escrito a mano solo se interpolan el nombre FIJO del
        # procedimiento y los marcadores «?»; los valores van siempre enlazados
        for sql in re.findall(r'DB::(?:select|statement|unprepared|insert|update|delete)\(\s*"([^"]*)"', texto):
            extra = set(re.findall(r'\{\$([^}]+)\}', sql)) - {'this->procedimiento', 'marcas'}
            if extra or re.search(r'(?<!\{)\$\w', sql):
                sospechosos.append(f'{ruta}: interpola {sorted(extra) or "una variable"} en «{sql[:50]}»')
    assert not sospechosos, sospechosos
