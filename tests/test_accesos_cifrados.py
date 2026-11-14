"""Accesos cifrados: token por proyecto, llave maestra y las dos salidas
cuando el token se pierde."""
import os

import pytest
from conftest import archivos, leer

from davgen.nucleo import bd, boveda, configuracion

TOKEN = 'token-del-proyecto-2026'
OTRO = 'otro-token-distinto-99'
SECRETOS = ('Pr0d;#Clave', 'FtpClave9', 'DevClave77')


@pytest.fixture
def proyecto(proyecto_nuevo, monkeypatch):
    """Proyecto con accesos cargados en los dos entornos, y sin variables de
    token heredadas del equipo."""
    for variable in (boveda.VARIABLE_TOKEN, boveda.VARIABLE_MAESTRA, 'DAVGEN_TOKEN_NUEVO'):
        monkeypatch.delenv(variable, raising=False)
    f = configuracion.fijar_valor
    for clave, valor in (('host', '127.0.0.1'), ('usuario', 'root'),
                         ('password', 'DevClave77'), ('database', 'dev_db')):
        f(proyecto_nuevo, 'bd', clave, valor, archivo='_acceso.desarrollo.ini')
    for clave, valor in (('host', 'bd.hosting.test'), ('usuario', 'u_prod'),
                         ('password', 'Pr0d;#Clave'), ('database', 'prod_db')):
        f(proyecto_nuevo, 'bd', clave, valor, archivo='_acceso.produccion.ini')
    for clave, valor in (('host', 'ftp.hosting.test'), ('usuario', 'ftpu'),
                         ('password', 'FtpClave9'), ('url', 'https://sitio.test')):
        f(proyecto_nuevo, 'ftp', clave, valor, archivo='_acceso.produccion.ini')
    return proyecto_nuevo


def _llave_mostrada(salida: str) -> str:
    lineas = [x.strip() for x in salida.splitlines()]
    return next(x.split('\x1b')[-2].split('m')[-1] if '\x1b' in x else x
                for x in lineas if x.replace('\x1b[1m', '').replace('\x1b[0m', '').count('-') == 7)


def _cifrar(proyecto, davgen, monkeypatch, *extra):
    monkeypatch.setenv(boveda.VARIABLE_TOKEN, TOKEN)
    codigo, salida = davgen(proyecto, ['acceso', 'cifrar', *extra])
    assert codigo == 0, salida
    return salida


# ── la bóveda ───────────────────────────────────────────────────────────────
def test_cifra_y_abre_con_token_o_con_llave_maestra():
    llave = boveda.nueva_llave_maestra()
    sellado = boveda.cifrar('[bd]\npassword = S3creta;#\n', 'produccion', TOKEN, llave)
    assert sellado.startswith('davgen-acceso v1\nentorno: produccion\n')
    assert 'S3creta' not in sellado and TOKEN not in sellado and llave not in sellado
    assert boveda.descifrar(sellado, TOKEN) == '[bd]\npassword = S3creta;#\n'
    # la llave se puede escribir en minúsculas, con o sin guiones
    assert boveda.descifrar(sellado, llave_maestra=llave.lower().replace('-', ' ')) \
        == '[bd]\npassword = S3creta;#\n'


def test_token_incorrecto_y_archivo_alterado_dan_el_mismo_error():
    sellado = boveda.cifrar('secreto', 'produccion', TOKEN)
    with pytest.raises(boveda.TokenIncorrecto):
        boveda.descifrar(sellado, OTRO)
    lineas = sellado.splitlines()
    datos = lineas[-1]
    alterado = '\n'.join(lineas[:-1] + [datos[:-6] + ('AAAAAA' if not datos.endswith('AAAAAA') else 'BBBBBB')])
    with pytest.raises(boveda.TokenIncorrecto):
        boveda.descifrar(alterado, TOKEN)
    # un archivo de desarrollo no pasa por el de producción
    with pytest.raises(boveda.TokenIncorrecto):
        boveda.descifrar(sellado.replace('entorno: produccion', 'entorno: desarrollo'), TOKEN)


