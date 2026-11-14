"""Límite de conexiones a MySQL del hosting compartido (errores 1226 y 1203).

Tres frentes: el backend generado reutiliza las conexiones, una corrida de
davgen abre una sola, y el frontend no repite pedidos de archivos ni de listas.
"""
import os
import shutil
import subprocess

import pytest
from conftest import leer

from davgen import cli
from davgen.nucleo import bd, configuracion, diagnostico, gen_sql, resumen

GEN = ('03-Backend', '_backendGenerado')
DATOS = {'host': 'bd.ejemplo.test', 'puerto': '3306', 'usuario': 'u', 'password': 'p',
         'database': 'base'}


def _bootstrap(proyecto) -> str:
    return leer(proyecto, *GEN, 'backend', 'bootstrap', 'app.php')


# ── backend generado: conexiones persistentes ──────────────────────────────
def test_el_backend_generado_reutiliza_las_conexiones_por_defecto(proyecto_generado):
    php = _bootstrap(proyecto_generado)
    assert r'\PDO::ATTR_PERSISTENT => true' in php
    assert "env('DB_PERSISTENT', true)" in php
    # las dos conexiones de Laravel para esta familia de bases
    assert "['mysql', 'mariadb']" in php
    # no pisa las demás opciones de la conexión (certificado SSL)
    assert '+ (array) config("{$clave}.options", [])' in php
    assert 'conexiones_persistentes = si' in leer(proyecto_generado, '_configtotal.ini')


def test_con_la_clave_en_no_el_backend_no_las_activa(proyecto_nuevo, davgen):
    configuracion.fijar_valor(proyecto_nuevo, 'opciones', 'conexiones_persistentes', 'no')
    codigo, salida = davgen(proyecto_nuevo, ['generar', '--local'])
    assert codigo == 0, salida
    php = _bootstrap(proyecto_nuevo)
    assert 'ATTR_PERSISTENT' not in php and 'DB_PERSISTENT' not in php
    assert '->withExceptions(' in php          # el resto del archivo sigue entero


def test_un_ini_anterior_sin_la_clave_las_activa(proyecto_nuevo, davgen):
    """Proyecto creado antes de existir la clave: regenerar ya trae el cambio."""
    ruta = os.path.join(proyecto_nuevo, '_configtotal.ini')
    with open(ruta, encoding='utf-8') as f:
        lineas = [x for x in f.read().splitlines()
                  if not x.startswith('conexiones_persistentes')]
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lineas) + '\n')
    codigo, salida = davgen(proyecto_nuevo, ['generar', '--local'])
    assert codigo == 0, salida
    assert 'ATTR_PERSISTENT' in _bootstrap(proyecto_nuevo)


def test_bootstrap_app_viaja_en_el_despliegue_incremental():
    """Es lo que lleva el cambio a un sitio ya publicado."""
    assert resumen._es_archivo_control('bootstrap/app.php')


