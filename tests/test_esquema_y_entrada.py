"""Mockup → entidades → tablas: el corazón del camino `tipo = mockup`."""
import os

from conftest import RAIZ_REPO

from davgen.nucleo import entrada, esquema

MOCKUP = os.path.join(RAIZ_REPO, 'ejemplos', 'biblioteca', 'index.html')


def test_nombres_normalizados():
    assert esquema.a_snake_case('Año de Publicación') == 'ano_de_publicacion'
    assert esquema.singularizar('libros') == 'libro'
    assert esquema.nombre_entidad('Préstamos') == 'prestamo'
    assert esquema.a_clase('tbl_bib_libro') == 'TblBibLibro'


def test_mockup_detecta_las_tres_entidades():
    entidades = {e['nombre']: e for e in entrada.analizar_mockup(MOCKUP)}
    assert set(entidades) == {'libro', 'socio', 'prestamo'}
    campos = [c['nombre'] for c in entidades['libro']['campos']]
    assert campos[:3] == ['titulo', 'autor', 'isbn']
    assert 'accion' not in campos and 'acciones' not in campos


def test_select_se_convierte_en_enum_sin_la_opcion_vacia():
    entidades = {e['nombre']: e for e in entrada.analizar_mockup(MOCKUP)}
    genero = next(c for c in entidades['libro']['campos'] if c['nombre'] == 'genero')
    assert genero['opciones'] == ['novela', 'ensayo', 'infantil', 'tecnico']


def test_tablas_con_prefijo_de_modulo_columnas_de_sistema_y_fk():
    tablas = esquema.construir_tablas(entrada.analizar_mockup(MOCKUP), 'bib')
    por_nombre = {t['tabla']: t for t in tablas}
    assert set(por_nombre) == {'tbl_bib_libro', 'tbl_bib_socio', 'tbl_bib_prestamo'}

    libro = {c['COLUMN_NAME']: c for c in por_nombre['tbl_bib_libro']['columnas']}
    assert libro['id']['COLUMN_KEY'] == 'PRI'
    assert 'AUTO_INCREMENT' in libro['id']['SQL_FULL']
    assert {'activo', 'created_at', 'updated_at'} <= set(libro)
    assert libro['genero']['SQL_FULL'].startswith("ENUM('novela'")
    assert por_nombre['tbl_bib_libro']['vista'] == 'vis_bib_libro'

    prestamo = {c['COLUMN_NAME']: c for c in por_nombre['tbl_bib_prestamo']['columnas']}
    assert prestamo['libro_id']['FK'] == 'libro'
    assert prestamo['socio_id']['FK'] == 'socio'


def test_orden_por_dependencias_pone_primero_las_tablas_referenciadas():
    tablas = esquema.ordenar_por_dependencias(
        esquema.construir_tablas(entrada.analizar_mockup(MOCKUP), 'bib'))
    orden = [t['tabla'] for t in tablas]
    assert orden.index('tbl_bib_prestamo') > orden.index('tbl_bib_libro')
    assert orden.index('tbl_bib_prestamo') > orden.index('tbl_bib_socio')


def test_html_sin_formularios_no_inventa_entidades(tmp_path):
    ruta = tmp_path / 'vacio.html'
    ruta.write_text('<html><body><h1>Hola</h1><p>Sin datos</p></body></html>',
                    encoding='utf-8')
    assert entrada.analizar_mockup(str(ruta)) == []
