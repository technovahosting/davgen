"""
esquema.py — modelo de entidades y estándares SQL de davgen v4.0.

Normaliza las entidades crudas (de entrada.py) a definiciones de tabla:
  - tbl_{modulo}_{entidad} en singular · columnas obligatorias
    (id, activo, created_at, updated_at) · tipos por nombre/input/TS
  - ENUM cuando el mockup declara los valores (prioridad máxima)
  - FKs por sufijo _id o selects que apuntan a otra entidad
  - orden de creación según dependencias FK

Formato de columna (dict):
  COLUMN_NAME, DATA_TYPE, IS_NULLABLE ('YES'/'NO'), COLUMN_KEY ('PRI'/''),
  EXTRA ('auto_increment'/''), SQL_FULL, FK (entidad destino), ENUM_VALS
"""
import re
import unicodedata
from typing import Dict, List, Optional

# ─────────────────────────────────────────────
#  Normalización de nombres
# ─────────────────────────────────────────────
_STOPWORDS = {
    'nuevo', 'nueva', 'nuevos', 'nuevas', 'editar', 'crear', 'agregar',
    'registrar', 'registro', 'gestion', 'gestionar', 'lista', 'listado',
    'panel', 'modulo', 'formulario', 'form', 'modal', 'de', 'del', 'la',
    'el', 'los', 'las', 'mis', 'mi', 'plan',
}
_IRREGULAR_SINGULAR = {
    'proveedores': 'proveedor', 'clientes': 'cliente', 'asientos': 'asiento',
    'cuentas': 'cuenta', 'ventas': 'venta', 'compras': 'compra',
    'citas': 'cita', 'pacientes': 'paciente', 'pagos': 'pago',
    'usuarios': 'usuario', 'productos': 'producto', 'categorias': 'categoria',
    'pedidos': 'pedido', 'casos': 'caso', 'documentos': 'documento',
    'servicios': 'servicio', 'tratamientos': 'tratamiento',
}


def quitar_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def a_snake_case(texto: str) -> str:
    texto = quitar_acentos(texto.strip())
    texto = re.sub(r'(?<=[a-z0-9])([A-Z])', r'_\1', texto)
    texto = re.sub(r'[^0-9a-zA-Z]+', '_', texto)
    return texto.strip('_').lower()


def singularizar(palabra: str) -> str:
    if palabra in _IRREGULAR_SINGULAR:
        return _IRREGULAR_SINGULAR[palabra]
    if palabra.endswith('es') and len(palabra) > 4 and palabra[-3] in 'rndlj':
        return palabra[:-2]
    if palabra.endswith('s') and len(palabra) > 3 and not palabra.endswith('ss'):
        return palabra[:-1]
    return palabra


def nombre_entidad(titulo: str) -> str:
    partes = [p for p in a_snake_case(titulo).split('_') if p and p not in _STOPWORDS]
    if not partes:
        return ''
    partes[-1] = singularizar(partes[-1])
    return '_'.join(partes)


def a_clase(tabla: str) -> str:
    """tbl_seg_usuario → TblSegUsuario (misma convención de toda la familia)."""
    return ''.join(p.capitalize() for p in tabla.split('_'))


def titulo_legible(entidad: str) -> str:
    return ' '.join(p.capitalize() for p in entidad.split('_'))


# ─────────────────────────────────────────────
#  Inferencia de tipos
# ─────────────────────────────────────────────
_POR_NOMBRE = [
    (r'(email|correo|mail)$',                          ('varchar', 'VARCHAR(191)')),
    (r'(password|clave|contrasena|contrasenia)$',      ('varchar', 'VARCHAR(255)')),
    (r'(telefono|celular|phone|whatsapp|tel)$',        ('varchar', 'VARCHAR(20)')),
    (r'(^|_)(precio|monto|total|subtotal|iva|saldo|costo|importe|debe|haber|salario|pago)(_|$)',
                                                       ('decimal', 'DECIMAL(12,2)')),
    (r'(^|_)(cantidad|stock|quantity|nivel|orden|anio|year|numero|size|talla|duracion)(_|$)',
                                                       ('int',     'INT UNSIGNED')),
    (r'(descripcion|notas?|observacion(es)?|direccion|concepto|hechos|peticion|detalle|description|address|comentario)$',
                                                       ('text',    'TEXT')),
    (r'(activo|activa|visible|habilitado|enabled|destacado|pagado)$',
                                                       ('tinyint', 'TINYINT(1) NOT NULL DEFAULT 1')),
    (r'(imagen|foto|image|avatar|logo|url|image_url|archivo|file)$',
                                                       ('varchar', 'VARCHAR(500)')),
    (r'(nit|ci|dni|codigo|code|matricula|expediente|placa|slug)$',
                                                       ('varchar', 'VARCHAR(50)')),
    (r'fecha_hora',                                    ('datetime', 'DATETIME')),
    (r'(^fecha($|_)|_fecha$|^date$|_date$)',           ('date',    'DATE')),
    (r'(^hora($|_)|_hora$|^time$)',                    ('time',    'TIME')),
    (r'(estado|status|tipo|categoria|category|gender|genero|rol|metodo.*|.*method)$',
                                                       ('varchar', 'VARCHAR(50)')),
]
_POR_INPUT_HTML = {
    'email':          ('varchar',  'VARCHAR(191)'),
    'password':       ('varchar',  'VARCHAR(255)'),
    'tel':            ('varchar',  'VARCHAR(20)'),
    'date':           ('date',     'DATE'),
    'datetime-local': ('datetime', 'DATETIME'),
    'time':           ('time',     'TIME'),
    'checkbox':       ('tinyint',  'TINYINT(1) NOT NULL DEFAULT 1'),
    'number':         ('decimal',  'DECIMAL(12,2)'),
    'url':            ('varchar',  'VARCHAR(500)'),
    'textarea':       ('text',     'TEXT'),
}
_POR_TIPO_TS = {
    'string':  ('varchar',  'VARCHAR(150)'),
    'number':  ('decimal',  'DECIMAL(12,2)'),
    'boolean': ('tinyint',  'TINYINT(1) NOT NULL DEFAULT 1'),
    'date':    ('datetime', 'DATETIME'),
}
_DEFECTO = ('varchar', 'VARCHAR(150)')


