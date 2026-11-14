"""La skill «crear-sistema» y el plugin de Claude Code que la distribuye:
que se pueda instalar, que no prometa comandos que no existen y que el .zip
descargable funcione solo."""
import argparse
import json
import os
import re
import zipfile

import pytest
from conftest import RAIZ_REPO, leer

from davgen import cli
from davgen.nucleo import configuracion, entrada
from davgen.nucleo.version import VERSION

NOMBRE = 'crear-sistema'
SKILL = os.path.join(RAIZ_REPO, 'skills', NOMBRE)
# claves del estándar de skills: con otras, la aplicación de Claude rechaza el .zip
CLAVES_ESTANDAR = {'name', 'description', 'license', 'compatibility', 'metadata',
                   'allowed-tools'}


def _markdowns():
    for base, _dirs, nombres in os.walk(SKILL):
        for n in nombres:
            if n.endswith('.md'):
                yield os.path.join(base, n)


def _frontmatter():
    crudo = open(os.path.join(SKILL, 'SKILL.md'), 'rb').read()
    assert crudo.startswith(b'---\n'), 'SKILL.md debe empezar con --- (sin BOM y con LF)'
    cabecera, cuerpo = crudo.decode('utf-8')[4:].split('\n---\n', 1)
    campos = dict(linea.split(': ', 1) for linea in cabecera.splitlines())
    return campos, cuerpo


# ── formato ────────────────────────────────────────────────────────────────
def test_la_cabecera_cumple_el_estandar_de_skills():
    campos, cuerpo = _frontmatter()
    assert set(campos) <= CLAVES_ESTANDAR, set(campos) - CLAVES_ESTANDAR
    assert campos['name'] == NOMBRE == os.path.basename(SKILL)
    assert re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', campos['name']) and len(NOMBRE) <= 64
    assert 100 < len(campos['description']) <= 1024
    assert '<' not in campos['description'] and '>' not in campos['description']
    assert len(cuerpo.splitlines()) < 500                    # lo demás va en referencias/


def test_los_archivos_de_la_skill_no_tienen_bom_ni_texto_roto():
    for ruta in _markdowns():
        crudo = open(ruta, 'rb').read()
        assert not crudo.startswith(b'\xef\xbb\xbf'), ruta
        assert b'\r\n' not in crudo, ruta
        assert 'Ã' not in crudo.decode('utf-8'), ruta        # UTF-8 leído como ANSI


def test_los_enlaces_entre_archivos_de_la_skill_existen():
    vistos = 0
    for ruta in _markdowns():
        for destino in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', leer(ruta)):
            if '://' in destino:
                continue
            vistos += 1
            assert os.path.isfile(os.path.join(SKILL, destino)), f'{ruta}: {destino}'
    assert vistos >= 4


# ── que lo que dice sea verdad ─────────────────────────────────────────────
def _comandos_que_ensena():
    """Cada `davgen …` escrito como código en la skill (bloques y comillas)."""
    comandos = set()
    for ruta in _markdowns():
        texto = leer(ruta)
        dentro, bloques = False, []
        for linea in texto.splitlines():
            if linea.lstrip().startswith('```'):
                dentro = not dentro
            elif dentro:
                bloques.append(linea)
        for crudo in (re.findall(r'^\s*davgen ([^#\n]+)', '\n'.join(bloques), re.M)
                      + re.findall(r'(?<!`)`davgen ([^`\n]+)`', texto)):
            if '<' not in crudo and '--help' not in crudo and '--version' not in crudo:
                comandos.add(tuple(crudo.split()))
    return sorted(comandos)


def test_la_skill_ensena_los_comandos_del_recorrido():
    comandos = _comandos_que_ensena()
    for esperado in (('nuevo', 'mi-sistema'), ('generar', '--listar'), ('generar', '--local'),
                     ('seguridad', '--si'), ('generar', '--si'), ('doctor', '--conexiones'),
                     ('generar', '--entorno', 'produccion')):
        assert esperado in comandos, esperado