def test_cada_cifrado_es_distinto_y_sin_llave_no_hay_recuperacion():
    a, b = boveda.cifrar('x', 'desarrollo', TOKEN), boveda.cifrar('x', 'desarrollo', TOKEN)
    assert a != b                                  # sal y nonce al azar
    assert not boveda.tiene_llave_maestra(a)
    with pytest.raises(boveda.ErrorBoveda, match='SIN llave maestra'):
        boveda.descifrar(a, llave_maestra='ABCD-EFGH')


def test_tokens_debiles_se_rechazan():
    assert boveda.validar_token('corto')
    assert boveda.validar_token('aaaaaaaaaaaaaaaa')
    assert boveda.validar_token(TOKEN) == ''
    with pytest.raises(boveda.ErrorBoveda):
        boveda.cifrar('x', 'desarrollo', '1234')


def test_cambiar_token_con_el_actual_o_con_la_llave_maestra():
    llave = boveda.nueva_llave_maestra()
    sellado = boveda.cifrar('contenido', 'produccion', TOKEN, llave)
    con_actual = boveda.cambiar_token(sellado, OTRO, token_actual=TOKEN)
    assert boveda.descifrar(con_actual, OTRO) == 'contenido'
    with pytest.raises(boveda.TokenIncorrecto):
        boveda.descifrar(con_actual, TOKEN)                    # el viejo ya no abre
    # token perdido: la llave maestra autoriza uno nuevo y sigue sirviendo después
    recuperado = boveda.cambiar_token(sellado, 'recuperado-con-llave-1', llave_maestra=llave)
    assert boveda.descifrar(recuperado, 'recuperado-con-llave-1') == 'contenido'
    assert boveda.descifrar(recuperado, llave_maestra=llave) == 'contenido'
    with pytest.raises(boveda.TokenIncorrecto):
        boveda.cambiar_token(sellado, 'nuevo-token-valido-1', token_actual='no-es-el-token-1')


def test_reescribir_conserva_la_llave_maestra():
    llave = boveda.nueva_llave_maestra()
    sellado = boveda.cifrar('uno', 'desarrollo', TOKEN, llave)
    nuevo = boveda.reescribir(sellado, 'dos', TOKEN)
    assert boveda.descifrar(nuevo, TOKEN) == 'dos'
    assert boveda.descifrar(nuevo, llave_maestra=llave) == 'dos'


# ── el proyecto cifrado ─────────────────────────────────────────────────────
def test_cifrar_guarda_los_dos_entornos_y_borra_los_ini(proyecto, davgen, monkeypatch):
    salida = _cifrar(proyecto, davgen, monkeypatch)
    for entorno in ('desarrollo', 'produccion'):
        assert os.path.isfile(os.path.join(proyecto, f'_acceso.{entorno}.cifrado'))
        assert not os.path.exists(os.path.join(proyecto, f'_acceso.{entorno}.ini'))
        assert os.path.isfile(os.path.join(proyecto, f'_acceso.{entorno}.ejemplo.ini'))
    # ningún secreto queda legible en NINGÚN archivo del proyecto
    for rel in archivos(proyecto):
        with open(os.path.join(proyecto, rel), encoding='utf-8', errors='replace') as f:
            texto = f.read()
        for secreto in SECRETOS + (TOKEN,):
            assert secreto not in texto, (rel, secreto)
    assert 'LLAVE MAESTRA' in salida and 'SOLO ESTA VEZ' in salida
    codigo, estado = davgen(proyecto, ['acceso'])
    assert codigo == 0 and estado.count(': CIFRADO') == 2 and 'con llave maestra' in estado


def test_con_el_token_todo_funciona_igual(proyecto, davgen, monkeypatch):
    antes_dev, _ = configuracion.cargar(proyecto)
    antes_prod, _ = configuracion.cargar(proyecto, entorno='produccion')
    _cifrar(proyecto, davgen, monkeypatch)
    dev, e1 = configuracion.cargar(proyecto)
    prod, e2 = configuracion.cargar(proyecto, entorno='produccion')
    assert e1 == [] and e2 == []
    for clave in ('bd', 'ftp', 'admin_password', 'ftp_listo'):
        assert dev[clave] == antes_dev[clave] and prod[clave] == antes_prod[clave], clave
    assert dev['acceso_cifrado'] and dev['archivo_acceso'] == '_acceso.desarrollo.cifrado'
    assert prod['bd']['password'] == 'Pr0d;#Clave'
    codigo, salida = davgen(proyecto, ['generar', '--local'])
    assert codigo == 0, salida
    assert 'accesos en _acceso.desarrollo.cifrado' in salida