@pytest.mark.parametrize('persistentes', [True, False])
def test_bootstrap_app_es_php_valido(proyecto_nuevo, davgen, persistentes):
    php = next((c for c in (os.environ.get('DAVGEN_PHP'), shutil.which('php'))
                if c and os.path.isfile(c)), None)
    if not php:
        pytest.skip('sin PHP para validar la sintaxis')
    configuracion.fijar_valor(proyecto_nuevo, 'opciones', 'conexiones_persistentes',
                              'si' if persistentes else 'no')
    assert davgen(proyecto_nuevo, ['generar', '--local'])[0] == 0
    ruta = os.path.join(proyecto_nuevo, *GEN, 'backend', 'bootstrap', 'app.php')
    r = subprocess.run([php, '-l', ruta], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_el_env_trae_el_interruptor_y_no_se_lo_vuelve_a_encender(tmp_path):
    (tmp_path / '.env.example').write_text('APP_KEY=\nDB_CONNECTION=sqlite\n', encoding='utf-8')
    cli._configurar_env_laravel(str(tmp_path), DATOS)
    assert 'DB_PERSISTENT=true' in leer(str(tmp_path), '.env').splitlines()

    # el usuario lo apaga (su hosting dio 1203): otra corrida lo respeta
    ruta = tmp_path / '.env'
    ruta.write_text(ruta.read_text(encoding='utf-8').replace(
        'DB_PERSISTENT=true', 'DB_PERSISTENT=false'), encoding='utf-8')
    cli._configurar_env_laravel(str(tmp_path), DATOS)
    lineas = leer(str(tmp_path), '.env').splitlines()
    assert 'DB_PERSISTENT=false' in lineas and 'DB_PERSISTENT=true' not in lineas

    resumen._preparar_env_produccion(str(tmp_path), DATOS, 'https://sitio.ejemplo.test', '/servicio')
    lineas = leer(str(tmp_path), '.env').splitlines()
    assert lineas.count('DB_PERSISTENT=false') == 1 and 'DB_PERSISTENT=true' not in lineas


# ── davgen: una sola conexión por corrida ──────────────────────────────────
class _Cursor:
    def execute(self, *_a):
        pass

    def fetchall(self):
        return []

    def close(self):
        pass


class _Conexion:
    def __init__(self):
        self.cerrada = False
        self.viva = True
        self.deshechos = 0

    def cursor(self, *_a, **_k):
        return _Cursor()

    def ping(self, reconnect=False):
        if not self.viva:
            raise OSError('conexión perdida')

    def commit(self):
        pass

    def rollback(self):
        self.deshechos += 1

    def close(self):
        self.cerrada = True


def _fabrica_contada():
    abiertas = []

    def fabrica(_datos, _timeout):
        abiertas.append(_Conexion())
        return abiertas[-1]
    bd.usar_fabrica(fabrica)
    return abiertas


def test_sin_compartir_cada_paso_abre_la_suya():
    abiertas = _fabrica_contada()
    bd.conectar(DATOS).close()
    bd.conectar(DATOS).close()
    assert len(abiertas) == 2 and all(c.cerrada for c in abiertas)


def test_una_corrida_abre_una_sola_conexion():
    abiertas = _fabrica_contada()
    antes = bd.conexiones_abiertas()
    with bd.una_sola_conexion():
        for _ in range(6):                      # validar, esquema, SPs, seeds…
            conn = bd.conectar(DATOS)
            conn.cursor().execute('SELECT 1')
            conn.close()                        # cada paso «cierra» la suya
        with bd.una_sola_conexion():            # anidar no abre otra
            bd.conectar(DATOS).close()
        assert len(abiertas) == 1 and not abiertas[0].cerrada
        assert abiertas[0].deshechos == 7       # lo no confirmado se descarta
    assert abiertas[0].cerrada                  # se cierra al terminar la corrida
    assert bd.conexiones_abiertas() - antes == 1
    bd.conectar(DATOS).close()                  # fuera del bloque, como siempre
    assert len(abiertas) == 2


def test_otra_base_usa_otra_conexion_y_una_caida_se_reemplaza():
    abiertas = _fabrica_contada()
    with bd.una_sola_conexion():
        bd.conectar(DATOS)
        bd.conectar(dict(DATOS, database='otra'))
        assert len(abiertas) == 2
        abiertas[0].viva = False                # el hosting cortó la inactiva
        bd.conectar(DATOS)
        assert len(abiertas) == 3
    assert abiertas[1].cerrada and abiertas[2].cerrada


def test_los_comandos_de_davgen_comparten_la_conexion(monkeypatch):
    abiertas = _fabrica_contada()

    def comando(_argv):
        for _ in range(4):
            bd.conectar(DATOS).close()
        return 0
    monkeypatch.setattr(cli, '_main', comando)
    assert cli.main([]) == 0
    assert len(abiertas) == 1 and abiertas[0].cerrada


def test_aplicar_procedimientos_y_seeds_no_reconectan(tmp_path):
    abiertas = _fabrica_contada()
    sps = tmp_path / '03_procedimientos.sql'
    sps.write_text('DELIMITER $$\n' + ''.join(
        f'DROP PROCEDURE IF EXISTS pcruTblX{i}$$\nCREATE PROCEDURE pcruTblX{i}() BEGIN SELECT 1; END$$\n'
        for i in range(5)) + 'DELIMITER ;\n', encoding='utf-8')
    with bd.una_sola_conexion():
        gen_sql.aplicar_procedimientos(DATOS, str(sps), aplicar=False)
        rep = gen_sql.aplicar_procedimientos(DATOS, str(sps), aplicar=True)
    assert 'error' not in rep
    assert len(abiertas) == 1


# ── mensajes: límite del hosting ───────────────────────────────────────────
class _ErrorMysql(Exception):
    pass


def test_el_limite_por_hora_se_explica_sin_traza_y_sin_reintentar(tmp_path):
    intentos = []

    def bloqueada(_datos, _timeout):
        intentos.append(1)
        raise _ErrorMysql(1226, "User 'u' has exceeded the 'max_connections_per_hour' resource")
    bd.usar_fabrica(bloqueada)
    sps = tmp_path / 'x.sql'
    sps.write_text('', encoding='utf-8')
    rep = gen_sql.aplicar_procedimientos(DATOS, str(sps))
    assert len(intentos) == 1                               # no insiste
    assert 'por una hora' in rep['error'] and '1226' in rep['error']
    assert 'Traceback' not in rep['error'] and 'exceeded' not in rep['error']

    causa, hacer = diagnostico.explicar_error_bd(_ErrorMysql(1226, 'x'), DATOS)
    assert 'por una hora' in causa and 'esperar' in hacer


def test_el_limite_de_simultaneas_dice_como_apagar_las_persistentes():
    causa, hacer = diagnostico.explicar_error_bd(_ErrorMysql(1203, 'x'), DATOS)
    assert '1203' in causa and 'simultáneas' in causa
    assert 'conexiones_persistentes = no' in hacer
    assert bd.explicar_limite(_ErrorMysql(1045, 'Access denied')) is None
    assert bd.mensaje_error(ValueError('otra cosa')) == 'otra cosa'


# ── frontend: no repetir pedidos ───────────────────────────────────────────
def test_el_frontend_guarda_los_archivos_descargados(proyecto_generado):
    js = leer(proyecto_generado, *GEN, 'frontend', 'src', 'services', 'api.js')
    assert 'export function descargar(' in js and 'export function olvidarArchivos(' in js
    assert 'MAX_ARCHIVOS' in js and 'MAX_BYTES' in js          # con tope
    assert 'URL.revokeObjectURL' in js                         # y libera lo que saca
    # cerrar sesión no deja los archivos de un usuario al siguiente
    limpiar = js[js.index('limpiar: () => {'):js.index('activa:')]
    assert 'olvidarArchivos()' in limpiar


def test_los_desplegables_comparten_la_lista(proyecto_generado):
    jsx = leer(proyecto_generado, *GEN, 'frontend', 'src', 'components', 'generados',
               'SelectRelacion.jsx')
    assert 'new WeakMap()' in jsx and 'VIGENCIA_MS' in jsx
    assert 'export function olvidarOpciones(' in jsx
    assert jsx.count("servicio.listar('', 1, 100)") == 1