@pytest.mark.parametrize('comando', _comandos_que_ensena(), ids=' '.join)
def test_davgen_acepta_cada_comando_que_ensena_la_skill(comando, monkeypatch):
    """Solo el análisis de argumentos: un comando u opción inventados fallan
    aquí (argparse sale con SystemExit) antes de llegar a un estudiante."""
    original = argparse.ArgumentParser.parse_args
    visto = []

    def espia(self, args=None, namespace=None):
        visto.append(original(self, args, namespace))
        raise KeyboardInterrupt                              # no ejecutar el comando

    monkeypatch.setattr(argparse.ArgumentParser, 'parse_args', espia)
    with pytest.raises(KeyboardInterrupt):
        cli._main(list(comando))
    assert visto


def test_las_claves_del_ini_que_ensena_la_skill_existen():
    texto = '\n'.join(leer(r) for r in _markdowns())
    plantilla = configuracion.PLANTILLA
    for clave in ('nombre', 'modulo', 'tipo', 'mockup', 'excluir', 'solo_consulta', 'publico',
                  'componentes_react', 'form_requests', 'tests', 'export', 'openapi',
                  'produccion', 'front', 'admin_email'):
        assert re.search(rf'^{clave} =', plantilla, re.M), clave
        assert clave in texto, clave
    acceso = configuracion.nueva_plantilla_acceso('desarrollo', 'ClaveX12345')
    for clave in ('host', 'puerto', 'usuario', 'password', 'database', 'admin_password'):
        assert re.search(rf'^{clave} =', acceso, re.M), clave


def test_el_mockup_de_la_skill_es_el_ejemplo_del_repo_y_da_tres_tablas():
    de_la_skill = os.path.join(SKILL, 'ejemplos', 'biblioteca.html')
    del_repo = os.path.join(RAIZ_REPO, 'ejemplos', 'biblioteca', 'index.html')
    assert open(de_la_skill, 'rb').read() == open(del_repo, 'rb').read()
    assert {e['nombre'] for e in entrada.analizar_mockup(de_la_skill)} == \
        {'libro', 'socio', 'prestamo'}


def test_el_fragmento_de_la_guia_del_mockup_lo_entiende_davgen(tmp_path):
    guia = leer(SKILL, 'referencias', 'mockup.md')
    fragmento = re.search(r'```html\n(.*?)```', guia, re.S).group(1)
    ruta = tmp_path / 'index.html'
    ruta.write_text(fragmento, encoding='utf-8')
    (producto,) = entrada.analizar_mockup(str(ruta))
    assert producto['nombre'] == 'producto'
    assert [c['nombre'] for c in producto['campos']] == \
        ['nombre', 'precio', 'categoria_id', 'estado', 'descripcion']
    estado = producto['campos'][3]
    assert estado['opciones'] == ['disponible', 'agotado']   # «Seleccione…» se descarta


def test_los_nombres_reservados_de_la_guia_son_los_del_analizador():
    guia = leer(SKILL, 'referencias', 'mockup.md')
    for nombre in sorted(entrada._NOMBRES_IGNORAR - {''}):
        assert f'`{nombre}`' in guia, nombre


