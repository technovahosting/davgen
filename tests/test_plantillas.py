"""Plantillas como datos: resolución proyecto → paquete."""
import os

import pytest
from conftest import leer

from davgen.nucleo import plantillas


def test_el_paquete_trae_las_plantillas():
    todas = plantillas.listar()
    assert len(todas) >= 60
    for esperada in ('backend/controller_tabla.php', 'frontend/pagina.jsx',
                     'sql/seguridad.sql', 'google/boton_google.jsx',
                     'proyecto/configtotal.ini'):
        assert esperada in todas


def test_toda_plantilla_usada_por_el_codigo_existe():
    """Importar los generadores registra cada plantilla que consumen; ninguna
    puede faltar en el paquete (rompería en el equipo del usuario)."""
    from davgen import cli  # noqa: F401  (importa todos los generadores)
    registradas = set(plantillas._registro)
    assert len(registradas) >= 60
    assert registradas <= set(plantillas.listar())


def test_las_plantillas_no_llevan_retornos_de_carro():
    for ruta in plantillas.listar():
        with open(os.path.join(plantillas.DIR_PAQUETE, *ruta.split('/')), 'rb') as f:
            assert b'\r' not in f.read(), ruta


def test_plantilla_inexistente_da_un_error_claro():
    with pytest.raises(FileNotFoundError, match='no/existe.txt'):
        plantillas.cargar('no/existe.txt')


def test_copiar_al_proyecto_no_pisa_sin_forzar(tmp_path):
    destino = plantillas.copiar_al_proyecto('frontend/pagina.jsx', str(tmp_path))
    assert os.path.isfile(destino)
    with pytest.raises(FileExistsError):
        plantillas.copiar_al_proyecto('frontend/pagina.jsx', str(tmp_path))
    plantillas.copiar_al_proyecto('frontend/pagina.jsx', str(tmp_path),
                                  sobrescribir=True)


def test_avisa_de_archivos_que_no_son_plantillas(tmp_path):
    carpeta = tmp_path / '_plantillas' / 'frontend'
    carpeta.mkdir(parents=True)
    (carpeta / 'pagina.jsx').write_text('x', encoding='utf-8')
    (carpeta / 'pajina.jsx').write_text('x', encoding='utf-8')     # mal escrito
    assert plantillas.propias(str(tmp_path)) == ['frontend/pagina.jsx']
    assert plantillas.desconocidas(str(tmp_path)) == ['frontend/pajina.jsx']


def test_la_plantilla_del_proyecto_gana_y_se_puede_volver_atras(tmp_path):
    from davgen.nucleo import gen_backend
    original = gen_backend._PAGINACION
    carpeta = tmp_path / '_plantillas' / 'backend'
    carpeta.mkdir(parents=True)
    (carpeta / 'paginacion.php').write_text('// PROPIA\n', encoding='utf-8')

    assert plantillas.usar_proyecto(str(tmp_path)) == ['backend/paginacion.php']
    assert gen_backend._PAGINACION == '// PROPIA\n'
    assert plantillas.origen('backend/paginacion.php') == 'proyecto'

    plantillas.usar_proyecto(None)
    assert gen_backend._PAGINACION == original
    assert plantillas.origen('backend/paginacion.php') == 'paquete'


def test_generar_usa_la_plantilla_propia_del_proyecto(proyecto_nuevo, davgen):
    """De punta a punta: copiar una plantilla, editarla y regenerar."""
    codigo, _ = davgen(proyecto_nuevo, ['plantillas', 'copiar', 'frontend/api.js'])
    assert codigo == 0
    propia = os.path.join(proyecto_nuevo, '_plantillas', 'frontend', 'api.js')
    with open(propia, encoding='utf-8') as f:
        texto = f.read()
    with open(propia, 'w', encoding='utf-8', newline='\n') as f:
        f.write('// MARCA-DEL-PROYECTO\n' + texto)

    codigo, salida = davgen(proyecto_nuevo, ['generar', '--local'])
    assert codigo == 0, salida
    assert 'plantilla(s) propia(s)' in salida
    generado = leer(proyecto_nuevo, '03-Backend', '_backendGenerado', 'frontend',
                    'src', 'services', 'api.js')
    assert 'MARCA-DEL-PROYECTO' in generado
