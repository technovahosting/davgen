"""De punta a punta: `davgen nuevo` + `davgen generar --local` sobre el mockup
de ejemplo. Sin base de datos, sin FTP y sin Laravel/React instalados."""
import json
import os
import re
import shutil
import subprocess

import generar_ejemplo
import pytest
from conftest import CLAVE_PRUEBA, archivos, leer

GEN = ('03-Backend', '_backendGenerado')


def _php():
    """Ejecutable de PHP si hay uno (para validar la sintaxis), o None."""
    candidatos = [os.environ.get('DAVGEN_PHP'), shutil.which('php')]
    return next((c for c in candidatos if c and os.path.isfile(c)), None)


def test_nuevo_crea_la_estructura_y_no_genera_codigo(proyecto_nuevo):
    for carpeta in ('00-Requisitos', '01-Mockups', '02-Base-de-datos',
                    '03-Backend', '04-Frontend', '05-Testing', '_prompts'):
        assert os.path.isdir(os.path.join(proyecto_nuevo, carpeta)), carpeta
    for archivo in ('_configtotal.ini', '.gitignore',
                    '_acceso.desarrollo.ini', '_acceso.produccion.ini',
                    '_acceso.desarrollo.ejemplo.ini', '_acceso.produccion.ejemplo.ini',
                    'leeme.html', '_davgen.leeme.md',
                    os.path.join('02-Base-de-datos', '00-seguridad.sql')):
        assert os.path.isfile(os.path.join(proyecto_nuevo, archivo)), archivo
    assert not os.path.isdir(os.path.join(proyecto_nuevo, *GEN))


def test_el_gitignore_del_proyecto_protege_los_secretos(proyecto_nuevo):
    lineas = leer(proyecto_nuevo, '.gitignore').splitlines()
    assert '_acceso.*.ini' in lineas and '!_acceso.*.ejemplo.ini' in lineas
    # la configuración del proyecto no lleva contraseñas: se versiona
    assert '_configtotal.ini' not in lineas
    assert CLAVE_PRUEBA not in leer(proyecto_nuevo, '_configtotal.ini')
    assert 'password' not in leer(proyecto_nuevo, '_configtotal.ini')
    # los accesos sí, y sus ejemplos van sin ellas
    assert CLAVE_PRUEBA in leer(proyecto_nuevo, '_acceso.desarrollo.ini')
    assert CLAVE_PRUEBA not in leer(proyecto_nuevo, '_acceso.desarrollo.ejemplo.ini')
    produccion = leer(proyecto_nuevo, '_acceso.produccion.ini')
    assert CLAVE_PRUEBA not in produccion          # cada entorno, su contraseña
    clave_prod = [x.split('=', 1)[1].strip() for x in produccion.splitlines()
                  if x.startswith('admin_password')][0]
    assert clave_prod == ''                        # davgen no inventa ninguna


def test_genera_las_cuatro_capas(proyecto_generado):
    base = os.path.join(proyecto_generado, *GEN)
    esperados = [
        'database/01_seguridad.sql', 'database/02_negocio.sql',
        'database/03_procedimientos.sql',
        'backend/routes/api.php', 'backend/routes/bib_api.php',
        'backend/routes/seg_api.php', 'backend/bootstrap/app.php',
        'backend/app/Services/BaseService.php',
        'backend/app/Services/TblBibLibroService.php',
        'backend/app/Http/Controllers/bib/BibLibroController.php',
        'backend/app/Http/Controllers/bib/BibPrestamoController.php',
        'backend/app/Http/Requests/TblBibLibroRequest.php',
        'backend/tests/Feature/Generados/AuthTest.php',
        'frontend/src/App.jsx', 'frontend/src/services/api.js',
        'frontend/src/services/libroService.js',
        'frontend/src/pages/generados/rutas.jsx',
        'frontend/src/components/generados/BotonGoogle.jsx',
        'testing/api.http', 'testing/postman_collection.json',
        'documentacion/guia.md', 'documentacion/openapi.json', 'RESUMEN.md',
        '.davgen-integridad.json',
    ]
    presentes = set(archivos(base))
    faltan = [e for e in esperados if e not in presentes]
    assert not faltan, f"faltan: {faltan}"


