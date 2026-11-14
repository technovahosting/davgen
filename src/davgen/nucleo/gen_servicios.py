"""
gen_servicios.py — servicios JS del frontend React (carpeta 04-Front*).

Genera UN servicio por tabla en {04-Front*}/frontend/src/services/, siguiendo
el patrón de productoService.js: métodos listar/obtener/crear/actualizar/
desactivar (y reactivar si la tabla tiene columna `activo`) apuntando a los
endpoints POST del backend Laravel generado (v4.32.0: rutas por módulo):

    /{mod}/{recurso}/listar    → listado paginado sobre la vista vis_*
    /{mod}/{recurso}/obtener   → pcru*('R', pid)
    /{mod}/{recurso}/guardar   → pcru*('C', ...)
    /{mod}/{recurso}/actualizar → pcru*('U', ...)  ¡sobreescribe TODOS!
    /{mod}/{recurso}/eliminar  → pcru*('D', pid)  (baja lógica)

Los servicios importan { post, ahoraSql } de './api' (cliente HTTP que ya
existe en el proyecto React). No se tocan api.js, index.js ni los servicios
escritos a mano.
"""
import os
from typing import Dict, List, Optional

from .esquema import COLS_AUTO, a_clase
from .plantillas import cargar as _plantilla

_TIPOS_FECHA = {'date', 'datetime', 'timestamp', 'time'}
_TIPOS_NUM   = {'int', 'smallint', 'tinyint', 'mediumint', 'bigint', 'year',
                'decimal', 'float', 'double'}
_TIPOS_TEXTO = {'varchar', 'char', 'text', 'tinytext', 'mediumtext', 'longtext'}


def _camel(snake: str) -> str:
    partes = [p for p in snake.split('_') if p]
    return partes[0] + ''.join(p.title() for p in partes[1:])


def _mod_rec(tabla: str) -> tuple:
    """Extrae (modulo, recurso) de tbl_{mod}_{entity}; fallback ('gen', tabla)."""
    if tabla.startswith('tbl_'):
        resto = tabla[4:]
        idx = resto.find('_')
        if idx > 0:
            return resto[:idx], resto[idx + 1:]
    return 'gen', tabla


def _cols_parametro(columnas: List[Dict]) -> List[Dict]:
    """Columnas que son parámetro del SP (excluye created_at/updated_at)."""
    return [c for c in columnas if c['COLUMN_NAME'].lower() not in COLS_AUTO]


def _linea_parametro(c: Dict, pk: str) -> str:
    """Una línea de aParametros(): 'p{col}: <expresión JS>,'."""
    nombre = c['COLUMN_NAME']
    dt = c['DATA_TYPE'].lower()
    if nombre == pk:
        return f"    p{nombre}: registro.{nombre} ?? 0,"
    if dt in _TIPOS_FECHA:
        if 'actualizado' in nombre.lower() or 'updated' in nombre.lower():
            return f"    p{nombre}: ahoraSql(),"
        if c.get('IS_NULLABLE') == 'YES':
            return f"    p{nombre}: registro.{nombre} ?? null,"
        return f"    p{nombre}: registro.{nombre} ?? ahoraSql(),"
    if nombre.lower() == 'activo':
        return f"    p{nombre}: registro.{nombre} ? 1 : 0,"
    if dt in _TIPOS_NUM:
        return f"    p{nombre}: Number(registro.{nombre} ?? 0),"
    return f"    p{nombre}: registro.{nombre} ?? '',"


def _columna_busqueda(columnas: List[Dict], pk: str) -> str:
    """Primera columna de texto (no PK) — usada por listar() para el LIKE."""
    for c in columnas:
        if c['COLUMN_NAME'] != pk and c['DATA_TYPE'].lower() in _TIPOS_TEXTO:
            return c['COLUMN_NAME']
    return ''


