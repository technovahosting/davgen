"""Privacidad, términos de uso, conservación de datos y accesibilidad del
sistema generado."""
import os
import re

import pytest
from conftest import leer

from davgen.nucleo import configuracion, gen_legal, gen_servicios, gen_sql

GEN = ('03-Backend', '_backendGenerado')


def _front(proyecto, *partes) -> str:
    return leer(proyecto, *GEN, 'frontend', 'src', *partes)


def _back(proyecto, *partes) -> str:
    return leer(proyecto, *GEN, 'backend', *partes)


# ── privacidad y términos ──────────────────────────────────────────────────
def test_se_genera_el_aviso_legal_y_la_app_nueva_lo_muestra(proyecto_generado):
    aviso = _front(proyecto_generado, 'components', 'generados', 'AvisoLegal.jsx')
    assert 'Política de privacidad' in aviso and 'Términos de uso' in aviso
    assert '__' not in re.sub(r'__[a-z]', '', aviso)        # sin marcadores sin reemplazar
    app = _front(proyecto_generado, 'App.jsx')
    assert "import AvisoLegal from './components/generados/AvisoLegal'" in app
    assert app.count('<AvisoLegal') == 2                    # pie del ingreso y menú
    assert os.path.isfile(os.path.join(proyecto_generado, *GEN, 'frontend', 'src',
                                       'components', 'generados', 'LEEME-LEGAL.md'))


def test_los_textos_toman_los_datos_de_la_seccion_legal(proyecto_nuevo, davgen):
    for clave, valor in (('responsable', 'Biblioteca Ejemplo S.R.L.'),
                         ('contacto', 'datos@ejemplo.test'),
                         ('jurisdiccion', 'Bolivia'),
                         ('alojamiento', 'Hosting Ejemplo (Bolivia)'),
                         ('vigente_desde', '1 de marzo de 2026'),
                         ('retencion_bitacora_dias', '90')):
        configuracion.fijar_valor(proyecto_nuevo, 'legal', clave, valor)
    assert davgen(proyecto_nuevo, ['generar', '--local'])[0] == 0
    aviso = _front(proyecto_nuevo, 'components', 'generados', 'AvisoLegal.jsx')
    assert "const RESPONSABLE = 'Biblioteca Ejemplo S.R.L.'" in aviso
    assert "const CONTACTO = 'datos@ejemplo.test'" in aviso
    assert "const JURISDICCION = 'Bolivia'" in aviso
    assert "const ALOJAMIENTO = 'Hosting Ejemplo (Bolivia)'" in aviso
    assert "const VIGENTE_DESDE = '1 de marzo de 2026'" in aviso
    assert 'const DIAS_BITACORA = 90' in aviso
    # el mismo plazo llega a la base (semilla) y a la limpieza del backend
    assert "('retencion_bitacora_dias', '90'," in leer(
        proyecto_nuevo, *GEN, 'database', '01_seguridad.sql')
    assert 'DIAS_BITACORA = 90;' in _back(proyecto_nuevo, 'app', 'Utils', 'Retencion.php')


def test_los_textos_cubren_lo_que_protege_al_responsable_y_al_usuario(proyecto_generado):
    aviso = _front(proyecto_generado, 'components', 'generados', 'AvisoLegal.jsx')
    for titulo in ('Por qué podemos usarlos', 'Con quién se comparten', 'Dónde se guardan',
                   'Cómo se protegen', 'Menores de edad', 'Tus derechos', 'Cambios',
                   'Aceptación', 'Lo que cargas', 'Disponibilidad', 'Responsabilidad'):
        assert f'<h4>{titulo}</h4>' in aviso, titulo
    assert 'Hasta donde la ley lo permita' in aviso          # límite de responsabilidad…
    assert 'no limita los derechos que la ley te' in aviso   # …sin cláusula abusiva
    assert 'tal como está' in aviso
    assert "const ALOJAMIENTO = ''" in aviso and "const VIGENTE_DESDE = ''" in aviso
    # la pantalla de ingreso avisa que entrar es aceptar; el menú no lo repite
    app = _front(proyecto_generado, 'App.jsx')
    assert app.count('<AvisoLegal className="opacity-70" conAceptacion />') == 1
    assert 'Al ingresar aceptas los términos de uso y la política de privacidad.' in aviso


def test_la_guia_legal_dice_quien_responde_y_que_revisar(proyecto_generado):
    guia = _front(proyecto_generado, 'components', 'generados', 'LEEME-LEGAL.md')
    assert '## Quién responde por qué' in guia
    assert 'sin garantía (licencia MIT)' in guia and 'no da asesoría legal' in guia
    assert '## Lista para el desarrollador antes de publicar' in guia
    assert guia.count('- [ ]') >= 12
    assert 'no asesoría legal' in guia and 'Decreto Supremo\n  1793' in guia
    for clave in ('responsable', 'contacto', 'jurisdiccion', 'alojamiento', 'vigente_desde',
                  'retencion_bitacora_dias'):
        assert f'`{clave}`' in guia, clave
        assert re.search(rf'(?m)^{clave} =', configuracion.PLANTILLA), clave