def test_los_sql_traen_tablas_vistas_y_un_sp_por_tabla(proyecto_generado):
    base = os.path.join(proyecto_generado, *GEN, 'database')
    negocio = leer(base, '02_negocio.sql')
    for tabla in ('tbl_bib_libro', 'tbl_bib_socio', 'tbl_bib_prestamo'):
        assert f'CREATE TABLE IF NOT EXISTS `{tabla}`' in negocio or \
               f'`{tabla}`' in negocio
    assert 'vis_bib_prestamo' in negocio
    sps = leer(base, '03_procedimientos.sql')
    assert len(re.findall(r'CREATE PROCEDURE', sps)) == 3
    assert 'pcruTblBibLibro' in sps and 'LAST_INSERT_ID()' in sps


def test_el_seed_del_admin_usa_la_contrasena_del_ini(proyecto_generado):
    bcrypt = pytest.importorskip('bcrypt')
    sql = leer(proyecto_generado, *GEN, 'database', '01_seguridad.sql')
    hashes = re.findall(r'\$2y\$12\$[./A-Za-z0-9]{53}', sql)
    assert hashes, 'no hay hash bcrypt del admin'
    h = hashes[0].replace('$2y$', '$2b$').encode()
    assert bcrypt.checkpw(CLAVE_PRUEBA.encode(), h)


def test_la_contrasena_del_admin_no_queda_en_archivos_que_se_versionan(proyecto_generado):
    """Solo puede estar en el archivo de accesos (que no se versiona o va
    cifrado). Los archivos de prueba generados llevan un marcador."""
    con_clave = []
    for rel in archivos(proyecto_generado):
        with open(os.path.join(proyecto_generado, rel), encoding='utf-8', errors='replace') as f:
            if CLAVE_PRUEBA in f.read():
                con_clave.append(rel)
    assert con_clave == ['_acceso.desarrollo.ini']
    api = leer(proyecto_generado, *GEN, 'testing', 'api.http')
    assert 'ESCRIBIR-LA-CONTRASENA-DEL-ADMIN' in api
    ps1 = leer(proyecto_generado, *GEN, 'testing', 'pruebas-api.ps1')
    assert '$Password = $env:DAVGEN_ADMIN_PASSWORD' in ps1


def test_google_viene_apagado_y_sin_cuenta_duena(proyecto_generado):
    sql = leer(proyecto_generado, *GEN, 'database', '01_seguridad.sql')
    assert "('google_auth_activo',  '0'" in sql
    assert re.search(r"\('google_client_id',\s*''", sql)
    assert 'sin [seguridad] owner_email' in sql
    assert 'apps.googleusercontent.com' not in sql


def test_lo_generado_no_contiene_datos_del_autor_del_generador(proyecto_generado):
    """Nada de lo que davgen escribe en un proyecto ajeno puede llevar
    correos, dominios, IPs o identificadores de quien desarrolla davgen."""
    prohibido = re.compile(
        # por su FORMA, no por su valor: este archivo también se publica
        r'\b(?!persona@|cuenta@|usuario@|ejemplo@)[\w.+-]+@(gmail|hotmail|outlook|yahoo)\.'
        r'|\d{12}-[a-z0-9]{32}\.apps\.googleusercontent\.com'     # Client ID real
        r'|\bu\d{9}\b'                                            # usuarios de hosting
        r'|\b(?!127\.0\.0\.1\b|0\.0\.0\.0\b)(?:\d{1,3}\.){3}\d{1,3}\b'   # IPs
        r'|validar_acceso|davgen_lock|davgen4', re.I)             # restos de la v4
    hallazgos = []
    for rel in archivos(proyecto_generado):
        ruta = os.path.join(proyecto_generado, rel)
        with open(ruta, encoding='utf-8', errors='replace') as f:
            m = prohibido.search(f.read())
        if m:
            hallazgos.append(f'{rel}: {m.group(0)}')
    assert not hallazgos, hallazgos


