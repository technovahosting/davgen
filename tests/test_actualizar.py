"""`davgen actualizar`: pasar un proyecto de davgen 4.x a 5 sin generar código."""
import os

from conftest import archivos, leer

from davgen.nucleo import configuracion

INI_V4 = """\
; =============================================================================
; _configtotal.ini — davgen v4.0
; Completar este archivo y ejecutar:  python davgen4.py generar
; =============================================================================

[proyecto]
; mi comentario propio
nombre = Legado
modulo = leg
autor = alguien

[entrada]
tipo = bd

[bd]
host = servidor.ejemplo
puerto = 3306
usuario = u_legado
password = S3cr;eta#1
database = legado

[generar]
aplicar_sps = si
; npm test + `davgen4 verificar` (rompe el build si editan lo generado)
ci = no

[seguridad]
; Protección de acceso al GENERADOR (no al sistema generado).
; La contraseña vigente es SIEMPRE el producto de dos números del reloj.
;   distinto de 0 → davgen NO pregunta
validar_acceso = 0

; ── Usuario administrador sembrado ──
admin_email = jefe@legado.test
owner_email = duenio@legado.test

[ftp]
host = ftp://ftp.ejemplo
usuario = ftpuser
password = Ftp%Clave
ruta_remota = /servicio
url = https://legado.test/
"""


def _proyecto_v4(tmp_path, crlf=False):
    raiz = tmp_path / 'legado'
    (raiz / '03-Backend').mkdir(parents=True)
    texto = INI_V4.replace('\n', '\r\n') if crlf else INI_V4
    (raiz / '_configtotal.ini').write_bytes(texto.encode('utf-8'))
    (raiz / '_davgen.leeme.md').write_text('guía vieja: davgen4, validar_acceso',
                                           encoding='utf-8')
    (raiz / '_davgen4-4.36.0.exe').write_bytes(b'MZ')
    (raiz / '.gitignore').write_text('*.zip\n', encoding='utf-8')
    return str(raiz)


def test_migrar_ini_quita_solo_lo_obsoleto(tmp_path):
    raiz = _proyecto_v4(tmp_path)
    antes, _ = configuracion.cargar(raiz)
    cambios = configuracion.migrar_ini(raiz)
    assert any('validar_acceso' in c for c in cambios)
    texto = leer(raiz, '_configtotal.ini')
    assert 'validar_acceso' not in texto and 'davgen4' not in texto
    assert 'Protección de acceso' not in texto        # su bloque de comentarios
    assert '; mi comentario propio' in texto           # los del usuario quedan
    assert '; ── Usuario administrador sembrado ──' in texto
    despues, errores = configuracion.cargar(raiz)
    assert errores == []
    for clave in ('nombre', 'modulo', 'autor', 'tipo', 'bd', 'ftp',
                  'admin_email', 'owner_email', 'generar'):
        assert antes[clave] == despues[clave], clave
    assert despues['bd']['password'] == 'S3cr;eta#1'
    assert despues['ftp']['password'] == 'Ftp%Clave'
    assert not any('validar_acceso' in a for a in despues['avisos'])
    assert configuracion.migrar_ini(raiz) == []        # idempotente


def test_migrar_ini_conserva_los_finales_de_linea(tmp_path):
    raiz = _proyecto_v4(tmp_path, crlf=True)
    configuracion.migrar_ini(raiz)
    with open(os.path.join(raiz, '_configtotal.ini'), 'rb') as f:
        crudo = f.read()
    assert b'\r\n' in crudo and b'\n' not in crudo.replace(b'\r\n', b'')


def test_avisa_de_los_valores_por_defecto_que_cambiaron(tmp_path):
    raiz = _proyecto_v4(tmp_path)
    avisos = ' | '.join(configuracion.claves_con_defecto_distinto(raiz))
    assert '[generar] produccion' in avisos and '[generar] front' in avisos
    assert 'google_auth_activo' in avisos
    assert 'owner_email' not in avisos and '[proyecto] autor' not in avisos


def test_actualizar_renueva_las_guias_y_no_genera_nada(tmp_path, davgen):
    raiz = _proyecto_v4(tmp_path)
    codigo, salida = davgen(raiz, ['actualizar', '--ini'])
    assert codigo == 0, salida
    guia = leer(raiz, '_davgen.leeme.md')
    assert 'davgen4' not in guia and 'validar_acceso' not in guia
    for archivo in ('leeme.html', 'CONFIGURAR-GOOGLE-AUTH.md',
                    '_configtotal.ejemplo.ini', '_prompts/leeme.md'):
        assert os.path.isfile(os.path.join(raiz, archivo)), archivo
    ejemplo = leer(raiz, '_configtotal.ejemplo.ini')
    assert 'S3cr;eta#1' not in ejemplo and 'Ftp%Clave' not in ejemplo
    # no genera código, no borra los restos de la v4 (solo informa)
    assert not os.path.exists(os.path.join(raiz, '03-Backend', '_backendGenerado'))
    assert os.path.isfile(os.path.join(raiz, '_davgen4-4.36.0.exe'))
    assert '_davgen4-4.36.0.exe ya no se usa' in salida
    assert 'NO está en .gitignore' in salida
    assert not any(a.endswith(('.php', '.jsx', '.sql')) for a in archivos(raiz))


def test_actualizar_sin_ini_no_toca_la_configuracion(tmp_path, davgen):
    raiz = _proyecto_v4(tmp_path)
    codigo, salida = davgen(raiz, ['actualizar'])
    assert codigo == 0, salida
    assert leer(raiz, '_configtotal.ini') == INI_V4
    assert 'actualizar --ini' in salida


def test_actualizar_fuera_de_un_proyecto_falla_sin_crear_nada(tmp_path, davgen):
    codigo, _ = davgen(tmp_path, ['actualizar'])
    assert codigo == 1
    assert os.listdir(tmp_path) == []