def test_sin_token_no_se_abre_y_no_revienta(proyecto, davgen, monkeypatch):
    _cifrar(proyecto, davgen, monkeypatch)
    monkeypatch.delenv(boveda.VARIABLE_TOKEN)
    boveda.olvidar()
    codigo, salida = davgen(proyecto, ['generar', '--local'])
    assert codigo == 1 and 'falta el token' in salida and boveda.VARIABLE_TOKEN in salida
    monkeypatch.setenv(boveda.VARIABLE_TOKEN, OTRO)
    codigo, salida = davgen(proyecto, ['generar', '--local'])
    assert codigo == 1 and 'incorrecto' in salida
    assert 'cambiar-token --con-llave-maestra' in salida and 'acceso reiniciar' in salida
    assert 'Traceback' not in salida
    for secreto in SECRETOS:
        assert secreto not in salida


def test_ver_muestra_los_accesos_solo_con_el_token(proyecto, davgen, monkeypatch):
    _cifrar(proyecto, davgen, monkeypatch)
    codigo, salida = davgen(proyecto, ['acceso', 'ver', '--entorno', 'produccion'])
    assert codigo == 0 and 'password = Pr0d;#Clave' in salida and 'DevClave77' not in salida
    monkeypatch.setenv(boveda.VARIABLE_TOKEN, OTRO)
    codigo, salida = davgen(proyecto, ['acceso', 'ver'])
    assert codigo == 1 and 'Pr0d' not in salida


def test_guardar_un_secreto_en_un_archivo_cifrado(proyecto, davgen, monkeypatch):
    """`davgen seguridad` genera la contraseña del admin: debe poder guardarla
    aunque los accesos estén cifrados, y sin perder la llave maestra."""
    salida = _cifrar(proyecto, davgen, monkeypatch)
    llave = _llave_mostrada(salida)
    archivo = configuracion.guardar_secreto(proyecto, 'portal', 'token_reporte', 'ValorNuevo123')
    assert archivo == '_acceso.desarrollo.cifrado'
    boveda.olvidar()
    assert configuracion.leer_ini(proyecto).get('portal', 'token_reporte') == 'ValorNuevo123'
    assert 'ValorNuevo123' not in leer(proyecto, archivo)
    assert boveda.descifrar(leer(proyecto, archivo), llave_maestra=llave).count('ValorNuevo123') == 1


def test_seguridad_funciona_con_los_accesos_cifrados(proyecto, davgen, monkeypatch):
    _cifrar(proyecto, davgen, monkeypatch)

    class _Cur:
        def __init__(self, base):
            self.base, self.filas = base, []

        def execute(self, sql, params=None):
            self.base.append(' '.join(sql.split()))
            self.filas = []

        def fetchall(self):
            return self.filas

        def close(self):
            pass

    class _Con:
        def __init__(self, base):
            self.base = base

        def cursor(self, **_k):
            return _Cur(self.base)

        def commit(self):
            pass

        def close(self):
            pass

    usados, ejecutado = [], []

    def fabrica(datos, _timeout):
        usados.append((datos['database'], datos['password']))
        return _Con(ejecutado)
    bd.usar_fabrica(fabrica)
    codigo, salida = davgen(proyecto, ['seguridad', '--si'])
    assert codigo == 0, salida
    assert usados[-1] == ('dev_db', 'DevClave77')          # leyó los accesos cifrados
    assert any(s.startswith('CREATE TABLE IF NOT EXISTS `tbl_seg_usuario`') for s in ejecutado)


