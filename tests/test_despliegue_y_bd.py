"""Despliegue incremental (qué archivos viajan) y capa de base de datos,
probados sin FTP y sin servidor MySQL."""
import os

from davgen import cli
from davgen.nucleo import bd, gen_sql, resumen

GENERADO = "<?php\n/**\n * @generated davgen v5.0.0 | 2026-01-01 00:00\n */\nclass X {}\n"
PROPIO = "<?php\nclass Mio {}\n"


def _escribir(base, rel, texto):
    ruta = os.path.join(str(base), *rel.split('/'))
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(texto)
    return ruta


def _arbol(tmp_path):
    espejo, laravel = tmp_path / 'espejo', tmp_path / 'laravel'
    for base in (espejo, laravel):
        _escribir(base, 'app/Services/BaseService.php', GENERADO)
        _escribir(base, 'routes/api.php', GENERADO)
    # código propio, en los sitios donde los proyectos reales lo guardan
    for rel in ('app/Http/Controllers/Custom/PedidoController.php',
                'app/Dominio/Calculo.php', 'app/Providers/AppServiceProvider.php',
                'routes/Custom/tienda.php', 'routes/dominio_api.php',
                'bootstrap/providers.php'):
        _escribir(laravel, rel, PROPIO)
    # resto de una tabla eliminada: generado, ya no está en el espejo
    _escribir(laravel, 'app/Services/TblViejaService.php', GENERADO)
    # nada de esto debe viajar
    _escribir(laravel, 'vendor/autoload.php', PROPIO)
    _escribir(laravel, 'config/app.php', PROPIO)
    _escribir(laravel, '.env', 'DB_PASSWORD=secreto')
    return str(espejo), str(laravel)


def test_el_delta_lleva_todo_el_codigo_propio_este_donde_este(tmp_path):
    espejo, laravel = _arbol(tmp_path)
    hashes, origenes = resumen._hashes_control(espejo, laravel)
    assert set(hashes) == {
        'app/Services/BaseService.php', 'routes/api.php',
        'app/Http/Controllers/Custom/PedidoController.php',
        'app/Dominio/Calculo.php', 'app/Providers/AppServiceProvider.php',
        'routes/Custom/tienda.php', 'routes/dominio_api.php',
        'bootstrap/providers.php'}
    # lo generado sale del espejo; lo propio, del Laravel real y marcado
    assert origenes['routes/api.php'].startswith(espejo)
    assert origenes['routes/Custom/tienda.php'].startswith(laravel)
    assert hashes['routes/Custom/tienda.php'].startswith('propio:')
    assert not hashes['routes/api.php'].startswith('propio:')


def test_restos_generados_no_se_confunden_con_codigo_propio(tmp_path):
    espejo, laravel = _arbol(tmp_path)
    hashes, _ = resumen._hashes_control(espejo, laravel)
    assert 'app/Services/TblViejaService.php' not in hashes


def test_el_hash_ignora_la_linea_generated(tmp_path):
    a = _escribir(tmp_path, 'a.php', GENERADO)
    b = _escribir(tmp_path, 'b.php', GENERADO.replace('2026-01-01 00:00', '2027-05-05 10:10'))
    c = _escribir(tmp_path, 'c.php', GENERADO.replace('class X', 'class Y'))
    assert resumen._sha256_generado(a) == resumen._sha256_generado(b)
    assert resumen._sha256_generado(a) != resumen._sha256_generado(c)


def test_el_hash_del_frontend_cubre_todo_lo_que_entra_al_build(tmp_path):
    for rel in ('src/App.jsx', 'src/pages/generados/LibroPage.jsx',
                'src/components/Propio.jsx', 'src/index.css',
                'public/.htaccess', 'index.html', 'package.json',
                'vite.config.js'):
        _escribir(tmp_path, rel, 'x')
    for rel in ('node_modules/react/index.js', 'dist/index.html', '.env'):
        _escribir(tmp_path, rel, 'x')
    hashes = resumen._hashes_front_control(str(tmp_path))
    assert {'src/App.jsx', 'src/pages/generados/LibroPage.jsx',
            'src/components/Propio.jsx', 'src/index.css', 'public/.htaccess',
            'index.html', 'package.json', 'vite.config.js'} <= set(hashes)
    assert not any(r.startswith(('node_modules/', 'dist/')) or r == '.env'
                   for r in hashes)


def test_env_valor_protege_los_simbolos():
    assert cli.env_valor('simple123') == 'simple123'
    assert cli.env_valor('con espacio') == '"con espacio"'
    assert cli.env_valor('a#b') == '"a#b"'
    assert cli.env_valor('a"b$c') == '"a\\"b\\$c"'
    assert cli.env_valor('') == ''


def test_env_de_laravel_nuevo_usa_archivos_y_no_duplica_claves(tmp_path):
    (tmp_path / '.env.example').write_text(
        '﻿APP_KEY=\nDB_CONNECTION=sqlite\n# DB_HOST=127.0.0.1\n'
        'SESSION_DRIVER=database\nCACHE_STORE=database\nQUEUE_CONNECTION=database\n',
        encoding='utf-8')
    datos = {'host': 'srv', 'puerto': '3306', 'usuario': 'u',
             'password': 'p#1 x', 'database': 'bd'}
    cli._configurar_env_laravel(str(tmp_path), datos)
    env = (tmp_path / '.env').read_text(encoding='utf-8')
    lineas = env.splitlines()
    assert 'SESSION_DRIVER=file' in lineas and 'CACHE_STORE=file' in lineas
    assert 'QUEUE_CONNECTION=sync' in lineas
    assert 'DB_CONNECTION=mysql' in lineas and 'DB_HOST=srv' in lineas
    assert 'DB_PASSWORD="p#1 x"' in lineas
    assert any(linea.startswith('APP_KEY=base64:') for linea in lineas)
    for clave in ('DB_HOST', 'DB_CONNECTION', 'SESSION_DRIVER'):
        assert sum(1 for linea in lineas if linea.startswith(clave + '=')) == 1