def _servicio_js(t: Dict, autor: str) -> str:
    tabla        = t['tabla']
    camel        = _camel(t['entidad'])
    servicio     = f"{camel}Service"
    cn           = a_clase(tabla)
    columnas     = t['columnas']
    pk           = next((c['COLUMN_NAME'] for c in columnas
                         if c['COLUMN_KEY'] == 'PRI'), 'id')
    params       = _cols_parametro(columnas)
    tiene_activo = any(c['COLUMN_NAME'].lower() == 'activo' for c in columnas)
    col_busqueda = _columna_busqueda(columnas, pk)

    # Ruta modular: /{mod}/{recurso-kebab} (v4.32.0)
    mod, rec  = _mod_rec(tabla)
    ruta_base = f'/{mod}/{rec.replace("_", "-")}'

    lineas_parametros = '\n'.join(_linea_parametro(c, pk) for c in params)

    if col_busqueda:
        cuerpo_listar = f"""\
    const filters = []
    const texto = String(busqueda ?? '').trim()
    if (texto) filters.push({{ field: '{col_busqueda}', operator: 'like', value: texto }})
    const {{ info }} = await post(`${{RUTA}}/listar`, {{ page: pagina, per_page: porPagina, filters }})
    return {{ items: info.item ?? [], paginacion: info.pagination }}"""
        firma_listar = "async listar(busqueda = '', pagina = 1, porPagina = 25)"
        doc_listar   = f"/** Lista paginada; busqueda aplica LIKE sobre `{col_busqueda}`. */"
    else:
        cuerpo_listar = """\
    const { info } = await post(`${RUTA}/listar`, { page: pagina, per_page: porPagina, filters })
    return { items: info.item ?? [], paginacion: info.pagination }"""
        firma_listar = "async listar(pagina = 1, porPagina = 25, filters = [])"
        doc_listar   = "/** Lista paginada (filters: [{field,operator,value}]). */"

    extra_reactivar = ''
    if tiene_activo:
        extra_reactivar = """

  /** Reactivación: actualizar con el registro completo y activo = 1. */
  reactivar(registro) {
    return this.actualizar({ ...registro, activo: 1 })
  },"""

    nota_del = ('Baja lógica (activo = 0).' if tiene_activo
                else 'Eliminación vía SP (modo D).')
    linea_autor = f"// @author {autor}\n" if autor else ''

    return f"""\
// {servicio}.js — GENERADO por davgen (NO editar a mano: se regenera).
{linea_autor}// Servicio de {t['entidad']} contra la API davgen.
// Endpoints (todos POST, token Bearer, módulo {mod}):
//   {ruta_base}/listar    -> listado paginado sobre {t['vista']}
//                            {{ page, per_page, filters:[{{field,operator,value}}] }}
//   {ruta_base}/obtener   -> pcru{cn}('R', p{pk})   (solo activos)
//   {ruta_base}/guardar   -> pcru{cn}('C', ...)
//   {ruta_base}/actualizar -> pcru{cn}('U', ...)   ¡SOBREESCRIBE TODO!
//   {ruta_base}/eliminar  -> pcru{cn}('D', p{pk})   (baja lógica)
//
// IMPORTANTE: el 'U' de pcru* actualiza TODOS los campos con lo que llega.
// Por eso actualizar() exige el registro COMPLETO: enviar solo lo
// cambiado borraría el resto.
import {{ post, ahoraSql }} from './api'

const RUTA = '{ruta_base}'

function aParametros(registro) {{
  return {{
{lineas_parametros}
  }}
}}

export const {servicio} = {{
  {doc_listar}
  {firma_listar} {{
{cuerpo_listar}
  }},

  /** Lee por {pk} (el procedimiento solo devuelve activos). */
  async obtener(id) {{
    const {{ info }} = await post(`${{RUTA}}/obtener`, {{ p{pk}: id }})
    return info.item?.[0] ?? null
  }},

  /** Alta: p{pk}=0 -> el procedimiento asigna el siguiente {pk}. */
  async crear(registro) {{
    const {{ info }} = await post(`${{RUTA}}/guardar`, aParametros({{ ...registro, {pk}: 0 }}))
    return info.item?.[0] ?? null
  }},

  /** Modificación: requiere el registro COMPLETO (ver nota de cabecera). */
  async actualizar(registro) {{
    const {{ info }} = await post(`${{RUTA}}/actualizar`, aParametros(registro))
    return info.item?.[0] ?? null
  }},

  /** {nota_del} */
  async desactivar(id) {{
    const {{ info }} = await post(`${{RUTA}}/eliminar`, {{ p{pk}: id }})
    return info.item?.[0] ?? null
  }},{extra_reactivar}
}}
"""


