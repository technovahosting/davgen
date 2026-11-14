"""Guardas de publicación: lo que NO puede entrar al repositorio ni al paquete."""
import os
import re

from conftest import RAIZ_REPO

from davgen.nucleo import configuracion
from davgen.nucleo.version import VERSION

IGNORAR_DIRS = {'.git', '.tmp', 'build', 'dist', '__pycache__', '.pytest_cache',
                '.ruff_cache', 'node_modules', '.venv', 'venv'}
TEXTO = ('.py', '.md', '.toml', '.yml', '.yaml', '.ini', '.php', '.js', '.jsx',
         '.sql', '.html', '.json', '.txt', '.ps1', '.sh', '.css', '.cfg')


def _archivos_del_repo():
    for base, dirs, nombres in os.walk(RAIZ_REPO):
        dirs[:] = [d for d in dirs if d not in IGNORAR_DIRS
                   and not d.endswith('.egg-info')]
        for n in nombres:
            if n.lower().endswith(TEXTO) or n in ('LICENSE', '.gitignore'):
                yield os.path.join(base, n)


def test_no_hay_datos_personales_ni_credenciales_en_el_repo():
    """Correos, teléfonos, hosts, usuarios de hosting, Client IDs de OAuth o
    contraseñas reales: nada de eso puede publicarse. (Este archivo y el de
    pruebas de punta a punta contienen los patrones para poder buscarlos.)"""
    patrones = re.compile(
        r'[\w.+-]+@(gmail|hotmail|outlook|yahoo)\.[a-z.]+'      # correos personales
        r'|\b\d{12}-[a-z0-9]{32}\.apps\.googleusercontent\.com'  # Client ID real
        r'|\b(?:\d{1,3}\.){3}\d{1,3}\b'                          # direcciones IP
        r'|\bu\d{9}[._][a-z]+', re.I)                            # usuarios de hosting
    # direcciones locales y correos de EJEMPLO de las guías
    permitidas = re.compile(
        r'^(127\.0\.0\.1|0\.0\.0\.0|\d+\.\d+\.\d+\.0'
        r'|(persona|cuenta|usuario|alguien|ejemplo|tu[._-]?correo)@.+)$', re.I)
    propios = {os.path.join(RAIZ_REPO, 'tests', n)
               for n in ('test_publicacion.py', 'test_e2e_local.py', 'test_cli.py')}
    hallazgos = []
    for ruta in _archivos_del_repo():
        if ruta in propios:
            continue
        with open(ruta, encoding='utf-8', errors='replace') as f:
            for n, linea in enumerate(f, 1):
                for m in patrones.finditer(linea):
                    if permitidas.match(m.group(0)):
                        continue
                    hallazgos.append(f'{os.path.relpath(ruta, RAIZ_REPO)}:{n}: {m.group(0)}')
    assert not hallazgos, '\n'.join(hallazgos)


def test_no_queda_la_contrasena_fija_de_la_v4_en_ningun_archivo():
    """La versión 4 sembraba el mismo administrador en todos los sistemas. Ni
    el código ni los documentos pueden nombrar esa contraseña."""
    historica = 'Admin' + '1234'                       # armada: este archivo se publica
    hallazgos = []
    for ruta in _archivos_del_repo():
        with open(ruta, encoding='utf-8', errors='replace') as f:
            if historica.lower() in f.read().lower():
                hallazgos.append(os.path.relpath(ruta, RAIZ_REPO))
    assert not hallazgos, hallazgos


def test_no_hay_binarios_ni_configuracion_real_en_el_repo():
    prohibidos = []
    for base, dirs, nombres in os.walk(RAIZ_REPO):
        dirs[:] = [d for d in dirs if d not in IGNORAR_DIRS]
        for n in nombres:
            if n.lower().endswith(('.exe', '.zip', '.sqlite')) or n in ('_configtotal.ini', '.env'):
                prohibidos.append(os.path.relpath(os.path.join(base, n), RAIZ_REPO))
    assert not prohibidos, prohibidos


def test_los_ps1_con_acentos_llevan_bom():
    """Windows PowerShell 5.1 lee un .ps1 sin BOM como ANSI: un «✓» o una «ó»
    rompen el análisis del script entero."""
    carpeta = os.path.join(RAIZ_REPO, 'scripts')
    for n in os.listdir(carpeta):
        if not n.endswith('.ps1'):
            continue
        with open(os.path.join(carpeta, n), 'rb') as f:
            crudo = f.read()
        if any(b > 127 for b in crudo):
            assert crudo.startswith(b'\xef\xbb\xbf'), n


def test_archivos_de_publicacion_presentes():
    for archivo in ('LICENSE', 'README.md', 'CHANGELOG.md', 'AVISOS-TERCEROS.md',
                    'SECURITY.md', 'CONTRIBUTING.md', 'DESCARGO.md', 'pyproject.toml'):
        assert os.path.isfile(os.path.join(RAIZ_REPO, archivo)), archivo
    with open(os.path.join(RAIZ_REPO, 'LICENSE'), encoding='utf-8') as f:
        assert 'MIT License' in f.read()


def test_la_version_esta_en_un_solo_lugar_y_en_el_changelog():
    assert re.fullmatch(r'\d+\.\d+\.\d+', VERSION)
    with open(os.path.join(RAIZ_REPO, 'pyproject.toml'), encoding='utf-8') as f:
        toml = f.read()
    assert 'davgen.nucleo.version.VERSION' in toml
    assert not re.search(r'^version\s*=\s*"', toml, re.M)     # no duplicada
    with open(os.path.join(RAIZ_REPO, 'CHANGELOG.md'), encoding='utf-8') as f:
        assert f'## [{VERSION}]' in f.read()


def test_la_plantilla_del_ini_no_trae_valores_de_nadie():
    def valores(texto):
        seccion, con_valor = '', {}
        for linea in texto.splitlines():
            limpia = linea.strip()
            if limpia.startswith('['):
                seccion = limpia.strip('[]')
            elif limpia and limpia[0] != ';' and '=' in limpia:
                clave, valor = (p.strip() for p in limpia.split('=', 1))
                con_valor[(seccion, clave)] = valor
        return con_valor

    con_valor = valores(configuracion.PLANTILLA)
    # la configuración del proyecto no tiene accesos…
    assert not any(s in ('bd', 'ftp') or 'password' in c for s, c in con_valor)
    for clave in (('proyecto', 'nombre'), ('proyecto', 'autor'),
                  ('seguridad', 'google_client_id'), ('seguridad', 'owner_email')):
        assert con_valor[clave] == '', clave
    # …y los archivos de acceso nacen vacíos (salvo la contraseña aleatoria)
    for entorno in configuracion.ENTORNOS:
        acceso = valores(configuracion.nueva_plantilla_acceso(entorno, 'ClaveX12345'))
        for clave in (('bd', 'host'), ('bd', 'usuario'), ('bd', 'password'),
                      ('bd', 'database'), ('ftp', 'host'), ('ftp', 'usuario'),
                      ('ftp', 'password'), ('ftp', 'url')):
            assert acceso[clave] == '', (entorno, clave)
        assert acceso[('seguridad', 'admin_password')] == 'ClaveX12345'
        vacio = valores(configuracion.nueva_plantilla_acceso(entorno))
        assert vacio[('seguridad', 'admin_password')] == ''     # la escribe el usuario
    assert con_valor[('seguridad', 'google_auth_activo')] == 'no'
    assert con_valor[('generar', 'produccion')] == 'no'
    assert con_valor[('generar', 'front')] == 'no'