# ── se perdió el token ──────────────────────────────────────────────────────
def test_camino_1_la_llave_maestra_pone_un_token_nuevo(proyecto, davgen, monkeypatch):
    llave = _llave_mostrada(_cifrar(proyecto, davgen, monkeypatch))
    monkeypatch.delenv(boveda.VARIABLE_TOKEN)              # token perdido
    monkeypatch.setenv(boveda.VARIABLE_MAESTRA, llave)
    monkeypatch.setenv('DAVGEN_TOKEN_NUEVO', OTRO)
    codigo, salida = davgen(proyecto, ['acceso', 'cambiar-token', '--con-llave-maestra'])
    assert codigo == 0, salida
    assert salida.count('token cambiado') == 2             # los dos entornos, mismo token
    monkeypatch.setenv(boveda.VARIABLE_TOKEN, OTRO)
    prod, errores = configuracion.cargar(proyecto, entorno='produccion')
    assert errores == [] and prod['bd']['password'] == 'Pr0d;#Clave'   # no se perdió nada
    monkeypatch.setenv(boveda.VARIABLE_TOKEN, TOKEN)       # el token viejo ya no abre
    boveda.olvidar()
    with pytest.raises(boveda.TokenIncorrecto):
        configuracion.cargar(proyecto)


def test_llave_maestra_incorrecta_no_cambia_nada(proyecto, davgen, monkeypatch):
    _cifrar(proyecto, davgen, monkeypatch)
    antes = leer(proyecto, '_acceso.produccion.cifrado')
    monkeypatch.setenv(boveda.VARIABLE_MAESTRA, boveda.nueva_llave_maestra())
    monkeypatch.setenv('DAVGEN_TOKEN_NUEVO', OTRO)
    codigo, _ = davgen(proyecto, ['acceso', 'cambiar-token', '--con-llave-maestra'])
    assert codigo == 1
    assert leer(proyecto, '_acceso.produccion.cifrado') == antes


def test_camino_2_reiniciar_y_volver_a_cargar_los_accesos(proyecto, davgen, monkeypatch):
    _cifrar(proyecto, davgen, monkeypatch, '--sin-llave-maestra')
    monkeypatch.delenv(boveda.VARIABLE_TOKEN)              # token perdido, sin llave
    boveda.olvidar()
    codigo, salida = davgen(proyecto, ['acceso', 'reiniciar', '--entorno', 'produccion', '--si'])
    assert codigo == 0, salida
    # producción vuelve a un .ini vacío para completar; el cifrado viejo no se destruye
    assert os.path.isfile(os.path.join(proyecto, '_acceso.produccion.ini'))
    assert not os.path.exists(os.path.join(proyecto, '_acceso.produccion.cifrado'))
    assert any(a.startswith('_acceso.produccion.cifrado.perdido-') for a in os.listdir(proyecto))
    prod, errores = configuracion.cargar(proyecto, entorno='produccion')
    assert errores == [] and prod['bd']['password'] == '' and prod['ftp_listo'] is False
    # desarrollo no se tocó: sigue cifrado
    assert os.path.isfile(os.path.join(proyecto, '_acceso.desarrollo.cifrado'))
    # se vuelven a cargar los accesos y se cifran con un token nuevo
    configuracion.fijar_valor(proyecto, 'bd', 'password', 'NuevaDelPanel1',
                              archivo='_acceso.produccion.ini')
    monkeypatch.setenv(boveda.VARIABLE_TOKEN, OTRO)
    codigo, salida = davgen(proyecto, ['acceso', 'cifrar', '--entorno', 'produccion'])
    assert codigo == 1                     # un token por proyecto: desarrollo usa otro
    assert os.path.isfile(os.path.join(proyecto, '_acceso.produccion.ini'))   # no borró nada


def test_descifrar_devuelve_el_ini_para_editar(proyecto, davgen, monkeypatch):
    original = leer(proyecto, '_acceso.produccion.ini')
    _cifrar(proyecto, davgen, monkeypatch)
    codigo, salida = davgen(proyecto, ['acceso', 'descifrar', '--entorno', 'produccion'])
    assert codigo == 0, salida
    assert leer(proyecto, '_acceso.produccion.ini') == original
    assert not os.path.exists(os.path.join(proyecto, '_acceso.produccion.cifrado'))
    assert os.path.isfile(os.path.join(proyecto, '_acceso.desarrollo.cifrado'))


def test_cifrar_sin_token_no_hace_nada(proyecto, davgen):
    codigo, salida = davgen(proyecto, ['acceso', 'cifrar'])
    assert codigo == 1 and 'Falta el token' in salida
    assert os.path.isfile(os.path.join(proyecto, '_acceso.produccion.ini'))