def test_laravel_existente_sin_vendor_nunca_se_borra(tmp_path, monkeypatch):
    """Tras un `git clone` no hay vendor/. La v4 trataba esa carpeta como
    «restos» y la eliminaba entera, con el código propio adentro."""
    backend = tmp_path / '03-Backend' / 'backend'
    _escribir(backend, 'artisan', '#!/usr/bin/env php')
    _escribir(backend, 'composer.json', '{}')
    propio = _escribir(backend, 'app/Http/Controllers/Custom/Mio.php', PROPIO)
    monkeypatch.setattr(cli.shutil, 'which', lambda _nombre: None)   # sin composer
    resultado = cli._crear_proyecto_laravel(str(tmp_path / '03-Backend'), {})
    assert resultado is None                 # no pudo instalar…
    assert os.path.isfile(propio)            # …pero no borró nada


def test_carpeta_backend_con_archivos_ajenos_se_aparta_no_se_borra(tmp_path, monkeypatch):
    carpeta = tmp_path / '03-Backend'
    nota = _escribir(carpeta / 'backend', 'notas.txt', 'importante')
    monkeypatch.setattr(cli.shutil, 'which', lambda _nombre: None)
    assert cli._crear_proyecto_laravel(str(carpeta), {}) is None
    assert not os.path.exists(nota)
    apartadas = [d for d in os.listdir(carpeta) if d.startswith('backend._incompleto-')]
    assert len(apartadas) == 1
    assert (carpeta / apartadas[0] / 'notas.txt').read_text(encoding='utf-8') == 'importante'


# ── base de datos, con un doble de la conexión ──────────────────────────────
class _Cursor:
    def __init__(self, conexion):
        self.c = conexion
        self._filas = []

    def execute(self, sql, params=None):
        self.c.ejecutado.append(' '.join(sql.split()))
        self._filas = self.c.responder(sql)

    def fetchall(self):
        return self._filas

    def close(self):
        pass


class _Conexion:
    def __init__(self, responder):
        self.responder = responder
        self.ejecutado = []
        self.commits = 0
        self.cerrada = False

    def cursor(self, **_kw):
        return _Cursor(self)

    def commit(self):
        self.commits += 1

    def close(self):
        self.cerrada = True


BD = {'host': 'h', 'puerto': '3306', 'usuario': 'u', 'password': '', 'database': 'd'}


def test_texto_normaliza_bytes():
    assert bd.texto(b'abc') == 'abc'
    assert bd.texto(bytearray('ñ'.encode())) == 'ñ'
    assert bd.texto(None) == '' and bd.texto(5) == '5'


def test_aplicar_procedimientos_solo_recrea_los_nuevos_o_distintos(proyecto_generado):
    ruta = os.path.join(proyecto_generado, '03-Backend', '_backendGenerado',
                        'database', '03_procedimientos.sql')
    estado = {}                              # nombre → definición en la "BD"

    def responder(sql):
        if 'INFORMATION_SCHEMA.ROUTINES' in sql:
            return [(n, d.encode()) for n, d in estado.items()]   # bytes, como mysql-connector
        return []

    conexiones = []

    def fabrica(_bd, _timeout):
        conexiones.append(_Conexion(responder))
        return conexiones[-1]

    bd.usar_fabrica(fabrica)

    # 1) BD vacía, solo comparar: todo es nuevo y no se ejecuta nada
    rep = gen_sql.aplicar_procedimientos(BD, ruta, aplicar=False)
    assert len(rep['nuevos']) == 3 and not rep['iguales']
    assert not any(s.startswith(('DROP', 'CREATE')) for s in conexiones[-1].ejecutado)

    # 2) aplicar: DROP + CREATE por cada SP
    rep = gen_sql.aplicar_procedimientos(BD, ruta, aplicar=True)
    hechos = conexiones[-1].ejecutado
    assert sum(1 for s in hechos if s.startswith('DROP PROCEDURE')) == 3
    creados = [s for s in hechos if s.startswith('CREATE PROCEDURE')]
    assert len(creados) == 3 and conexiones[-1].cerrada

    # 3) la BD ya tiene esos SPs: una nueva corrida no toca nada (idempotente)
    for stmt in gen_sql._statements_sp(ruta):
        if stmt.upper().startswith('CREATE PROCEDURE'):
            estado[gen_sql._nombre_create(stmt)] = stmt[stmt.upper().find('BEGIN'):]
    rep = gen_sql.aplicar_procedimientos(BD, ruta, aplicar=True)
    assert len(rep['iguales']) == 3 and not rep['nuevos'] and not rep['actualizados']
    assert not any(s.startswith(('DROP', 'CREATE')) for s in conexiones[-1].ejecutado)


def test_sin_conexion_devuelve_error_y_no_revienta(proyecto_generado):
    def fabrica(_bd, _timeout):
        raise OSError('servidor apagado')
    bd.usar_fabrica(fabrica)
    ruta = os.path.join(proyecto_generado, '03-Backend', '_backendGenerado',
                        'database', '03_procedimientos.sql')
    assert 'servidor apagado' in gen_sql.aplicar_procedimientos(BD, ruta)['error']
