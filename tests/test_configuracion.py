"""_configtotal.ini: validación, valores neutros y manejo de secretos."""
import os
import re

import pytest
from conftest import CLAVE_PRUEBA

from davgen.nucleo import configuracion


def _escribir(carpeta, texto):
    ruta = os.path.join(str(carpeta), '_configtotal.ini')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(texto)
    return ruta


def _minimo(carpeta, extra=''):
    (carpeta / 'm.html').write_text('<html></html>', encoding='utf-8')
    return _escribir(carpeta, f"""
[proyecto]
nombre = Demo
modulo = dem
[entrada]
tipo = mockup
mockup = m.html
{extra}
""")


def test_plantilla_nueva_lista_los_campos_obligatorios(tmp_path):
    _escribir(tmp_path, configuracion.nueva_plantilla())
    _cfg, errores = configuracion.cargar(str(tmp_path))
    texto = ' | '.join(errores)
    assert '[proyecto] nombre' in texto
    assert '[proyecto] modulo' in texto


def test_config_minima_es_valida(tmp_path):
    _minimo(tmp_path)
    cfg, errores = configuracion.cargar(str(tmp_path))
    assert errores == []
    assert cfg['nombre'] == 'Demo' and cfg['modulo'] == 'dem'


def test_valores_por_defecto_son_neutros(tmp_path):
    """Publicable: el generador no trae cuentas ni identificadores de nadie y
    nada sale del proyecto sin que el usuario lo configure."""
    _minimo(tmp_path)
    cfg, _ = configuracion.cargar(str(tmp_path))
    assert cfg['owner_email'] == ''
    assert cfg['google_client_id'] == ''
    assert cfg['google_auth_activo'] is False
    assert cfg['autor'] == ''
    assert cfg['admin_email'] == 'admin@localhost'
    assert cfg['generar']['produccion'] is False
    assert cfg['generar']['front'] is False
    assert cfg['ftp_listo'] is False


def test_davgen_no_trae_ninguna_contrasena_de_administrador(tmp_path):
    """Ni fija ni inventada: nace vacía y la escribe quien crea el proyecto."""
    assert not hasattr(configuracion, 'ADMIN_PASSWORD_HISTORICA')
    assert '__ADMIN_PASSWORD__' not in configuracion.nueva_plantilla()
    for entorno in configuracion.ENTORNOS:
        acceso = configuracion.nueva_plantilla_acceso(entorno)
        assert re.search(r'(?m)^admin_password =\s*$', acceso), entorno
        assert 'ESCRIBE LA\n; TUYA' in acceso
    _minimo(tmp_path)                      # sin admin_password: no se asume ninguna
    cfg, errores = configuracion.cargar(str(tmp_path))
    assert errores == [] and cfg['admin_password'] == ''


@pytest.mark.parametrize('clave, problema', [
    ('corta1', 'mínimo 8'),
    ('sololetrasaqui', 'letras y números'),
    ('1234567890', 'letras y números'),
    ('aaaa1111', 'repite'),
    ('admin@localhost', 'letras y números'),
    ('admin2026', 'correo'),
    ('ADMIN987654', 'correo'),
    (CLAVE_PRUEBA, ''),
    ('Mi-Clave;con#simbolos9', ''),
])
def test_la_contrasena_del_administrador_tiene_un_minimo_de_fortaleza(tmp_path, clave, problema):
    resultado = configuracion.problema_admin_password(clave, 'admin@localhost')
    assert (problema in resultado) if problema else resultado == '', resultado
    _minimo(tmp_path, f'[seguridad]\nadmin_password = {clave}')
    _cfg, errores = configuracion.cargar(str(tmp_path))
    assert any('admin_password' in e for e in errores) is bool(problema)


def test_password_con_simbolos_se_lee_completa(tmp_path):
    """Un ; o un # en la contraseña NO es un comentario, y un % no rompe."""
    _minimo(tmp_path, '[bd]\nhost = localhost\nusuario = u\ndatabase = d\n'
                      'password = ab;cd#ef%gh|ij')
    cfg, errores = configuracion.cargar(str(tmp_path))
    assert errores == []
    assert cfg['bd']['password'] == 'ab;cd#ef%gh|ij'


def test_modulo_admite_de_dos_a_seis_letras(tmp_path):
    for modulo, valido in (('a', False), ('ab', True), ('gasip', True),
                           ('abcdef', True), ('abcdefg', False), ('ab1', False)):
        (tmp_path / 'm.html').write_text('<html></html>', encoding='utf-8')
        _escribir(tmp_path, f"[proyecto]\nnombre = X\nmodulo = {modulo}\n"
                            "[entrada]\ntipo = mockup\nmockup = m.html\n")
        _cfg, errores = configuracion.cargar(str(tmp_path))
        assert (not any('modulo' in e for e in errores)) is valido, modulo


def test_mockup_fuera_del_proyecto_se_rechaza(tmp_path):
    _escribir(tmp_path, "[proyecto]\nnombre = X\nmodulo = ab\n"
                        "[entrada]\ntipo = mockup\nmockup = ../otro/m.html\n")
    _cfg, errores = configuracion.cargar(str(tmp_path))
    assert any('RELATIVA' in e for e in errores)


def test_ftp_a_medias_es_error_y_http_es_aviso(tmp_path):
    _minimo(tmp_path, '[ftp]\nhost = ftp.ejemplo.com\nurl = http://ejemplo.com')
    cfg, errores = configuracion.cargar(str(tmp_path))
    assert any('[ftp]' in e for e in errores)
    assert any('https' in a for a in cfg['avisos'])


def test_clave_validar_acceso_de_la_v4_solo_avisa(tmp_path):
    _minimo(tmp_path, f'[seguridad]\nvalidar_acceso = 0\nadmin_password = {CLAVE_PRUEBA}')
    cfg, errores = configuracion.cargar(str(tmp_path))
    assert errores == []
    assert any('validar_acceso' in a for a in cfg['avisos'])


def test_ejemplo_no_lleva_secretos_y_conserva_lo_demas(tmp_path):
    _minimo(tmp_path, '[bd]\nhost = srv\nusuario = u\ndatabase = d\npassword = S3creta!\n'
                      '[seguridad]\nadmin_password = OtraSecreta99\n'
                      '[ftp]\nhost = f\nusuario = fu\npassword = FtpSecreta\nurl = https://x.com')
    ruta = configuracion.escribir_ejemplo(str(tmp_path))
    texto = open(ruta, encoding='utf-8').read()
    for secreto in ('S3creta!', 'OtraSecreta99', 'FtpSecreta'):
        assert secreto not in texto
    assert 'host = srv' in texto and 'nombre = Demo' in texto
    # segunda llamada sin cambios: no reescribe
    assert configuracion.escribir_ejemplo(str(tmp_path)) == ''


def test_ejemplo_vacia_tambien_los_secretos_que_agrega_el_proyecto():
    """Secciones propias del proyecto: lo que por nombre es un secreto no
    viaja al ejemplo versionado; el Client ID de Google (público) sí."""
    texto = configuracion.texto_ejemplo(
        "[portal]\ntoken_reporte = T0kenPrivado\nurl = https://x.test\n"
        "[pagos]\napi_key = LLAVE123\nclient_secret = SECRETO9\n"
        "[seguridad]\ngoogle_client_id = 123-abc.apps.example\n")
    for secreto in ('T0kenPrivado', 'LLAVE123', 'SECRETO9'):
        assert secreto not in texto
    assert 'token_reporte =' in texto and 'api_key =' in texto
    assert 'url = https://x.test' in texto
    assert 'google_client_id = 123-abc.apps.example' in texto