def test_rutas_publicas_y_propias(proyecto_generado):
    bootstrap = leer(proyecto_generado, *GEN, 'backend', 'bootstrap', 'app.php')
    assert "routes/Custom/*.php" in bootstrap
    api = leer(proyecto_generado, *GEN, 'backend', 'routes', 'api.php')
    assert "RateLimiter::for('publico'" in api


def test_el_controller_manda_null_en_fechas_y_enum_vacios(proyecto_generado):
    ctrl = leer(proyecto_generado, *GEN, 'backend', 'app', 'Http',
                'Controllers', 'bib', 'BibPrestamoController.php')
    assert "'pfecha_prestamo' => $request->input('pfecha_prestamo') ?: null" in ctrl
    assert "'psituacion' => $request->input('psituacion') ?: null" in ctrl


def test_el_boton_de_google_puede_dibujarse(proyecto_generado):
    """Dos fallas que impedían que el botón apareciera: comparar el parámetro
    solo con '1' (la API entrega true) y devolver null antes de que exista el
    nodo donde Google lo dibuja."""
    boton = leer(proyecto_generado, *GEN, 'frontend', 'src', 'components',
                 'generados', 'BotonGoogle.jsx')
    assert "'true'" in boton and ".toLowerCase()" in boton
    assert 'if (!activo) return null' not in boton
    assert "display: activo ? 'grid' : 'none'" in boton
    assert '<div ref={contenedor} />' in boton


def test_la_app_lleva_el_nombre_del_sistema(proyecto_generado):
    """Hasta la v4 la pantalla mostraba el marcador «__NOMBRE__» sin reemplazar."""
    app = leer(proyecto_generado, *GEN, 'frontend', 'src', 'App.jsx')
    assert '__NOMBRE__' not in app
    assert '>Biblioteca<' in app and "return 'Biblioteca'" in app


def test_interfaz_adaptable_y_con_tema_claro_oscuro_o_del_sistema(proyecto_generado):
    src = os.path.join(proyecto_generado, *GEN, 'frontend', 'src')
    app = leer(src, 'App.jsx')
    # adaptable: menú como cajón, fijo solo en pantallas grandes
    assert 'drawer lg:drawer-open' in app and 'lg:hidden' in app
    # sin colores fijos: todo sale de los colores semánticos del tema
    assert not re.search(r'#[0-9a-fA-F]{6}\b|rgba?\(', app)
    assert 'bg-base-100' in app and 'style={{' not in app
    # tema: sistema por defecto, y la elección se recuerda
    assert "import './services/tema'" in app and '<SelectorTema />' in app
    tema = leer(src, 'services', 'tema.js')
    assert "return TEMAS.includes(t) ? t : 'sistema'" in tema
    assert 'prefers-color-scheme: dark' in tema and "removeAttribute('data-theme')" in tema
    selector = leer(src, 'components', 'generados', 'SelectorTema.jsx')
    for opcion in ("'sistema'", "'claro'", "'oscuro'"):
        assert opcion in selector
    # los dos temas declarados, con el oscuro siguiendo al sistema
    from davgen.nucleo import gen_servicios
    assert 'light --default, dark --prefersdark' in gen_servicios._INDEX_CSS_TAILWIND


def test_nombre_con_caracteres_raros_no_rompe_el_jsx(tmp_path):
    from davgen.nucleo import gen_servicios
    ruta = gen_servicios.generar_app_jsx(str(tmp_path), "Mi {Sis}tema <b>'x'</b>")
    texto = open(ruta, encoding='utf-8').read()
    assert 'Mi Sistema bx/b' in texto and '__NOMBRE__' not in texto
    assert gen_servicios.generar_app_jsx(str(tmp_path), 'Otro') is None      # no pisa