def generar_servicios(tablas: List[Dict], cfg: Dict, carpeta: str) -> List[str]:
    """Escribe {entidad}Service.js por tabla en `carpeta`. Devuelve las rutas."""
    os.makedirs(carpeta, exist_ok=True)
    rutas = []
    for t in tablas:
        nombre = f"{_camel(t['entidad'])}Service.js"
        ruta = os.path.join(carpeta, nombre)
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(_servicio_js(t, cfg.get('autor', '')))
        rutas.append(ruta)
    return rutas


# ═════════════════════════════════════════════
#  Base del frontend: api.js + authService.js (solo si NO existen)
# ═════════════════════════════════════════════
_API_JS = _plantilla('frontend/api.js', __name__, '_API_JS')

_AUTH_SERVICE_JS = _plantilla('frontend/auth_service.js', __name__, '_AUTH_SERVICE_JS')


_APP_JSX = _plantilla('frontend/app.jsx', __name__, '_APP_JSX')


def generar_base_frontend(carpeta: str) -> List[str]:
    """Crea api.js y authService.js SOLO si no existen (no pisa lo manual)."""
    os.makedirs(carpeta, exist_ok=True)
    creados = []
    for nombre, contenido in (('api.js', _API_JS),
                              ('authService.js', _AUTH_SERVICE_JS)):
        ruta = os.path.join(carpeta, nombre)
        if not os.path.isfile(ruta):
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(contenido)
            creados.append(ruta)
    return creados


def ajustar_index_html(carpeta_front: str, nombre: str = '') -> bool:
    """Deja el index.html del proyecto React con el idioma de la interfaz y un
    título de verdad. La plantilla de Vite trae `lang="en"` y el título
    «frontend»: un lector de pantalla pronuncia el español con voz inglesa y
    la pestaña no dice qué sistema es. Solo cambia esos valores de fábrica: si
    el usuario ya puso los suyos, no se tocan. Devuelve True si escribió."""
    import html
    import re
    ruta = os.path.join(carpeta_front, 'index.html')
    try:
        with open(ruta, encoding='utf-8') as f:
            original = f.read()
    except OSError:
        return False
    nuevo = re.sub(r'<html\s+lang="en"', '<html lang="es"', original, count=1)
    if nombre.strip():
        nuevo = re.sub(r'<title>\s*(frontend|Vite \+ React)\s*</title>',
                       lambda _m: f'<title>{html.escape(nombre.strip())}</title>',
                       nuevo, count=1)
    if nuevo == original:
        return False
    with open(ruta, 'w', encoding='utf-8', newline='') as f:
        f.write(nuevo)
    return True


def generar_app_jsx(src_dir: str, nombre: str = '') -> Optional[str]:
    """Crea App.jsx en src_dir con pantalla de login, SOLO si no existe.
    No se incluye en el manifiesto de integridad porque es personalizable.
    `nombre` es el nombre visible del sistema ([proyecto] nombre)."""
    ruta = os.path.join(src_dir, 'App.jsx')
    if os.path.isfile(ruta):
        return None
    # El nombre va tanto en texto JSX como dentro de una cadena JS: se quitan
    # los caracteres que romperían cualquiera de los dos.
    limpio = ''.join(c for c in (nombre or 'Sistema') if c not in '{}<>\'"`\\').strip()
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(_APP_JSX.replace('__NOMBRE__', limpio or 'Sistema'))
    return ruta


# ═════════════════════════════════════════════
#  Páginas CRUD (pages/generados) + rutas.jsx
# ═════════════════════════════════════════════
def _titulo(snake: str) -> str:
    return ' '.join(p.capitalize() for p in snake.split('_') if p)