def test_el_repositorio_trae_su_descargo_de_responsabilidad():
    from conftest import RAIZ_REPO
    descargo = leer(RAIZ_REPO, 'DESCARGO.md')
    for frase in ('sin garantía de ningún tipo', 'no responden por daños',
                  'no son asesoría\nlegal', 'no tiene telemetría', 'no trae ninguna contraseña',
                  'No pegues en el chat contraseñas', 'vale la licencia'):
        assert frase in descargo, frase
    for enlace in re.findall(r'\]\(([^)#:]+)\)', descargo):
        assert os.path.isfile(os.path.join(RAIZ_REPO, enlace)), enlace
    assert '(DESCARGO.md)' in leer(RAIZ_REPO, 'README.md')


def test_un_dato_legal_con_comillas_no_rompe_el_javascript(tmp_path):
    cfg = {'nombre': "Sis'tema", 'google_auth_activo': False,
           'legal': {'responsable': "O'Brien <script>{x}</script>", 'contacto': 'a"b`c\\d',
                     'jurisdiccion': 'Bolivia\n', 'retencion_bitacora_dias': 0}}
    gen_legal.generar_legal(cfg, str(tmp_path))
    aviso = leer(str(tmp_path), 'components', 'generados', 'AvisoLegal.jsx')
    assert "const RESPONSABLE = 'OBrien scriptx/script'" in aviso
    assert "const CONTACTO = 'abcd'" in aviso
    assert "const SISTEMA = 'Sistema'" in aviso
    assert 'const DIAS_BITACORA = 0' in aviso


def test_el_plazo_de_la_bitacora_debe_ser_un_numero(proyecto_nuevo, davgen):
    configuracion.fijar_valor(proyecto_nuevo, 'legal', 'retencion_bitacora_dias', 'un año')
    codigo, salida = davgen(proyecto_nuevo, ['generar', '--local'])
    assert codigo == 1 and 'retencion_bitacora_dias' in salida


def test_no_hay_aviso_de_cookies_porque_no_hay_cookies(proyecto_generado):
    """El sistema guarda la sesión en el almacenamiento local y no carga nada
    de terceros: el texto de privacidad lo dice y no se pide un permiso vacío."""
    aviso = _front(proyecto_generado, 'components', 'generados', 'AvisoLegal.jsx')
    assert 'no usa cookies' in aviso
    api = _front(proyecto_generado, 'services', 'api.js')
    assert 'localStorage' in api and 'document.cookie' not in api
    raiz = os.path.join(proyecto_generado, *GEN, 'frontend', 'src')
    for base, _dirs, nombres in os.walk(raiz):
        for n in nombres:
            if n.endswith(('.js', '.jsx')):
                assert 'document.cookie' not in leer(base, n), n
    assert 'aviso de cookies' in _front(proyecto_generado, 'components', 'generados',
                                        'LEEME-LEGAL.md')


# ── conservación de datos ──────────────────────────────────────────────────
def test_la_limpieza_borra_lo_vencido_y_nunca_los_datos_del_negocio(proyecto_generado):
    php = _back(proyecto_generado, 'app', 'Utils', 'Retencion.php')
    for tabla in ('tbl_seg_bitacora', 'tbl_seg_codigo_verificacion', 'tbl_seg_token_reset',
                  'personal_access_tokens'):
        assert f"DB::table('{tabla}')" in php, tabla
    assert re.findall(r"DB::table\('(\w+)'\)", php).count('tbl_seg_usuario') == 0
    assert 'tbl_bib_' not in php and 'tbl_seg_archivo' not in php
    assert "Parametro::entero('retencion_bitacora_dias', self::DIAS_BITACORA)" in php
    assert 'if ($dias > 0)' in php                          # 0 = no se borra
    assert 'catch (\\Throwable' in php                      # nunca tumba el ingreso
    assert 'DIAS_BITACORA = 365;' in php
    auth = _back(proyecto_generado, 'app', 'Http', 'Controllers', 'AuthController.php')
    assert '\\App\\Utils\\Retencion::quizas();' in auth
    assert "('retencion_bitacora_dias', '365'," in leer(
        proyecto_generado, *GEN, 'database', '01_seguridad.sql')
    assert "('retencion_bitacora_dias', '365'," in leer(
        proyecto_generado, '02-Base-de-datos', '00-seguridad.sql')


def test_la_semilla_de_parametros_llega_entera_a_la_base(proyecto_generado):
    """davgen parte el script por «;»: un punto y coma dentro de una descripción
    cortaba el INSERT de parámetros a la mitad (error 1064 al aplicar seeds)."""
    script = leer(proyecto_generado, *GEN, 'database', '01_seguridad.sql')
    sentencias = [s for s in gen_sql.sentencias_script(script)
                  if 'INTO `tbl_seg_parametro`' in s]
    assert len(sentencias) == 1
    sentencia = sentencias[0]
    assert "'retencion_bitacora_dias'" in sentencia and "'max_archivo_mb'" in sentencia
    assert sentencia.count('(') == sentencia.count(')')
    assert sentencia.count("'") % 2 == 0