def inferir_tipo(nombre: str, tipo_html: str = '', tipo_ts: str = '',
                 opciones: Optional[List[str]] = None):
    """(DATA_TYPE, SQL_FULL, ENUM_VALS) — prioridad: enum > nombre > input/ts."""
    if opciones:
        vals = [quitar_acentos(o)[:40] for o in opciones if o][:10]
        if 1 < len(vals) <= 10:
            lista = ','.join(f"'{v}'" for v in vals)
            return 'enum', f"ENUM({lista}) NOT NULL DEFAULT '{vals[0]}'", vals
    for patron, tipo in _POR_NOMBRE:
        if re.search(patron, nombre):
            return tipo[0], tipo[1], None
    if tipo_html in _POR_INPUT_HTML:
        t = _POR_INPUT_HTML[tipo_html]
        return t[0], t[1], None
    if tipo_ts.lower() in _POR_TIPO_TS:
        t = _POR_TIPO_TS[tipo_ts.lower()]
        return t[0], t[1], None
    return _DEFECTO[0], _DEFECTO[1], None


# ─────────────────────────────────────────────
#  Construcción de tablas con estándares
# ─────────────────────────────────────────────
COLS_AUTO = frozenset({'created_at', 'updated_at'})   # las gestiona el SP
_COLS_ESTANDAR = {'id', 'activo', 'created_at', 'updated_at'}


def col(nombre, data_type, sql_full, nullable=True, key='', extra='',
        fk=None, enum_vals=None) -> Dict:
    return {
        'COLUMN_NAME': nombre, 'DATA_TYPE': data_type,
        'IS_NULLABLE': 'YES' if nullable else 'NO',
        'COLUMN_KEY': key, 'EXTRA': extra,
        'SQL_FULL': sql_full, 'FK': fk, 'ENUM_VALS': enum_vals,
    }


def construir_tablas(entidades_crudas: List[Dict], modulo: str) -> List[Dict]:
    nombres = {e['nombre'] for e in entidades_crudas}
    tablas = []

    for ent in entidades_crudas:
        cols = [col('id', 'bigint', 'BIGINT UNSIGNED NOT NULL AUTO_INCREMENT',
                    nullable=False, key='PRI', extra='auto_increment')]
        vistos = {'id'}

        for campo in ent['campos']:
            nombre = campo['nombre']
            if nombre in vistos or nombre in _COLS_ESTANDAR or not nombre:
                continue
            vistos.add(nombre)

            stem = nombre[:-3] if nombre.endswith('_id') else None
            if stem is None and campo.get('tipo_html') == 'select':
                candidato = singularizar(nombre)
                if candidato in nombres and candidato != ent['nombre']:
                    stem, nombre = candidato, f"{candidato}_id"
            if stem:
                destino = stem if stem in nombres else None
                cols.append(col(nombre, 'bigint', 'BIGINT UNSIGNED NOT NULL',
                                nullable=False, fk=destino))
                continue

            dt, full, enum_vals = inferir_tipo(
                nombre, campo.get('tipo_html', ''), campo.get('tipo_ts', ''),
                campo.get('opciones'))
            nullable = dt in ('text', 'date', 'datetime', 'time') or \
                       full.startswith('VARCHAR(500)')
            if 'NOT NULL' not in full and not nullable:
                full += ' NOT NULL'
            cols.append(col(nombre, dt, full, nullable=nullable,
                            enum_vals=enum_vals))

        cols.append(col('activo', 'tinyint', 'TINYINT(1) NOT NULL DEFAULT 1',
                        nullable=False))
        cols.append(col('created_at', 'timestamp', 'TIMESTAMP NULL DEFAULT NULL'))
        cols.append(col('updated_at', 'timestamp', 'TIMESTAMP NULL DEFAULT NULL'))

        tablas.append({
            'entidad':  ent['nombre'],
            'tabla':    f"tbl_{modulo}_{ent['nombre']}",
            'vista':    f"vis_{modulo}_{ent['nombre']}",
            'origen':   ent.get('origen', '').replace('\\', '/'),
            'columnas': cols,
        })

    return ordenar_por_dependencias(tablas)


def ordenar_por_dependencias(tablas: List[Dict]) -> List[Dict]:
    ordenadas, pendientes, listos = [], list(tablas), set()
    for _ in range(len(tablas) + 1):
        avance = False
        for t in list(pendientes):
            deps = {c['FK'] for c in t['columnas'] if c['FK']}
            if deps <= listos:
                ordenadas.append(t)
                listos.add(t['entidad'])
                pendientes.remove(t)
                avance = True
        if not avance:
            break
    ordenadas.extend(pendientes)
    return ordenadas