def _clase_pagina(entidad: str) -> str:
    return ''.join(p.title() for p in entidad.split('_') if p)


def _tipo_input(c: Dict) -> tuple:
    """(tipo de <input>|'select'|'textarea', step) para una columna editable."""
    import re as _re
    dt = c['DATA_TYPE'].lower()
    nombre = c['COLUMN_NAME'].lower()
    if dt in ('decimal', 'float', 'double'):
        return 'number', '0.01'
    if dt in _TIPOS_NUM:
        return 'number', '1'
    if dt == 'date':
        return 'date', ''
    if dt in ('datetime', 'timestamp'):
        return 'datetime-local', ''
    if dt == 'time':
        return 'time', ''
    if dt == 'enum':
        return 'select', ''
    if dt in ('text', 'longtext', 'mediumtext', 'tinytext'):
        return 'textarea', ''
    if _re.search(r'(email|correo|mail)$', nombre):
        return 'email', ''
    if _re.search(r'(telefono|celular|phone|whatsapp|tel)$', nombre):
        return 'tel', ''
    return 'text', ''


def _es_fecha_auto(nombre: str) -> bool:
    n = nombre.lower()
    return any(p in n for p in ('creado', 'actualizado', 'created', 'updated'))


def _campos_editables(columnas: List[Dict], pk: str) -> List[Dict]:
    """Columnas que el usuario llena en el formulario: excluye PK, activo,
    fechas automáticas y created_at/updated_at."""
    return [c for c in columnas
            if c['COLUMN_NAME'] != pk
            and c['COLUMN_NAME'].lower() not in COLS_AUTO
            and c['COLUMN_NAME'].lower() != 'activo'
            and not (c['DATA_TYPE'].lower() in _TIPOS_FECHA
                     and _es_fecha_auto(c['COLUMN_NAME']))]


_PAGINA = _plantilla('frontend/pagina.jsx', __name__, '_PAGINA')


_PAGINA_CONSULTA = _plantilla('frontend/pagina_consulta.jsx', __name__, '_PAGINA_CONSULTA')

_FUNC_BAJA = _plantilla('frontend/func_baja.jsx', __name__, '_FUNC_BAJA')

_FUNC_REACTIVAR = _plantilla('frontend/func_reactivar.jsx', __name__, '_FUNC_REACTIVAR')

_BTN_REACTIVAR = """
                          {!r.activo && (
                            <button className="btn btn-ghost btn-sm join-item text-success" onClick={() => reactivar(r)}>
                              Reactivar
                            </button>
                          )}"""

_BTN_BAJA = """
                          <button className="btn btn-ghost btn-sm join-item text-error" onClick={() => setABaja(r)}>
                            Dar de baja
                          </button>"""

_BTNS_ACTIVO_Y_BAJA = _plantilla('frontend/btns_activo_y_baja.jsx', __name__, '_BTNS_ACTIVO_Y_BAJA')

_MODAL_BAJA = _plantilla('frontend/modal_baja.jsx', __name__, '_MODAL_BAJA')