# ── accesibilidad: teclado y lectores de pantalla ──────────────────────────
def test_las_pantallas_generadas_nombran_sus_controles(proyecto_generado):
    pagina = _front(proyecto_generado, 'pages', 'generados', 'LibroPage.jsx')
    for esperado in ('aria-label={`Buscar en ${TITULO}`}', 'aria-label="Página anterior"',
                     'aria-label="Página siguiente"', 'aria-label="Filas por página"',
                     'aria-label={`Editar ${TITULO} ${r[PK]}`}',
                     'aria-label={`Dar de baja ${TITULO} ${r[PK]}`}',
                     '<caption className="sr-only">', 'scope="col"'):
        assert esperado in pagina, esperado
    # ningún botón cuyo único contenido sea un símbolo queda sin nombre
    for boton in re.findall(r'<button[^>]*>[«»✕×]</button>', pagina, flags=re.S):
        assert 'aria-label=' in boton, boton


def test_las_ventanas_se_manejan_con_el_teclado(proyecto_generado):
    pagina = _front(proyecto_generado, 'pages', 'generados', 'LibroPage.jsx')
    assert pagina.count('role="dialog"') == 1 and pagina.count('role="alertdialog"') == 1
    assert pagina.count('aria-modal="true"') == 2
    assert pagina.count("e.key === 'Escape'") == 2          # Esc cierra las dos
    assert 'autoFocus={i === 0}' in pagina                  # el foco entra al formulario
    assert 'aria-labelledby="titulo-formulario"' in pagina and 'id="titulo-formulario"' in pagina
    assert '<dialog' not in pagina                          # <dialog> sin showModal no atrapa el foco
    aviso = _front(proyecto_generado, 'components', 'generados', 'AvisoLegal.jsx')
    assert 'role="dialog"' in aviso and "e.key === 'Escape'" in aviso
    assert 'origen.current?.focus()' in aviso               # devuelve el foco al cerrar


def test_los_avisos_y_errores_se_anuncian(proyecto_generado):
    pagina = _front(proyecto_generado, 'pages', 'generados', 'LibroPage.jsx')
    assert "role={aviso.startsWith('Error') ? 'alert' : 'status'}" in pagina
    assert '<p role="alert" className="mb-3 text-error">' in pagina
    assert 'role="status" aria-label="Cargando"' in pagina


def test_la_app_nueva_se_recorre_con_el_teclado(proyecto_generado):
    app = _front(proyecto_generado, 'App.jsx')
    assert 'Saltar al contenido' in app and 'href="#contenido"' in app
    assert '<main id="contenido" tabIndex={-1}' in app
    assert 'className="drawer-toggle" aria-label="Menú"' in app
    # los campos del ingreso tienen etiqueta visible, no solo un placeholder
    assert '<span className="text-sm">Correo electrónico</span>' in app
    assert '<span className="text-sm">Contraseña</span>' in app
    assert 'placeholder="Contraseña"' not in app


def test_ninguna_plantilla_trae_imagenes_sin_texto_alternativo(proyecto_generado):
    raiz = os.path.join(proyecto_generado, *GEN, 'frontend', 'src')
    vistos = 0
    for base, _dirs, nombres in os.walk(raiz):
        for n in nombres:
            if not n.endswith('.jsx'):
                continue
            vistos += 1
            texto = leer(base, n)
            for img in re.findall(r'<img\b[^>]*>', texto, flags=re.S):
                assert re.search(r'\balt=', img), f'{n}: {img}'
            assert not re.search(r'<(div|span)\b[^>]*\bonClick=', texto), \
                f'{n}: algo que se pulsa y no es un botón'
    assert vistos > 5


@pytest.mark.parametrize('original, esperado', [
    ('<html lang="en">\n<title>frontend</title>', '<html lang="es">\n<title>Mi &amp; Sistema</title>'),
    ('<html lang="en">\n<title>Vite + React</title>', '<html lang="es">\n<title>Mi &amp; Sistema</title>'),
    ('<html lang="pt">\n<title>Loja</title>', None),          # lo que puso el usuario no se toca
])
def test_el_index_declara_el_idioma_y_el_nombre(tmp_path, original, esperado):
    (tmp_path / 'index.html').write_text(original, encoding='utf-8')
    cambio = gen_servicios.ajustar_index_html(str(tmp_path), 'Mi & Sistema')
    assert cambio is (esperado is not None)
    assert leer(str(tmp_path), 'index.html') == (esperado or original)
    assert gen_servicios.ajustar_index_html(str(tmp_path), 'Mi & Sistema') is False   # idempotente
    assert gen_servicios.ajustar_index_html(str(tmp_path / 'no-existe'), 'X') is False
