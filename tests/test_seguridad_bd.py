"""`davgen seguridad`: crear tbl_seg_* en la base, con un doble de la conexión."""
import os
import re

import pytest
from conftest import CLAVE_PRUEBA, leer

from davgen.nucleo import bd, configuracion, gen_sql


class _Cursor:
    def __init__(self, c):
        self.c, self._filas = c, []

    def execute(self, sql, params=None):
        plano = ' '.join(sql.split())
        self.c.ejecutado.append(plano)
        if self.c.fallar_en and self.c.fallar_en in plano:
            raise RuntimeError('error simulado')
        if 'INFORMATION_SCHEMA.TABLES' in plano:
            self._filas = [(t,) for t in sorted(self.c.tablas)]
            return
        m = re.match(r'CREATE TABLE IF NOT EXISTS `(\w+)`', plano)
        if m:
            self.c.tablas.add(m.group(1))
        self._filas = []

    def fetchall(self):
        return self._filas

    def close(self):
        pass


class _Base:
    """Una «base de datos» en memoria que sobrevive entre conexiones."""
    def __init__(self, tablas=(), fallar_en=''):
        self.tablas, self.fallar_en = set(tablas), fallar_en
        self.ejecutado, self.conexiones = [], 0

    def __call__(self, _datos, _timeout):
        self.conexiones += 1
        return self

    def cursor(self, **_kw):
        return _Cursor(self)

    def commit(self):
        pass

    def close(self):
        pass


def _con_bd(proyecto):
    for clave, valor in (('host', 'servidor.prueba'), ('usuario', 'u'),
                         ('database', 'bd_prueba')):
        configuracion.fijar_valor(proyecto, 'bd', clave, valor)


# ── partir el script ────────────────────────────────────────────────────────
def test_sentencias_respeta_delimiter_cadenas_y_comentarios():
    script = """\
-- comentario; con punto y coma
SET NAMES utf8mb4;
INSERT INTO t (a) VALUES ('uno; dos'), ('it''s; ok'), ("x;y"); # otro; comentario
/* bloque;
   de varias; líneas */
DELIMITER //
CREATE PROCEDURE p()
BEGIN
  SELECT 1; SELECT 'a//b';
END//
DELIMITER ;
CALL p();
"""
    s = gen_sql.sentencias_script(script)
    assert s[0] == 'SET NAMES utf8mb4'
    assert s[1] == "INSERT INTO t (a) VALUES ('uno; dos'), ('it''s; ok'), (\"x;y\")"
    assert s[2].startswith('CREATE PROCEDURE p()') and s[2].endswith('END')
    assert "SELECT 1; SELECT 'a//b';" in s[2]
    assert s[3] == 'CALL p()'
    assert len(s) == 4


def test_el_script_de_seguridad_real_se_parte_bien(proyecto_generado):
    ruta = os.path.join(proyecto_generado, '03-Backend', '_backendGenerado',
                        'database', '01_seguridad.sql')
    s = gen_sql.sentencias_script(leer(ruta))
    assert sum(1 for x in s if x.startswith('CREATE TABLE')) == 11
    assert sum(1 for x in s if x.startswith('CREATE OR REPLACE VIEW')) == 8
    procedimiento = [x for x in s if x.startswith('CREATE PROCEDURE')]
    assert len(procedimiento) == 1 and procedimiento[0].rstrip().endswith('END')
    assert not any(x.upper().startswith('DELIMITER') or x.startswith('--') for x in s)
    assert any(x.startswith('INSERT INTO `tbl_seg_usuario`') for x in s)


# ── crear en la base ────────────────────────────────────────────────────────
def test_crea_las_tablas_en_una_base_vacia(proyecto_generado):
    ruta = os.path.join(proyecto_generado, '03-Backend', '_backendGenerado',
                        'database', '01_seguridad.sql')
    base = _Base()
    bd.usar_fabrica(base)
    rep = gen_sql.crear_seguridad({'database': 'x'}, ruta)
    assert rep['error'] == '' and not rep['ya_existia']
    assert rep['ejecutadas'] == rep['total'] > 30
    assert 'tbl_seg_usuario' in rep['tablas'] and 'tbl_seg_parametro' in rep['tablas']
    assert 'personal_access_tokens' not in rep['tablas']      # solo informa tbl_seg_*