def _pagina_jsx(t: Dict, cfg: Dict) -> str:
    columnas = t['columnas']
    pk = next((c['COLUMN_NAME'] for c in columnas if c['COLUMN_KEY'] == 'PRI'), 'id')
    srv = f"{_camel(t['entidad'])}Service"
    clase = _clase_pagina(t['entidad'])
    tiene_activo = any(c['COLUMN_NAME'].lower() == 'activo' for c in columnas)
    con_busqueda = bool(_columna_busqueda(columnas, pk))

    # tabla de SOLO CONSULTA: página sin alta/edición/baja (el dominio escribe)
    if t['tabla'].lower() in cfg.get('solo_consulta', set()):
        lineas_columnas = [f"  {{ campo: '{pk}', etiqueta: '{_titulo(pk)}' }},"]
        for c in _campos_editables(columnas, pk):
            nombre = c['COLUMN_NAME']
            if nombre.lower().endswith('_id'):
                base = nombre[:-3]
                lineas_columnas.append(
                    f"  {{ campo: '{nombre}', alterno: '{base}', "
                    f"etiqueta: '{_titulo(base)}' }},")
            else:
                lineas_columnas.append(
                    f"  {{ campo: '{nombre}', etiqueta: '{_titulo(nombre)}' }},")
        return (_PAGINA_CONSULTA
                .replace('__CLASE__', clase)
                .replace('__TABLA__', t['tabla'])
                .replace('__SRV__', srv)
                .replace('__TITULO__', _titulo(t['entidad']))
                .replace('__PK__', pk)
                .replace('__CON_BUSQUEDA__', 'true' if con_busqueda else 'false')
                .replace('__COLUMNAS__', '\n'.join(lineas_columnas)))

    # acciones/campos configurables por tabla en [opciones] de la config
    con_baja = t['tabla'].lower() not in cfg.get('sin_baja', set())
    solo_lectura = {c.lower()
                    for c in cfg.get('solo_lectura', {}).get(t['tabla'].lower(), [])}
    editables = [c for c in _campos_editables(columnas, pk)
                 if c['COLUMN_NAME'].lower() not in solo_lectura]

    con_componentes = bool(cfg.get('generar', {}).get('componentes_react'))

    lineas_campos = []
    lineas_inicial = []
    importaciones_relacion = []   # (base_name, service_name) para imports JS
    for c in editables:
        nombre = c['COLUMN_NAME']
        tipo, paso = _tipo_input(c)
        requerido = 'true' if c.get('IS_NULLABLE') != 'YES' and tipo not in (
            'number', 'select') else 'false'

        # FK *_id + componentes_react=si → SelectRelacion en lugar de input number.
        # Solo si es FK de negocio REAL (c['FK'] = entidad destino con service);
        # FK a tbl_seg_* o *_id polimórfico (sin FK) → input numérico (else).
        if (con_componentes and nombre.lower().endswith('_id') and tipo == 'number'
                and c.get('FK')):
            base = c['FK']                       # entidad destino real (tec_cliente)
            srv_name = f"{_camel(base)}Service"  # -> tecClienteService
            importaciones_relacion.append((base, srv_name))
            lineas_campos.append(
                f"  {{ campo: '{nombre}', etiqueta: '{_titulo(base)}', "
                f"tipo: 'select_relacion', servicio: {srv_name}, requerido: {requerido} }},")
            lineas_inicial.append(f"{nombre}: 0")
        else:
            paso_js = f", paso: '{paso}'" if paso else ''
            opciones_js = ''
            if tipo == 'select' and c.get('ENUM_VALS'):
                vals = ', '.join(f"'{v}'" for v in c['ENUM_VALS'])
                opciones_js = f", opciones: [{vals}]"
            lineas_campos.append(
                f"  {{ campo: '{nombre}', etiqueta: '{_titulo(nombre)}', "
                f"tipo: '{tipo}'{paso_js}{opciones_js}, requerido: {requerido} }},")
            lineas_inicial.append(f"{nombre}: " + ("0" if tipo == 'number' else "''"))
    if tiene_activo:
        lineas_inicial.append('activo: 1')

    # Imports JS para SelectRelacion y los servicios de las FK relacionadas
    if importaciones_relacion:
        vistos: set = set()
        import_lines = ["import SelectRelacion from '../../components/generados/SelectRelacion'"]
        for _base, srv_name in importaciones_relacion:
            if srv_name not in vistos:
                vistos.add(srv_name)
                import_lines.append(
                    f"import {{ {srv_name} }} from '../../services/{srv_name}'")
        import_relaciones = '\n' + '\n'.join(import_lines)
    else:
        import_relaciones = ''

    # listado: PK + campos de negocio (incluye los de solo lectura); para las
    # FK x_id se prefiere la columna legible `x` si la vista la entrega
    lineas_columnas = [f"  {{ campo: '{pk}', etiqueta: '{_titulo(pk)}' }},"]
    for c in _campos_editables(columnas, pk):
        nombre = c['COLUMN_NAME']
        if nombre.lower().endswith('_id'):
            base = nombre[:-3]
            lineas_columnas.append(
                f"  {{ campo: '{nombre}', alterno: '{base}', "
                f"etiqueta: '{_titulo(base)}' }},")
        else:
            lineas_columnas.append(
                f"  {{ campo: '{nombre}', etiqueta: '{_titulo(nombre)}' }},")

    if tiene_activo and con_baja:
        botones = _BTNS_ACTIVO_Y_BAJA
    elif tiene_activo:
        botones = _BTN_REACTIVAR
    elif con_baja:
        botones = _BTN_BAJA
    else:
        botones = ''

    funciones = (_FUNC_BAJA if con_baja else '') + \
                (_FUNC_REACTIVAR if tiene_activo else '')
    estado_baja = ("  const [aBaja, setABaja] = useState(null)\n"
                   if con_baja else '')

    return (_PAGINA
            .replace('__CLASE__', clase)
            .replace('__TABLA__', t['tabla'])
            .replace('__SRV__', srv)
            .replace('__TITULO__', _titulo(t['entidad']))
            .replace('__PK__', pk)
            .replace('__TIENE_ACTIVO__', 'true' if tiene_activo else 'false')
            .replace('__CON_BUSQUEDA__', 'true' if con_busqueda else 'false')
            .replace('__CAMPOS__', '\n'.join(lineas_campos))
            .replace('__COLUMNAS__', '\n'.join(lineas_columnas))
            .replace('__VALOR_INICIAL__', ', '.join(lineas_inicial))
            .replace('__ESTADO_BAJA__', estado_baja)
            .replace('__FUNCIONES_EXTRA__', funciones)
            .replace('__BOTONES_EXTRA__', botones)
            .replace('__MODAL_BAJA__', _MODAL_BAJA if con_baja else '')
            .replace('__IMPORT_RELACIONES__', import_relaciones))


