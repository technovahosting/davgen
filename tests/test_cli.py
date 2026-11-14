"""Comportamiento del comando: nada de efectos secundarios sorpresa."""
import os
import subprocess
import sys

from conftest import RAIZ_REPO

from davgen.nucleo.version import VERSION

ENTORNO = dict(os.environ, PYTHONPATH=os.path.join(RAIZ_REPO, 'src'),
               PYTHONIOENCODING='utf-8', DAVGEN_NO_ABRIR='1')


def _davgen(args, cwd):
    return subprocess.run([sys.executable, '-m', 'davgen', *args], cwd=str(cwd),
                          env=ENTORNO, capture_output=True, text=True,
                          encoding='utf-8', stdin=subprocess.DEVNULL, timeout=120)


def test_version(tmp_path):
    r = _davgen(['--version'], tmp_path)
    assert r.returncode == 0
    assert VERSION in r.stdout
    assert os.listdir(tmp_path) == []          # no escribe nada


def test_ayuda_lista_los_comandos(tmp_path):
    r = _davgen(['--help'], tmp_path)
    assert r.returncode == 0
    for comando in ('nuevo', 'generar', 'sincronizar', 'verificar', 'comparar',
                    'plantillas', 'doctor', 'actualizar', 'seguridad', 'entornos', 'proteger'):
        assert comando in r.stdout
    assert os.listdir(tmp_path) == []


def test_no_pide_contrasena_ni_bloquea_el_equipo(tmp_path, monkeypatch):
    """La v4 pedía una contraseña (día × hora) y, al fallar, creaba
    ~/.davgen_lock y dejaba el generador inutilizable en todo el equipo.
    Con stdin cerrado, cualquier comando debe terminar solo y sin ese archivo."""
    casa = tmp_path / 'casa'
    casa.mkdir()
    entorno = dict(ENTORNO, USERPROFILE=str(casa), HOME=str(casa))
    trabajo = tmp_path / 'trabajo'
    trabajo.mkdir()
    for args in (['generar'], ['generar', '--si'], ['verificar'], ['doctor']):
        r = subprocess.run([sys.executable, '-m', 'davgen', *args],
                           cwd=str(trabajo), env=entorno, capture_output=True,
                           text=True, encoding='utf-8',
                           stdin=subprocess.DEVNULL, timeout=120)
        assert 'ontraseña de acceso' not in r.stdout + r.stderr, args
    assert not (casa / '.davgen_lock').exists()


def test_sin_terminal_no_se_queda_esperando_el_token(tmp_path):
    """Con la entrada cerrada (tarea programada, CI, otro programa) un proyecto
    con accesos cifrados debe terminar con un mensaje, no quedarse esperando el
    token. En Windows el dispositivo nulo dice ser una terminal: se detectaba
    mal y el comando no terminaba nunca."""
    entorno = dict(ENTORNO, DAVGEN_TOKEN='token de la prueba 2026')
    assert subprocess.run([sys.executable, '-m', 'davgen', 'nuevo'], cwd=str(tmp_path),
                          env=entorno, capture_output=True, stdin=subprocess.DEVNULL,
                          timeout=120).returncode == 0
    r = subprocess.run([sys.executable, '-m', 'davgen', 'acceso', 'cifrar'], cwd=str(tmp_path),
                       env=entorno, capture_output=True, text=True, encoding='utf-8',
                       stdin=subprocess.DEVNULL, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    sin_token = {k: v for k, v in ENTORNO.items() if not k.startswith('DAVGEN_TOKEN')}
    for args in (['doctor'], ['generar', '--local'], ['acceso', 'ver'],
                 ['acceso', 'cambiar-token'], ['seguridad']):
        r = subprocess.run([sys.executable, '-m', 'davgen', *args], cwd=str(tmp_path),
                           env=sin_token, capture_output=True, text=True, encoding='utf-8',
                           stdin=subprocess.DEVNULL, timeout=60)      # colgarse = falla
        assert r.returncode == 1, (args, r.stdout[-300:])
        assert 'Traceback' not in r.stdout + r.stderr, args


def test_fuera_de_un_proyecto_no_crea_archivos_en_silencio(tmp_path):
    """`generar`/`verificar` en una carpeta cualquiera no deben sembrarla de
    archivos: para crear un proyecto está `davgen nuevo`."""
    for args in (['generar', '--si'], ['verificar'], ['comparar']):
        r = _davgen(args, tmp_path)
        assert r.returncode == 1, args
        assert os.listdir(tmp_path) == [], args
    assert 'davgen nuevo' in _davgen(['generar', '--si'], tmp_path).stdout


def test_nuevo_en_una_carpeta_y_rechaza_repetir(tmp_path):
    r = _davgen(['nuevo', 'mi-sistema'], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / 'mi-sistema' / '_configtotal.ini').is_file()
    assert (tmp_path / 'mi-sistema' / '03-Backend').is_dir()
    r = _davgen(['nuevo', 'mi-sistema'], tmp_path)
    assert r.returncode == 1


def test_config_incompleta_explica_que_falta(tmp_path):
    _davgen(['nuevo'], tmp_path)
    r = _davgen(['generar', '--local'], tmp_path)
    assert r.returncode == 1
    assert '[proyecto] nombre' in r.stdout
    assert '[proyecto] modulo' in r.stdout


def test_plantillas_listar_y_copiar(tmp_path):
    _davgen(['nuevo'], tmp_path)
    r = _davgen(['plantillas'], tmp_path)
    assert r.returncode == 0 and 'frontend/pagina.jsx' in r.stdout
    r = _davgen(['plantillas', 'copiar', 'frontend/pagina.jsx'], tmp_path)
    assert r.returncode == 0
    assert (tmp_path / '_plantillas' / 'frontend' / 'pagina.jsx').is_file()
    assert _davgen(['plantillas', 'copiar', 'no/existe.x'], tmp_path).returncode == 1


def test_doctor_no_modifica_nada(tmp_path):
    r = _davgen(['doctor'], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'Python' in r.stdout
    assert os.listdir(tmp_path) == []