def test_no_toca_una_base_ya_sembrada(proyecto_generado):
    ruta = os.path.join(proyecto_generado, '03-Backend', '_backendGenerado',
                        'database', '01_seguridad.sql')
    base = _Base(tablas={'tbl_seg_usuario', 'tbl_seg_rol'})
    bd.usar_fabrica(base)
    rep = gen_sql.crear_seguridad({'database': 'x'}, ruta)
    assert rep['ya_existia'] and rep['ejecutadas'] == 0
    assert not any(s.startswith(('CREATE', 'INSERT', 'DROP', 'ALTER', 'SET'))
                   for s in base.ejecutado)


def test_se_detiene_en_el_primer_error(proyecto_generado):
    ruta = os.path.join(proyecto_generado, '03-Backend', '_backendGenerado',
                        'database', '01_seguridad.sql')
    base = _Base(fallar_en='`tbl_seg_rol`')
    bd.usar_fabrica(base)
    rep = gen_sql.crear_seguridad({'database': 'x'}, ruta)
    assert 'error simulado' in rep['error']
    assert 0 < rep['ejecutadas'] < rep['total']
    assert 'tbl_seg_modulo' not in rep['tablas']              # no siguió


# ── fijar un valor en el .ini ───────────────────────────────────────────────
def test_fijar_valor_reemplaza_o_agrega_sin_tocar_lo_demas(proyecto_nuevo):
    acceso = '_acceso.desarrollo.ini'
    antes = leer(proyecto_nuevo, acceso)
    configuracion.fijar_valor(proyecto_nuevo, 'bd', 'host', 'srv', archivo=acceso)
    configuracion.fijar_valor(proyecto_nuevo, 'bd', 'clave_nueva', 'v', archivo=acceso)
    despues = leer(proyecto_nuevo, acceso)
    assert 'host = srv' in despues and 'clave_nueva = v' in despues
    assert len(despues.splitlines()) == len(antes.splitlines()) + 1
    # la clave nueva quedó dentro de [bd], antes de [ftp]
    lineas = despues.splitlines()
    assert lineas.index('[bd]') < lineas.index('clave_nueva = v') < lineas.index('[ftp]')
    # una sección que no existe se agrega al final del archivo
    configuracion.fijar_valor(proyecto_nuevo, 'portal', 'titulo', 'x')
    assert leer(proyecto_nuevo, '_configtotal.ini').rstrip().endswith('[portal]\ntitulo = x')
    cfg, _ = configuracion.cargar(proyecto_nuevo)
    assert cfg['bd']['host'] == 'srv' and cfg['admin_password'] == CLAVE_PRUEBA


# ── el comando ──────────────────────────────────────────────────────────────
def test_comando_seguridad_crea_y_reescribe_el_script_con_el_ini(proyecto_nuevo, davgen):
    _con_bd(proyecto_nuevo)
    configuracion.fijar_valor(proyecto_nuevo, 'seguridad', 'owner_email',
                              'duenio@empresa.test')
    base = _Base()
    bd.usar_fabrica(base)
    codigo, salida = davgen(proyecto_nuevo, ['seguridad', '--si'])
    assert codigo == 0, salida
    assert 'bd_prueba' in salida and 'servidor.prueba' in salida
    assert 'tbl_seg_usuario' in base.tablas
    sql = leer(proyecto_nuevo, '02-Base-de-datos', '00-seguridad.sql')
    assert 'duenio@empresa.test' in sql               # el script refleja el .ini
    assert any('duenio@empresa.test' in s for s in base.ejecutado)

    # segunda vez: la base ya está sembrada → no ejecuta nada
    antes = len(base.ejecutado)
    codigo, salida = davgen(proyecto_nuevo, ['seguridad', '--si'])
    assert codigo == 0 and 'no se' in salida
    assert not any(s.startswith(('CREATE', 'INSERT')) for s in base.ejecutado[antes:])


def _sin_clave_admin(proyecto):
    ini = os.path.join(proyecto, '_acceso.desarrollo.ini')
    texto = leer(ini)
    with open(ini, 'w', encoding='utf-8') as f:
        f.write(re.sub(r'(?m)^admin_password = .*\n', 'admin_password =\n', texto))