def _rutas_jsx(tablas: List[Dict]) -> str:
    importaciones, secciones, paginas = [], [], []
    modulos: dict = {}  # { mod: [(clave, etiqueta)] }
    for t in tablas:
        clase = _clase_pagina(t['entidad'])
        importaciones.append(f"import {clase}Page from './{clase}Page'")
        secciones.append(f"  {{ clave: '{t['entidad']}', "
                         f"etiqueta: '{_titulo(t['entidad'])}' }},")
        paginas.append(f"  {t['entidad']}: {clase}Page,")
        # extraer módulo de la tabla: tbl_zap_order → 'zap'
        tbl = t['tabla']
        if tbl.startswith('tbl_') and '_' in tbl[4:]:
            mod = tbl[4:4 + tbl[4:].index('_')]
        else:
            mod = 'gen'
        modulos.setdefault(mod, []).append((t['entidad'], _titulo(t['entidad'])))

    mod_entries = []
    for mod, secs in modulos.items():
        secs_js = ', '.join(
            f"{{ clave: '{c}', etiqueta: '{e}' }}" for c, e in secs
        )
        mod_entries.append(
            f"  {mod}: {{ etiqueta: '{mod.capitalize()}', secciones: [{secs_js}] }},"
        )
    nl = '\n'
    return f"""\
// rutas.jsx — GENERADO por davgen (NO editar a mano: se regenera).
// Arquitectura: un solo proyecto React, navegación agrupada por módulo.
// App.jsx consume MODULOS_GENERADOS para armar el sidebar dinámico.
// PAGINAS_GENERADAS es el mapa clave→componente para renderizar la página activa.
{nl.join(importaciones)}

// Módulos agrupados: cada módulo tiene etiqueta y lista de secciones.
// App.jsx itera sobre esto para construir el sidebar.
export const MODULOS_GENERADOS = {{
{nl.join(mod_entries)}
}}

// Compat: lista plana de secciones (para navegación sin sidebar)
export const SECCIONES_GENERADAS = [
{nl.join(secciones)}
]

// Mapa clave → componente
export const PAGINAS_GENERADAS = {{
{nl.join(paginas)}
}}
"""


