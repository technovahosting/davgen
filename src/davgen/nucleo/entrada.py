"""
entrada.py — FASE de entrada: mockup (HTML / carpeta React) o BD existente.

Ambos caminos devuelven el mismo formato de entidades crudas que consume
esquema.construir_tablas() (camino mockup) o directamente la lista de
tablas normalizadas (camino bd):

    mockup → [{'nombre','origen','campos':[{nombre,tipo_html,tipo_ts,opciones}]}]
    bd     → [{'entidad','tabla','vista','origen','columnas':[col,...]}]

el controlador de MySQL (ver bd.py) se importa de forma diferida: el camino mockup funciona
sin él instalado.
"""
import base64
import gzip
import json
import os
import re
from html.parser import HTMLParser
from typing import Dict, List, Optional

from .consola import warn, info, dim
from .esquema import a_snake_case, col, nombre_entidad, singularizar

_INPUTS_IGNORAR  = {'submit', 'button', 'reset', 'image', 'file', 'hidden',
                    'search', 'range', 'color'}
_NOMBRES_IGNORAR = {'buscar', 'busqueda', 'search', 'filtro', 'filter', 'q', ''}


# ═════════════════════════════════════════════
#  Camino A · mockup HTML autocontenido
# ═════════════════════════════════════════════
class _ParserMockup(HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titulo_actual = ''
        self._titulo_nivel = 0   # nivel del heading que fijó titulo_actual (1/2/3)
        self._cap = {'titulo': False, 'th': False, 'option': False}
        self._buf = {'titulo': [], 'th': [], 'option': []}
        self.grupos: Dict[str, Dict] = {}
        self.tablas_html: List[Dict] = []
        self._en_tabla: Optional[Dict] = None
        self._select_actual: Optional[Dict] = None

    @staticmethod
    def _attr(attrs, clave):
        for k, v in attrs:
            if k == clave:
                return v or ''
        return ''

    def _nombre_campo(self, attrs) -> str:
        crudo = self._attr(attrs, 'name') or self._attr(attrs, 'id')
        if not crudo:
            return ''
        if '-' in crudo:
            crudo = crudo.split('-', 1)[1]
        return a_snake_case(crudo)

    def _clave_grupo(self, attrs) -> str:
        if self.titulo_actual:
            return f"t:{self.titulo_actual}"
        crudo = self._attr(attrs, 'id')
        return f"p:{crudo.split('-', 1)[0]}" if '-' in crudo else 'p:general'

    def _registrar(self, attrs, tipo_html, opciones=None):
        nombre = self._nombre_campo(attrs)
        if nombre in _NOMBRES_IGNORAR:
            return None
        grupo = self.grupos.setdefault(
            self._clave_grupo(attrs), {'titulo': self.titulo_actual, 'campos': []})
        campo = {'nombre': nombre, 'tipo_html': tipo_html,
                 'tipo_ts': '', 'opciones': opciones or []}
        grupo['campos'].append(campo)
        return campo

    def handle_starttag(self, tag, attrs):
        if tag in ('h1', 'h2', 'h3'):
            self._cap['titulo'], self._buf['titulo'] = True, []
        elif tag == 'table':
            self._en_tabla = {'titulo': self.titulo_actual,
                              'nivel': self._titulo_nivel, 'columnas': []}
        elif tag == 'th' and self._en_tabla is not None:
            self._cap['th'], self._buf['th'] = True, []
        elif tag == 'input':
            tipo = (self._attr(attrs, 'type') or 'text').lower()
            if tipo not in _INPUTS_IGNORAR:
                self._registrar(attrs, tipo)
        elif tag == 'textarea':
            self._registrar(attrs, 'textarea')
        elif tag == 'select':
            self._select_actual = self._registrar(attrs, 'select')
        elif tag == 'option' and self._select_actual is not None:
            self._cap['option'], self._buf['option'] = True, []

    def handle_endtag(self, tag):
        if tag in ('h1', 'h2', 'h3'):
            self._cap['titulo'] = False
            texto = ' '.join(''.join(self._buf['titulo']).split())
            if texto:
                self.titulo_actual = texto
                self._titulo_nivel = int(tag[1])  # h1→1, h2→2, h3→3
        elif tag == 'table':
            if self._en_tabla and len(self._en_tabla['columnas']) >= 2:
                self.tablas_html.append(self._en_tabla)
            self._en_tabla = None
        elif tag == 'th':
            if self._cap['th'] and self._en_tabla is not None:
                columna = a_snake_case(' '.join(''.join(self._buf['th']).split()))
                if columna and columna not in _NOMBRES_IGNORAR:
                    self._en_tabla['columnas'].append(columna)
            self._cap['th'] = False
        elif tag == 'select':
            self._select_actual = None
        elif tag == 'option':
            if self._cap['option'] and self._select_actual is not None:
                val = a_snake_case(' '.join(''.join(self._buf['option']).split()))
                if val and not val.startswith('seleccion'):
                    self._select_actual['opciones'].append(val)
            self._cap['option'] = False

    def handle_data(self, data):
        for clave in ('titulo', 'th', 'option'):
            if self._cap[clave]:
                self._buf[clave].append(data)


def _analizar_html(texto: str) -> List[Dict]:
    parser = _ParserMockup()
    parser.feed(texto)
    entidades: Dict[str, Dict] = {}

    for grupo in parser.grupos.values():           # formularios: mejor señal
        if len(grupo['campos']) < 2:
            continue
        nombre = nombre_entidad(grupo['titulo']) if grupo['titulo'] else ''
        if not nombre:
            continue
        ent = entidades.setdefault(nombre, {
            'nombre': nombre, 'origen': f"formulario «{grupo['titulo']}»", 'campos': []})
        ya = {c['nombre'] for c in ent['campos']}
        ent['campos'].extend(c for c in grupo['campos'] if c['nombre'] not in ya)

    _COLS_TH_IGNORAR = {'accion', 'acciones', 'opcion', 'opciones', 'estado',
                         'activo', 'activa', 'imagen', 'foto', 'avatar'}
    for tabla in parser.tablas_html:               # tablas: complementan a los formularios
        nombre = nombre_entidad(tabla['titulo']) if tabla['titulo'] else ''
        if not nombre:
            continue
        ya_tiene_form = nombre in entidades
        # B4: <h3>+tabla solo enriquece entidades ya creadas por un form;
        # un h1/h2 sí puede crear una nueva entidad desde la tabla.
        if tabla.get('nivel', 0) > 2 and not ya_tiene_form:
            continue
        ent = entidades.setdefault(nombre, {
            'nombre': nombre, 'origen': f"tabla «{tabla['titulo']}»", 'campos': []})
        # B3: si la entidad ya tiene campos de un formulario, los encabezados
        # de <th> son etiquetas de pantalla (no nombres de campo) — no agregar.
        if ya_tiene_form:
            continue
        ya = {c['nombre'] for c in ent['campos']}
        for columna in tabla['columnas']:
            columna = singularizar(columna)
            if columna not in ya and columna not in _COLS_TH_IGNORAR:
                ent['campos'].append({'nombre': columna, 'tipo_html': '',
                                      'tipo_ts': '', 'opciones': []})
                ya.add(columna)

    return [e for e in entidades.values() if len(e['campos']) >= 2]


# ═════════════════════════════════════════════
#  Camino A · interfaces TypeScript (mockup React)
# ═════════════════════════════════════════════
_RE_INTERFACE = re.compile(r'export\s+interface\s+(\w+)\s*\{([^}]*)\}', re.DOTALL)
_RE_CAMPO_TS  = re.compile(r'^\s*(\w+)\??\s*:\s*([^;\n]+);?\s*$', re.MULTILINE)
_RE_UNION     = re.compile(r"^\s*'[^']*'(\s*\|\s*'[^']*')+\s*$")
_IFACES_UI    = {'props', 'state', 'cartitem', 'carrito', 'context'}


def _analizar_typescript(texto: str, origen: str) -> List[Dict]:
    entidades = []
    for m in _RE_INTERFACE.finditer(texto):
        nombre_iface, cuerpo = m.group(1), m.group(2)
        if nombre_iface.lower() in _IFACES_UI:
            continue
        campos = []
        for cm in _RE_CAMPO_TS.finditer(cuerpo):
            nombre, tipo = a_snake_case(cm.group(1)), cm.group(2).strip()
            if nombre == 'id':
                continue
            if _RE_UNION.match(tipo):
                campos.append({'nombre': nombre, 'tipo_html': '', 'tipo_ts': 'string',
                               'opciones': re.findall(r"'([^']*)'", tipo)})
            elif tipo.endswith('[]') or (tipo[0].isupper()
                                         and tipo not in ('Date', 'String', 'Number', 'Boolean')):
                continue   # relación / objeto anidado, no columna
            else:
                campos.append({'nombre': nombre, 'tipo_html': '', 'tipo_ts': tipo,
                               'opciones': []})
        if len(campos) >= 2:
            entidades.append({'nombre': nombre_entidad(nombre_iface),
                              'origen': f"interface {nombre_iface} ({origen})",
                              'campos': campos})
    return entidades


# ═════════════════════════════════════════════
#  Camino C · bundle Bolt.new / Design Canvas
# ═════════════════════════════════════════════

# Claves de objetos JS que son puramente UI, no campos de negocio
_CLAVES_UI_JS = frozenset({
    'id', 'key', 'icon', 'tone', 'cls', 'label', 'value', 'delta',
    'deltapositive', 'helper', 'active', 'badge', 'hint', 'text', 'time',
    'highlight', 'count', 'pct', 'onclick', 'placeholder', 'title', 'alt',
    'class', 'style', 'type', 'src', 'href', 'target', 'rel', 'color',
    'size', 'width', 'height', 'loading', 'format', 'variant', 'cat',
    'deltanegative',
})

# Nombres de variable claramente de UI: se ignoran al buscar entidades
_VARS_BUNDLE_UI = frozenset({
    'kpis', 'activity', 'items', 'bottom', 'tabs', 'links', 'nav',
    'menu', 'buttons', 'badges', 'actions', 'filters', 'columns',
    'breadcrumbs', 'crumbs', 'steps', 'options', 'choices', 'map',
    # Design Canvas (x-dc): datos de gráficas / dropdowns dinámicos, no entidades
    'cats', 'weeklydata', 'topraw', 'weeklyDataRow', 'chartdata',
    'categories', 'blobUrls', 'uuids', 'chunks', 'rows',
})


def _es_bundle(texto: str) -> bool:
    """True si el HTML es un bundle de Bolt.new / Design Canvas."""
    return '__bundler/manifest' in texto and '__bundler/template' in texto


class _ColectorScripts(HTMLParser):
    """Extrae el contenido de <script type="__bundler/..."> del HTML."""

    def __init__(self):
        super().__init__()
        self.scripts: Dict[str, str] = {}
        self._cur: Optional[str] = None
        self._buf: list = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            t = dict(attrs).get('type', '')
            if '__bundler' in t:
                self._cur = t
                self._buf = []

    def handle_endtag(self, tag):
        if tag == 'script' and self._cur:
            self.scripts[self._cur] = ''.join(self._buf)
            self._cur = None

    def handle_data(self, data):
        if self._cur:
            self._buf.append(data)


def _descomprimir_asset(entry: dict) -> str:
    """Base64-decode + gzip-decompress (si aplica) → texto UTF-8."""
    data = base64.b64decode(entry['data'])
    if entry.get('compressed'):
        try:
            data = gzip.decompress(data)
        except Exception:
            pass
    return data.decode('utf-8', errors='replace')


def _primer_objeto_js(texto: str, inicio: int) -> Optional[str]:
    """Extrae el cuerpo del primer {…} a partir de inicio (que apunta a '{')."""
    if inicio >= len(texto) or texto[inicio] != '{':
        return None
    depth = 0
    start = inicio + 1
    for i in range(inicio, len(texto)):
        c = texto[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return texto[start:i]
    return None


_RE_CONST_ARRAY = re.compile(r'\bconst\s+([A-Za-z_]\w*)\s*=\s*\[')
# Propiedad de objeto (state/config): nombre: [{ — cubre datos de negocio
# en mockups de Design Canvas (x-dc) donde el estado no usa const.
_RE_PROP_ARRAY  = re.compile(r'(?<![.\w])([A-Za-z_]\w*)\s*:\s*\[\s*\{')
# Campos de objeto: inicio de línea O tras coma — cubre tanto objetos
# multilínea (Bolt.new clásico) como objetos de una sola línea (x-dc).
_RE_CAMPO_JS    = re.compile(r'(?:^|,)\s*([a-zA-Z_]\w*)\s*:', re.MULTILINE)


def _analizar_bundle_js(js_texto: str) -> List[Dict]:
    """
    Busca arrays de objetos literales en código JS con dos patrones:
        const NOMBRE = [{campo: valor, ...}, ...]
        propiedad: [{campo: valor, ...}, ...]   (Design Canvas / x-dc)
    y extrae las claves como campos de una entidad.
    Ignora variables de UI y objetos con menos de 3 campos de negocio.
    """
    entidades = []
    vistos_var: set = set()

    # Combina los dos patrones; ambos entregan (nombre, posición tras '[')
    candidatos = []
    for m in _RE_CONST_ARRAY.finditer(js_texto):
        candidatos.append((m.group(1), m.end()))
    for m in _RE_PROP_ARRAY.finditer(js_texto):
        # _RE_PROP_ARRAY ya incluye '{' en el patrón; retrocedemos al '{'
        candidatos.append((m.group(1), m.end() - 1))

    for var_name, pos_tras_bracket in candidatos:
        if var_name.lower() in _VARS_BUNDLE_UI:
            continue
        if var_name in vistos_var:
            continue

        # Avanzar hasta el primer { del array
        pos = pos_tras_bracket
        while pos < len(js_texto) and js_texto[pos] in ' \t\r\n':
            pos += 1
        if pos >= len(js_texto) or js_texto[pos] != '{':
            continue

        cuerpo = _primer_objeto_js(js_texto, pos)
        if not cuerpo:
            continue

        campos: List[Dict] = []
        visto: set = set()
        for cm in _RE_CAMPO_JS.finditer(cuerpo):
            nombre_raw = cm.group(1)
            nombre_norm = a_snake_case(nombre_raw)
            if nombre_raw.lower() in _CLAVES_UI_JS or nombre_norm in _CLAVES_UI_JS:
                continue
            if nombre_norm in visto or not nombre_norm or len(nombre_norm) <= 1:
                continue
            visto.add(nombre_norm)
            campos.append({'nombre': nombre_norm, 'tipo_html': '',
                           'tipo_ts': '', 'opciones': []})

        if len(campos) < 3:
            continue

        ent_nombre = nombre_entidad(var_name)
        if not ent_nombre:
            continue

        vistos_var.add(var_name)
        entidades.append({
            'nombre':  ent_nombre,
            'origen':  f"array JS «{var_name}»",
            'campos':  campos,
        })

    return entidades


def analizar_bundle(contenido: str) -> List[Dict]:
    """
    Bundle HTML de Bolt.new / Design Canvas → entidades crudas.
    Extrae el template HTML (labels/headings) y escanea los assets JS
    buscando arrays de objetos de negocio.
    """
    colector = _ColectorScripts()
    colector.feed(contenido)
    scripts = colector.scripts

    if '__bundler/manifest' not in scripts or '__bundler/template' not in scripts:
        return []

    try:
        manifest = json.loads(scripts['__bundler/manifest'])
        template = json.loads(scripts['__bundler/template'])
    except Exception:
        return []
    if not isinstance(manifest, dict):
        return []

    entidades: Dict[str, Dict] = {}

    def _merge(ent: dict) -> None:
        nombre = ent.get('nombre', '')
        if not nombre:
            return
        if nombre not in entidades:
            entidades[nombre] = ent
        else:
            ya = {c['nombre'] for c in entidades[nombre]['campos']}
            entidades[nombre]['campos'].extend(
                c for c in ent['campos'] if c['nombre'] not in ya)

    # 1. HTML del template → headings/labels + bloque x-dc con datos de negocio
    if isinstance(template, dict):
        # Formato antiguo: {pages: {...}, entry: "id"}
        pages    = template.get('pages', {})
        entry_id = template.get('entry')
        if entry_id and entry_id in pages:
            page_html = pages[entry_id]
            idx = page_html.find('</helmet>')
            contenido_dc = page_html[idx:] if idx >= 0 else page_html
            for ent in _analizar_html(contenido_dc):
                _merge(ent)
    elif isinstance(template, str):
        # Formato nuevo: template ES el HTML completo
        idx = template.find('</helmet>')
        contenido_dc = template[idx:] if idx >= 0 else template
        for ent in _analizar_html(contenido_dc):
            _merge(ent)
        # Bloque <script type="text/x-dc"> con datos de negocio (state = {...})
        dc_m = re.search(
            r'<script[^>]+type=["\']?text/x-dc["\']?[^>]*>(.*?)</script>',
            template, re.DOTALL | re.IGNORECASE)
        if dc_m:
            for ent in _analizar_bundle_js(dc_m.group(1)):
                _merge(ent)

    # 2. Assets JS del manifest → arrays de datos de negocio (formato antiguo)
    for entry in manifest.values():
        if 'javascript' not in entry.get('mime', ''):
            continue
        js_texto = _descomprimir_asset(entry)
        for ent in _analizar_bundle_js(js_texto):
            _merge(ent)

    return [e for e in entidades.values() if len(e['campos']) >= 2]


def _aviso_bundle_sin_entidades(ruta: str) -> None:
    """Muestra pasos a seguir cuando un bundle Design Canvas no produce entidades."""
    nombre = os.path.basename(ruta)
    warn(f"El bundle '{nombre}' usa variables de plantilla ({{ var }}) en vez de")
    warn("  formularios HTML convencionales — davgen no puede extraer entidades.")
    info("Para generar el sistema igualmente:")
    dim("  1. Abre el prompt '_prompts/prompt-2-tablas-desde-mockup.md' con una IA")
    dim("     pasando el contenido del mockup — la IA lista las tablas sugeridas.")
    dim("  2. Crea las tablas en MySQL con esos nombres (tbl_{mod}_{entidad}).")
    dim("  3. Cambia tipo=mockup a tipo=bd en _configtotal.ini y vuelve a generar.")
    dim("  4. El generador leerá el esquema real y creará el backend completo.")
    info("  Se continúa sin CRUD (solo seguridad y backbone del sistema).")


def analizar_mockup(ruta: str) -> List[Dict]:
    """Archivo .html o carpeta de mockup → entidades crudas deduplicadas."""
    entidades: List[Dict] = []

    if os.path.isfile(ruta):
        with open(ruta, encoding='utf-8', errors='replace') as f:
            contenido = f.read()
        if _es_bundle(contenido):
            resultado_bundle = analizar_bundle(contenido)
            entidades.extend(resultado_bundle)
            if not resultado_bundle:
                _aviso_bundle_sin_entidades(ruta)
        else:
            entidades.extend(_analizar_html(contenido))
    else:
        for base, _dirs, archivos in os.walk(ruta):
            if 'node_modules' in base:
                continue
            for nombre in archivos:
                completo = os.path.join(base, nombre)
                try:
                    with open(completo, encoding='utf-8', errors='replace') as f:
                        texto = f.read()
                except OSError:
                    continue
                if nombre.lower().endswith('.html'):
                    ent_html = (analizar_bundle(texto) if _es_bundle(texto)
                                else _analizar_html(texto))
                    entidades.extend(ent_html)
                elif nombre.lower().endswith(('.ts', '.tsx')) and \
                        ('components' + os.sep + 'ui') not in completo:
                    entidades.extend(_analizar_typescript(
                        texto, os.path.relpath(completo, ruta)))

    unicas: Dict[str, Dict] = {}
    for ent in entidades:
        if not ent['nombre']:
            continue
        if ent['nombre'] not in unicas:
            unicas[ent['nombre']] = ent
        else:
            ya = {c['nombre'] for c in unicas[ent['nombre']]['campos']}
            unicas[ent['nombre']]['campos'].extend(
                c for c in ent['campos'] if c['nombre'] not in ya)
    return list(unicas.values())


# ═════════════════════════════════════════════
#  Camino B · base de datos existente
# ═════════════════════════════════════════════
_TABLAS_LARAVEL = {
    'cache', 'cache_locks', 'failed_jobs', 'jobs', 'job_batches', 'migrations',
    'password_reset_tokens', 'personal_access_tokens', 'sessions', 'users',
}


def leer_bd(cfg_bd: Dict, incluir_seg: bool = False) -> List[Dict]:
    """Lee INFORMATION_SCHEMA y devuelve tablas normalizadas (formato pipeline).

    incluir_seg=True devuelve también tbl_seg_* (para generar pcru* completos).
    """
    from . import bd as _bd
    conn = _bd.conectar(cfg_bd, timeout=20)
    db = cfg_bd['database']
    cur = _bd.cursor_dict(conn)

    cur.execute("""
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME""", (db,))
    nombres = [r['TABLE_NAME'] for r in cur.fetchall()
               if r['TABLE_NAME'].lower() not in _TABLAS_LARAVEL
               # tablas de seguridad davgen: excluidas del negocio salvo que
               # se pida explícitamente (para generar SPs de todas las tablas)
               and (incluir_seg
                    or not r['TABLE_NAME'].lower().startswith('tbl_seg_'))]

    # Relaciones FOREIGN KEY reales: (tabla, columna) -> (tabla_ref, ON DELETE).
    # Necesarias para reconstruir las CONSTRAINT en 02_negocio.sql (G-15) y para
    # resolver el service correcto de las FK en el frontend (G-14).
    cur.execute("""
        SELECT kcu.TABLE_NAME, kcu.COLUMN_NAME,
               kcu.REFERENCED_TABLE_NAME, rc.DELETE_RULE
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
        JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.TABLE_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = %s
          AND kcu.REFERENCED_TABLE_NAME IS NOT NULL""", (db,))
    fk_map = {(r['TABLE_NAME'], r['COLUMN_NAME']):
              (r['REFERENCED_TABLE_NAME'], r['DELETE_RULE'])
              for r in cur.fetchall()}

    tablas = []
    for nombre in nombres:
        cur.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE,
                   COLUMN_KEY, EXTRA
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION""", (db, nombre))
        columnas = []
        for c in cur.fetchall():
            import re as _re
            # mysql-connector entrega algunas columnas como bytes: a str
            c = {k: (_bd.texto(v) if isinstance(v, (bytes, bytearray)) else v)
                 for k, v in c.items()}
            nulo = '' if c['IS_NULLABLE'] == 'YES' else ' NOT NULL'
            dt = c['DATA_TYPE'].lower()
            enum_vals = None
            if dt == 'enum':
                enum_vals = _re.findall(r"'([^']+)'", c['COLUMN_TYPE']) or None
                sql_full  = c['COLUMN_TYPE'] + nulo
            else:
                sql_full  = c['COLUMN_TYPE'].upper() + nulo
            col_dict = col(
                c['COLUMN_NAME'], dt, sql_full,
                nullable=c['IS_NULLABLE'] == 'YES',
                key=c['COLUMN_KEY'], extra=c['EXTRA'],
                enum_vals=enum_vals)
            ref = fk_map.get((nombre, c['COLUMN_NAME']))
            if ref:
                ref_tabla, on_delete = ref
                col_dict['FK_TABLA'] = ref_tabla       # tabla referenciada real
                col_dict['FK_ONDELETE'] = on_delete    # RESTRICT/CASCADE/SET NULL…
                # FK "de negocio" (entidad con service) solo si la tabla destino
                # es de negocio; seg_*/Laravel → FK=None (frontend usa input num.)
                rt = ref_tabla.lower()
                if (rt.startswith('tbl_') and not rt.startswith('tbl_seg_')
                        and rt not in _TABLAS_LARAVEL):
                    col_dict['FK'] = ref_tabla[4:]     # tbl_tec_cliente → tec_cliente
            columnas.append(col_dict)
        if not columnas:
            continue
        sin_prefijo = nombre[4:] if nombre.startswith('tbl_') else nombre
        tablas.append({
            'entidad':  sin_prefijo,
            'tabla':    nombre,
            'vista':    f"vis_{sin_prefijo}",
            'origen':   f"base de datos «{db}»",
            'columnas': columnas,
        })
    cur.close()
    conn.close()
    return tablas