def test_sin_contrasena_de_administrador_davgen_se_detiene_y_dice_donde_escribirla(
        proyecto_nuevo, davgen, monkeypatch):
    """davgen no inventa ni trae ninguna: la pone el usuario."""
    monkeypatch.delenv('DAVGEN_ADMIN_PASSWORD', raising=False)
    _con_bd(proyecto_nuevo)
    _sin_clave_admin(proyecto_nuevo)
    base = _Base()
    bd.usar_fabrica(base)
    for comando in (['seguridad', '--si'], ['generar', '--local'], ['generar', '--si']):
        codigo, salida = davgen(proyecto_nuevo, comando)
        assert codigo == 1, comando
        assert 'davgen no trae' in salida and '_acceso.desarrollo.ini' in salida
        assert 'admin_password' in salida
        assert 'composer' not in salida.lower()              # se detiene ANTES de crear Laravel
    assert base.ejecutado == []                              # no tocó la base
    assert os.listdir(os.path.join(proyecto_nuevo, '03-Backend')) == []
    assert not os.path.isdir(os.path.join(proyecto_nuevo, '03-Backend', '_backendGenerado',
                                          'database'))
    # analizar el mockup no siembra nada: no la necesita
    assert davgen(proyecto_nuevo, ['generar', '--listar'])[0] == 0
    assert configuracion.cargar(proyecto_nuevo)[0]['admin_password'] == ''


def test_la_contrasena_del_administrador_puede_venir_del_entorno_sin_guardarse(
        proyecto_nuevo, davgen, monkeypatch):
    bcrypt = pytest.importorskip('bcrypt')
    _con_bd(proyecto_nuevo)
    _sin_clave_admin(proyecto_nuevo)
    bd.usar_fabrica(_Base())
    monkeypatch.setenv('DAVGEN_ADMIN_PASSWORD', 'corta1')
    codigo, salida = davgen(proyecto_nuevo, ['seguridad', '--si'])
    assert codigo == 1 and 'no sirve' in salida
    monkeypatch.setenv('DAVGEN_ADMIN_PASSWORD', 'DelEntorno2026x')
    codigo, salida = davgen(proyecto_nuevo, ['seguridad', '--si'])
    assert codigo == 0, salida
    assert 'DelEntorno2026x' not in salida                   # nunca se muestra
    assert 'DelEntorno2026x' not in leer(proyecto_nuevo, '_acceso.desarrollo.ini')
    sql = leer(proyecto_nuevo, '02-Base-de-datos', '00-seguridad.sql')
    h = re.findall(r'\$2y\$12\$[./A-Za-z0-9]{53}', sql)[0].replace('$2y$', '$2b$').encode()
    assert bcrypt.checkpw(b'DelEntorno2026x', h)


def test_el_script_de_un_proyecto_recien_creado_avisa_que_falta_la_contrasena(
        tmp_path, davgen):
    bcrypt = pytest.importorskip('bcrypt')
    proyecto = str(tmp_path / 'p')
    assert davgen(str(tmp_path), ['nuevo', proyecto])[0] == 0
    sql = leer(proyecto, '02-Base-de-datos', '00-seguridad.sql')
    assert sql.startswith('-- ATENCION: este script todavia NO lleva tu contrasena')
    assert 'davgen seguridad' in sql.split('\n\n')[0]
    # el hash es válido pero de un valor al azar: nadie entra con él
    h = re.findall(r'\$2y\$12\$[./A-Za-z0-9]{53}', sql)[0].replace('$2y$', '$2b$').encode()
    assert not bcrypt.checkpw(b'', h)
    otro = str(tmp_path / 'q')
    davgen(str(tmp_path), ['nuevo', otro])
    assert h.decode() not in leer(otro, '02-Base-de-datos', '00-seguridad.sql').replace(
        '$2y$', '$2b$')


def test_la_salida_de_davgen_no_muestra_la_contrasena_del_administrador(proyecto_nuevo, davgen):
    _con_bd(proyecto_nuevo)
    bd.usar_fabrica(_Base())
    for comando in (['seguridad', '--si'], ['generar', '--local']):
        codigo, salida = davgen(proyecto_nuevo, comando)
        assert codigo == 0, salida
        assert CLAVE_PRUEBA not in salida, comando
    sql = leer(proyecto_nuevo, '02-Base-de-datos', '00-seguridad.sql')
    assert not sql.startswith('-- ATENCION')                 # ya lleva la del usuario


def test_comando_seguridad_sin_bd_configurada_no_conecta(proyecto_nuevo, davgen):
    base = _Base()
    bd.usar_fabrica(base)
    codigo, salida = davgen(proyecto_nuevo, ['seguridad', '--si'])
    assert codigo == 1 and '[bd]' in salida
    assert base.conexiones == 0