def generar_paginas(tablas: List[Dict], cfg: Dict, carpeta: str) -> List[str]:
    """Escribe pages/generados/{Clase}Page.jsx por tabla + rutas.jsx opcional."""
    os.makedirs(carpeta, exist_ok=True)
    rutas = []
    for t in tablas:
        ruta = os.path.join(carpeta, f"{_clase_pagina(t['entidad'])}Page.jsx")
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(_pagina_jsx(t, cfg))
        rutas.append(ruta)
    ruta_rutas = os.path.join(carpeta, 'rutas.jsx')
    with open(ruta_rutas, 'w', encoding='utf-8') as f:
        f.write(_rutas_jsx(tablas))
    rutas.append(ruta_rutas)
    return rutas


# ═════════════════════════════════════════════
#  Setup Tailwind + DaisyUI  y  Capacitor (APK)
# ═════════════════════════════════════════════

_VITE_CONFIG_TAILWIND = _plantilla('frontend/vite_config_tailwind.js', __name__, '_VITE_CONFIG_TAILWIND')

_INDEX_CSS_TAILWIND = _plantilla('frontend/index_tailwind.css', __name__, '_INDEX_CSS_TAILWIND')

_CAPACITOR_CONFIG = _plantilla('frontend/capacitor_config.json', __name__, '_CAPACITOR_CONFIG')


def configurar_tailwind_daisyui(front_dir: str) -> bool:
    """Instala Tailwind CSS v4 + DaisyUI y actualiza vite.config.js / index.css
    SOLO si el proyecto aún no los tiene. Devuelve True si se realizó la
    instalación, False si ya estaba configurado."""
    import subprocess
    pkg_json = os.path.join(front_dir, 'package.json')
    if not os.path.isfile(pkg_json):
        return False
    try:
        with open(pkg_json, encoding='utf-8') as f:
            pkg = __import__('json').load(f)
    except Exception:
        return False
    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
    if 'tailwindcss' in deps:
        return False  # ya configurado

    subprocess.run(
        ['npm', 'install', '-D', 'tailwindcss', '@tailwindcss/vite', 'daisyui@latest'],
        cwd=front_dir, check=False,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        shell=True,
    )

    vite_cfg = os.path.join(front_dir, 'vite.config.js')
    with open(vite_cfg, 'w', encoding='utf-8') as f:
        f.write(_VITE_CONFIG_TAILWIND)

    css = os.path.join(front_dir, 'src', 'index.css')
    with open(css, 'w', encoding='utf-8') as f:
        f.write(_INDEX_CSS_TAILWIND)

    return True


def configurar_capacitor(front_dir: str, nombre: str, app_id: str = '') -> bool:
    """Crea capacitor.config.json en front_dir SOLO si no existe.
    Añade base './' a vite.config.js si aún no está.
    Devuelve True si se creó el archivo, False si ya existía."""
    cap_cfg = os.path.join(front_dir, 'capacitor.config.json')
    if not os.path.isfile(cap_cfg):
        nombre_limpio = nombre or 'App'
        slug = ''.join(c for c in nombre_limpio.lower() if c.isalnum())
        id_final = app_id or f'com.davgen.{slug}'
        with open(cap_cfg, 'w', encoding='utf-8') as f:
            f.write(_CAPACITOR_CONFIG.format(app_id=id_final, nombre=nombre_limpio))

    # asegurar base: './' en vite.config.js (necesario para Capacitor)
    vite_cfg = os.path.join(front_dir, 'vite.config.js')
    if os.path.isfile(vite_cfg):
        with open(vite_cfg, encoding='utf-8') as f:
            contenido = f.read()
        if "base: './'," not in contenido and 'base: "./",' not in contenido:
            contenido = contenido.replace(
                'export default defineConfig({',
                "export default defineConfig({\n  base: './',",
            )
            with open(vite_cfg, 'w', encoding='utf-8') as f:
                f.write(contenido)

    return not os.path.isfile(cap_cfg)