def test_el_recorrido_de_la_skill_funciona_de_punta_a_punta(tmp_path, davgen):
    """nuevo → mockup de ejemplo → dos claves del .ini → generar --local."""
    proyecto = str(tmp_path / 'mi-sistema')
    assert davgen(str(tmp_path), ['nuevo', proyecto])[0] == 0
    destino = os.path.join(proyecto, '01-Mockups', 'index.html')
    with open(os.path.join(SKILL, 'ejemplos', 'biblioteca.html'), 'rb') as f:
        open(destino, 'wb').write(f.read())
    for seccion, clave, valor in (('proyecto', 'nombre', 'Biblioteca del barrio'),
                                  ('proyecto', 'modulo', 'bib'),
                                  ('entrada', 'tipo', 'mockup'),
                                  ('entrada', 'mockup', '01-Mockups/index.html')):
        configuracion.fijar_valor(proyecto, seccion, clave, valor)
    # sin la contraseña del administrador (la escribe la persona) no genera
    codigo, salida = davgen(proyecto, ['generar', '--local'])
    assert codigo == 1 and 'admin_password' in salida
    assert 'admin_password' in leer(SKILL, 'SKILL.md').split('## Paso 3')[0]
    configuracion.fijar_valor(proyecto, 'seguridad', 'admin_password', 'LaPusoLaPersona9',
                              archivo='_acceso.desarrollo.ini')
    codigo, salida = davgen(proyecto, ['generar', '--local'])
    assert codigo == 0, salida
    generado = os.path.join(proyecto, '03-Backend', '_backendGenerado')
    for parte in ('database', 'backend', 'frontend', 'RESUMEN.md'):
        assert os.path.exists(os.path.join(generado, parte)), parte   # el cuadro del paso 3
    assert os.path.isfile(os.path.join(generado, 'database', '02_negocio.sql'))
    assert 'tbl_bib_libro' in leer(generado, 'database', '02_negocio.sql')


# ── el plugin ──────────────────────────────────────────────────────────────
def test_el_plugin_y_el_catalogo_son_coherentes_con_la_version():
    plugin = json.loads(leer(RAIZ_REPO, '.claude-plugin', 'plugin.json'))
    catalogo = json.loads(leer(RAIZ_REPO, '.claude-plugin', 'marketplace.json'))
    assert plugin['version'] == VERSION, 'subir también la versión de .claude-plugin/plugin.json'
    assert re.fullmatch(r'[a-z0-9-]+', plugin['name'])
    (entrada_catalogo,) = catalogo['plugins']
    assert entrada_catalogo['name'] == plugin['name']
    assert entrada_catalogo['source'] == './'                # el plugin es el repositorio
    assert catalogo['owner']['name'] and entrada_catalogo['description']
    # la skill instala davgen desde «dos carpetas más arriba»: debe ser la raíz
    assert os.path.isfile(os.path.join(SKILL, '..', '..', 'pyproject.toml'))
    assert '../../pyproject.toml' in leer(SKILL, 'SKILL.md')


# ── el .zip descargable ────────────────────────────────────────────────────
def test_el_zip_trae_la_skill_y_el_codigo_para_instalarse_solo(tmp_path):
    import empaquetar_skill as empaquetador                 # scripts/ (ver conftest)
    ruta = empaquetador.empaquetar(str(tmp_path / 'skill.zip'))
    with zipfile.ZipFile(ruta) as z:
        nombres = set(z.namelist())
        assert all(n.startswith(f'{NOMBRE}/') for n in nombres)     # una sola carpeta arriba
        for esperado in ('SKILL.md', 'referencias/mockup.md', 'ejemplos/biblioteca.html',
                         'fuente/pyproject.toml', 'fuente/LICENSE', 'fuente/README.md',
                         'fuente/src/davgen/cli.py', 'fuente/src/davgen/nucleo/version.py',
                         'fuente/src/davgen/plantillas/proyecto/configtotal.ini'):
            assert f'{NOMBRE}/{esperado}' in nombres, esperado
        assert not any('__pycache__' in n or n.endswith('.pyc') for n in nombres)
        assert not any('/tests/' in n or '.git' in n for n in nombres)
        assert f"VERSION = '{VERSION}'" in z.read(
            f'{NOMBRE}/fuente/src/davgen/nucleo/version.py').decode('utf-8')
    assert 'fuente/' in leer(SKILL, 'SKILL.md')              # la skill sabe buscarlo ahí
    otra = empaquetador.empaquetar(str(tmp_path / 'otra.zip'))
    assert open(ruta, 'rb').read() == open(otra, 'rb').read()        # reproducible