def test_json_generados_son_validos(proyecto_generado):
    base = os.path.join(proyecto_generado, *GEN)
    for rel in ('documentacion/openapi.json', 'testing/postman_collection.json',
                '.davgen-integridad.json', '.davgen-manifest.json'):
        with open(os.path.join(base, rel), encoding='utf-8') as f:
            json.load(f)


def test_la_generacion_es_reproducible(tmp_path):
    """Misma entrada + misma fecha (SOURCE_DATE_EPOCH) = misma salida, salvo el
    hash bcrypt del admin, que lleva sal aleatoria por diseño."""
    def generar(nombre):
        destino = generar_ejemplo.preparar(str(tmp_path / nombre), extras=True,
                                           admin_password=CLAVE_PRUEBA)
        codigo, salida = generar_ejemplo.en(destino, ['generar', '--local'],
                                            silencioso=True)
        assert codigo == 0, salida
        return destino

    a, b = generar('a'), generar('b')
    assert archivos(a) == archivos(b)
    con_sal = re.compile(r'\$2y\$12\$[./A-Za-z0-9]{53}')
    distintos = []
    for rel in archivos(a):
        if rel.endswith(('.davgen-integridad.json', '.davgen-manifest.json')):
            continue        # guardan el hash del .sql que lleva la sal
        if rel == '_acceso.produccion.ini':
            continue        # contraseña de producción: aleatoria por diseño
        ta = con_sal.sub('HASH', leer(a, rel))
        tb = con_sal.sub('HASH', leer(b, rel))
        if ta != tb:
            distintos.append(rel)
    assert not distintos, distintos


def test_regenerar_no_deja_archivos_de_tablas_que_ya_no_existen(proyecto_nuevo, davgen):
    codigo, _ = davgen(proyecto_nuevo, ['generar', '--local'])
    assert codigo == 0
    ctrl = os.path.join(proyecto_nuevo, *GEN, 'backend', 'app', 'Http',
                        'Controllers', 'bib', 'BibSocioController.php')
    assert os.path.isfile(ctrl)
    ini = os.path.join(proyecto_nuevo, '_configtotal.ini')
    with open(ini, encoding='utf-8') as f:
        texto = f.read()
    with open(ini, 'w', encoding='utf-8') as f:
        f.write(texto.replace('excluir =', 'excluir = socio'))
    codigo, _ = davgen(proyecto_nuevo, ['generar', '--local'])
    assert codigo == 0
    assert not os.path.isfile(ctrl)


def test_verificar_detecta_una_edicion_manual(copia_generado, davgen):
    codigo, salida = davgen(copia_generado, ['verificar'])
    assert codigo == 0, salida
    servicio = os.path.join(copia_generado, *GEN, 'frontend', 'src', 'services',
                            'libroService.js')
    with open(servicio, 'a', encoding='utf-8') as f:
        f.write('\n// editado a mano\n')
    codigo, salida = davgen(copia_generado, ['verificar'])
    assert codigo == 1
    assert 'libroService.js' in salida


def test_modo_local_no_toca_nada_fuera_del_proyecto(proyecto_generado):
    """--local no crea Laravel ni React ni instala dependencias."""
    assert not os.path.exists(os.path.join(proyecto_generado, '03-Backend', 'backend'))
    assert not os.path.exists(os.path.join(proyecto_generado, '03-Backend', 'servicio'))
    assert os.listdir(os.path.join(proyecto_generado, '04-Frontend')) == []
    assert 'node_modules' not in ' '.join(archivos(proyecto_generado))


@pytest.mark.skipif(_php() is None, reason='PHP no está instalado')
def test_todo_el_php_generado_tiene_sintaxis_valida(proyecto_generado):
    fallas = []
    for rel in archivos(proyecto_generado):
        if not rel.endswith('.php'):
            continue
        r = subprocess.run([_php(), '-l', os.path.join(proyecto_generado, rel)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            fallas.append(f'{rel}: {(r.stdout or r.stderr).strip()[:200]}')
    assert not fallas, fallas
