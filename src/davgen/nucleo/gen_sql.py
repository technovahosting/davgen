"""
gen_sql.py — FASE base de datos: scripts SQL numerados en orden de ejecución.

  01_seguridad.sql      usuarios + tokens + 2FA + archivos + CONFIGURACIÓN DE
                        ACCESO (roles, módulos, permisos, parámetros, bitácora)
                        + vistas seg + admin inicial. Idempotente: los seeds
                        usan INSERT IGNORE y NUNCA pisan lo administrado en BD.
  02_negocio.sql        tablas del negocio (orden FK) + vistas   (solo mockup)
  03_procedimientos.sql SPs CRUD: C/R/U con created_at/updated_at NOW(),
                        D = borrado lógico activo=0 (siempre funcional)
"""
import os
from datetime import datetime  # noqa: F401
from .reloj import ahora as _ahora
from typing import Dict, List

from . import bd as _bd
from .esquema import COLS_AUTO, a_clase, titulo_legible
from .plantillas import cargar as _plantilla


def _fecha() -> str:
    return _ahora().strftime('%Y-%m-%d %H:%M')


def _hash_admin(password: str = '') -> str:
    """Hash bcrypt ($2y$, el formato que espera Laravel) de la contraseña
    inicial del admin. Sin la librería bcrypt devuelve un relleno que NO sirve
    para entrar: el script lo dice en un comentario y `davgen doctor` lo avisa.

    Sin contraseña (proyecto recién creado, antes de que el usuario escriba la
    suya) se usa un valor al azar que no se guarda en ningún lado: el hash es
    válido pero nadie puede entrar con él. davgen no trae ninguna de fábrica."""
    if not password:
        import secrets
        password = secrets.token_urlsafe(32)
    try:
        import bcrypt
        h = bcrypt.hashpw(password.encode('utf-8'),
                          bcrypt.gensalt(rounds=12)).decode()
        return h.replace('$2b$', '$2y$')
    except ImportError:
        return '$2y$12$REEMPLAZAR_ESTE_HASH_falta_la_libreria_bcrypt_xxxxxxxxxxxxxxx'


# ═════════════════════════════════════════════
#  01_seguridad.sql
# ═════════════════════════════════════════════
_SEGURIDAD = _plantilla('sql/seguridad.sql', __name__, '_SEGURIDAD')


def _seed_modulos(tablas: List[Dict]) -> str:
    """INSERT IGNORE de un módulo de negocio por tabla (clave única = tabla)."""
    if not tablas:
        return '-- (sin tablas de negocio)'
    filas = ',\n'.join(
        f"  ('{t['tabla']}', '{titulo_legible(t['entidad'])}', 'negocio', "
        f"{(i + 1) * 10}, NOW())"
        for i, t in enumerate(tablas))
    return ("INSERT IGNORE INTO `tbl_seg_modulo` "
            "(`clave`, `titulo`, `tipo`, `orden`, `created_at`)\nVALUES\n"
            + filas + ';')


def _owner_seed(owner_email: str) -> str:
    """Bloque SQL para sembrar el correo DUEÑO (Google) como admin verificado, o
    un comentario si no se configuró [seguridad] owner_email."""
    owner_email = (owner_email or '').strip()
    if not owner_email:
        return '-- (sin [seguridad] owner_email: no se siembra dueño Google)'
    safe = owner_email.replace("'", "''")
    return ("INSERT INTO `tbl_seg_usuario` "
            "(`nombre`, `email`, `password`, `rol`, `activo`, `created_at`)\n"
            f"VALUES ('Owner', '{safe}', '', 'admin', 1, NOW())\n"
            "ON DUPLICATE KEY UPDATE `rol` = 'admin', `activo` = 1;")


def _escribir_seguridad(ruta: str, *, admin_email: str, admin_nombre: str,
                        owner_email: str, seed_modulos: str, max_mb,
                        extensiones: str, google_dominios: str,
                        roles_solo_google: str, google_activo: str = '1',
                        google_client_id: str = '',
                        admin_password: str = '',
                        retencion_dias: int = 365) -> None:
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(_SEGURIDAD.format(
            fecha=_fecha(), retencion_dias=int(retencion_dias),
            admin_email=admin_email, admin_nombre=admin_nombre,
            hash_admin=_hash_admin(admin_password), owner_seed=_owner_seed(owner_email),
            seed_modulos=seed_modulos, max_mb=max_mb, extensiones=extensiones,
            google_dominios=google_dominios, roles_solo_google=roles_solo_google,
            google_activo=google_activo, google_client_id=google_client_id))


def generar_seguridad(carpeta: str, dominio: str, tablas: List[Dict],
                      cfg: Dict) -> str:
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, '01_seguridad.sql')
    _escribir_seguridad(
        ruta,
        admin_email=cfg.get('admin_email', 'admin@localhost'),
        admin_nombre=cfg.get('admin_nombre', 'Administrador'),
        owner_email=cfg.get('owner_email', ''),
        seed_modulos=_seed_modulos(tablas),
        max_mb=cfg['max_archivo_mb'],
        extensiones=','.join(cfg['extensiones_archivo']),
        google_dominios=cfg.get('google_dominios_permitidos', ''),
        roles_solo_google=cfg.get('roles_solo_google', 'cliente'),
        google_activo='1' if cfg.get('google_auth_activo', False) else '0',
        google_client_id=cfg.get('google_client_id', ''),
        admin_password=cfg.get('admin_password', ''),
        retencion_dias=cfg.get('legal', {}).get('retencion_bitacora_dias', 365))
    return ruta


def generar_seguridad_inicial(carpeta: str,
                              nombre_archivo: str = '00-seguridad.sql',
                              admin_password: str = '') -> str:
    """Escribe el script de seguridad (tbl_seg_*) con valores POR DEFECTO, sin
    depender del esquema de negocio. Se usa al CREAR el proyecto (carpeta 02-*),
    para que `00-seguridad.sql` exista desde el inicio y el usuario lo ejecute
    en su BD ANTES de generar. Valores neutros: admin `admin@localhost`, sin
    cuenta dueña y con Google APAGADO (se activa con un Client ID propio)."""
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre_archivo)
    _escribir_seguridad(
        ruta, admin_email='admin@localhost', admin_nombre='Administrador',
        owner_email='', seed_modulos=_seed_modulos([]),
        max_mb=10, extensiones='pdf,jpg,jpeg,png,doc,docx,xls,xlsx',
        google_dominios='', roles_solo_google='cliente',
        google_activo='0', google_client_id='',
        admin_password=admin_password)
    if not admin_password:
        with open(ruta, encoding='utf-8') as f:
            cuerpo = f.read()
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(AVISO_SIN_CLAVE + cuerpo)
    return ruta


# Cabecera del script cuando todavía no hay contraseña de administrador.
AVISO_SIN_CLAVE = (
    "-- ATENCION: este script todavia NO lleva tu contrasena de administrador.\n"
    "-- No lo ejecutes a mano asi: el administrador quedaria sin poder ingresar.\n"
    "-- 1) Escribe la tuya en _acceso.desarrollo.ini -> [seguridad] admin_password\n"
    "-- 2) Ejecuta:  davgen seguridad   (reescribe este archivo y lo aplica)\n\n")


# ═════════════════════════════════════════════
#  README-SEGURIDAD.md — tablas obligatorias + código protegido
# ═════════════════════════════════════════════
_README_SEGURIDAD = _plantilla('sql/readme_seguridad.md', __name__, '_README_SEGURIDAD')


def generar_readme_seguridad(carpeta: str, admin_email: str = 'admin@localhost') -> str:
    """README de seguridad: tablas obligatorias + regla de no modificar."""
    from .version import VERSION
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, 'README-SEGURIDAD.md')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(_README_SEGURIDAD.format(version=VERSION, admin_email=admin_email,
                                         fecha=_fecha()))
    return ruta


# ═════════════════════════════════════════════
#  readme_cero.md — reglas de la carpeta 02-Base-de-datos
# ═════════════════════════════════════════════
_README_CERO = _plantilla('sql/readme_cero.md', __name__, '_README_CERO')


def generar_readme_cero(carpeta: str) -> str:
    """readme_cero.md para 02-Base-de-datos: reglas sobre 00-seguridad.sql."""
    from .version import VERSION
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, 'readme_cero.md')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(_README_CERO.format(version=VERSION, fecha=_fecha()))
    return ruta


# ═════════════════════════════════════════════
#  02_negocio.sql — tablas + vistas del negocio
# ═════════════════════════════════════════════
def _ddl_columna(c: Dict) -> str:
    """Tipo+atributos de la columna para el CREATE TABLE. Reañade AUTO_INCREMENT
    si la columna lo es y SQL_FULL no lo trae (caso tipo=bd: COLUMN_TYPE no
    incluye el EXTRA). Imprescindible para que el SP con LAST_INSERT_ID funcione
    al desplegar el 02_negocio.sql en una BD nueva."""
    sql = c['SQL_FULL']
    if ('auto_increment' in (c.get('EXTRA') or '').lower()
            and 'AUTO_INCREMENT' not in sql.upper()):
        sql += ' AUTO_INCREMENT'
    return sql


def _create_table(t: Dict, idx: Dict[str, Dict]) -> str:
    base = t['tabla'].replace('tbl_', '', 1)
    ancho = max(len(c['COLUMN_NAME']) for c in t['columnas']) + 2
    lineas = [f"  `{c['COLUMN_NAME']}`{' ' * (ancho - len(c['COLUMN_NAME']))}{_ddl_columna(c)},"
              for c in t['columnas']]
    claves = ["  PRIMARY KEY (`id`),", f"  KEY `idx_{base}_activo` (`activo`),"]
    for c in t['columnas']:
        col_name = c['COLUMN_NAME']
        if col_name.endswith('_id'):
            claves.append(f"  KEY `idx_{base}_{col_name}` (`{col_name}`),")
        # FK: tipo=bd trae la tabla/regla reales (FK_TABLA); mockup usa el idx.
        ref_tabla = on_delete = None
        if c.get('FK_TABLA'):
            ref_tabla, on_delete = c['FK_TABLA'], (c.get('FK_ONDELETE') or 'RESTRICT')
        elif c.get('FK') and c['FK'] in idx:
            ref_tabla, on_delete = idx[c['FK']]['tabla'], 'RESTRICT'
        if ref_tabla:
            claves.append(
                f"  CONSTRAINT `fk_{base}_{col_name}`\n"
                f"    FOREIGN KEY (`{col_name}`)\n"
                f"    REFERENCES `{ref_tabla}` (`id`)\n"
                f"    ON DELETE {on_delete},")
    cuerpo = '\n'.join(lineas + claves).rstrip(',')
    comentario = f"Entidad {t['entidad']} — {t['origen']}".replace("'", '')
    return (
        f"-- ── {t['tabla']} ──────────────────────────────────────────────\n"
        f"CREATE TABLE IF NOT EXISTS `{t['tabla']}` (\n{cuerpo}\n"
        f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci\n"
        f"  COMMENT='{comentario}';\n"
    )


def _col_etiqueta(t: Dict) -> str:
    nombres = [c['COLUMN_NAME'] for c in t['columnas']]
    for candidato in ('nombre', 'name', 'titulo', 'concepto', 'codigo', 'descripcion'):
        if candidato in nombres:
            return candidato
    return 'id'


def _create_view(t: Dict, idx: Dict[str, Dict]) -> str:
    selecciones, joins, n = [], [], 0
    usados = {c['COLUMN_NAME'] for c in t['columnas']}
    for c in t['columnas']:
        selecciones.append(f"  t.`{c['COLUMN_NAME']}`")
        if c['FK'] and c['FK'] in idx:
            n += 1
            etiqueta = _col_etiqueta(idx[c['FK']])
            alias = f"{c['FK']}_{etiqueta}"
            if alias in usados:                 # la tabla ya tiene esa columna
                alias = f"{c['FK']}_{etiqueta}_ref"
            usados.add(alias)
            selecciones.append(f"  r{n}.`{etiqueta}` AS `{alias}`")
            joins.append(f"LEFT JOIN `{idx[c['FK']]['tabla']}` r{n} "
                         f"ON r{n}.id = t.`{c['COLUMN_NAME']}`")
    joins_sql = ('\n' + '\n'.join(joins)) if joins else ''
    return (f"CREATE OR REPLACE VIEW `{t['vista']}` AS\nSELECT\n"
            + ',\n'.join(selecciones) + f"\nFROM `{t['tabla']}` t{joins_sql};\n")


def generar_negocio(tablas: List[Dict], carpeta: str, proyecto: str) -> str:
    idx = {t['entidad']: t for t in tablas}
    contenido = (
        f"-- =============================================================================\n"
        f"-- 02_negocio.sql — {proyecto} — {_fecha()}\n"
        f"-- {len(tablas)} tabla(s) + vistas, con sus FOREIGN KEY reconstruidas.\n"
        f"-- =============================================================================\n"
        f"SET NAMES utf8mb4;\n"
        f"-- FK checks off durante la creación: el orden de las tablas no importa\n"
        f"-- (las CONSTRAINT quedan activas igual al re-activarlo al final).\n"
        f"SET FOREIGN_KEY_CHECKS = 0;\n\n"
        + '\n'.join(_create_table(t, idx) for t in tablas)
        + "\n-- ════════ VISTAS ════════\n\n"
        + '\n'.join(_create_view(t, idx) for t in tablas)
        + "\nSET FOREIGN_KEY_CHECKS = 1;\n")
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, '02_negocio.sql')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(contenido)
    return ruta


# ═════════════════════════════════════════════
#  03_procedimientos.sql — SPs CRUD
# ═════════════════════════════════════════════
_TIPO_SP = {
    'int': 'INT', 'smallint': 'INT', 'tinyint': 'TINYINT', 'mediumint': 'INT',
    'bigint': 'BIGINT', 'year': 'INT', 'decimal': 'DECIMAL(12,2)',
    'float': 'FLOAT', 'double': 'DOUBLE', 'varchar': 'VARCHAR(255)',
    'char': 'CHAR(10)', 'text': 'TEXT', 'longtext': 'LONGTEXT',
    'mediumtext': 'TEXT', 'tinytext': 'VARCHAR(255)', 'date': 'DATE',
    'datetime': 'DATETIME', 'timestamp': 'DATETIME', 'time': 'TIME',
    'boolean': 'TINYINT(1)', 'enum': 'VARCHAR(50)', 'set': 'VARCHAR(100)',
    'json': 'JSON',
}


def cols_parametro(columnas: List[Dict]) -> List[Dict]:
    """Columnas que son parámetro del SP (excluye created_at/updated_at)."""
    return [c for c in columnas if c['COLUMN_NAME'].lower() not in COLS_AUTO]


def _tipo_param_sp(c: Dict) -> str:
    """Tipo del parámetro IN del SP: hereda el tipo/longitud REAL de la columna
    (VARCHAR(50), DECIMAL(12,2), ENUM(...), INT…) en lugar de un VARCHAR(255)
    fijo, para que el límite sea coherente extremo a extremo. Cae al mapa
    _TIPO_SP solo si la columna no trae SQL_FULL."""
    full = (c.get('SQL_FULL') or '').strip()
    if full:
        up = full.upper()
        for marca in (' NOT NULL', ' NULL', ' AUTO_INCREMENT', ' DEFAULT', ' COMMENT'):
            i = up.find(marca)
            if i != -1:
                full = full[:i]
                up = full.upper()
        full = full.strip()
        if full:
            return full
    return _TIPO_SP.get(c['DATA_TYPE'].lower(), 'VARCHAR(255)')


def _sp_tabla(t: Dict) -> str:
    cn  = a_clase(t['tabla'])
    pk  = next((c['COLUMN_NAME'] for c in t['columnas'] if c['COLUMN_KEY'] == 'PRI'), 'id')
    nombres = {c['COLUMN_NAME'].lower() for c in t['columnas']}
    # ¿la PK es AUTO_INCREMENT? entonces la asigna MySQL (atómico, sin MAX+1)
    pk_auto = any(c['COLUMN_NAME'] == pk and 'auto_increment' in (c.get('EXTRA') or '').lower()
                  for c in t['columnas'])

    params = ['IN `p__op` VARCHAR(1)'] + [
        f"IN `p{c['COLUMN_NAME']}` {_tipo_param_sp(c)}"
        for c in cols_parametro(t['columnas'])]

    # INSERT: columnas de negocio (activo fijo en 1, fechas NOW()). Si la PK es
    # AUTO_INCREMENT NO se incluye: la asigna MySQL (evita colisiones de id).
    ins = [c['COLUMN_NAME'] for c in cols_parametro(t['columnas'])
           if c['COLUMN_NAME'].lower() != 'activo'
           and not (pk_auto and c['COLUMN_NAME'] == pk)]
    ins_cols = ', '.join(f'`{c}`' for c in ins)
    ins_vals = ', '.join(f'p{c}' for c in ins)
    extra_c = extra_v = ''
    for fecha in ('created_at', 'updated_at'):
        if fecha in nombres:
            extra_c += f', `{fecha}`'
            extra_v += ', NOW()'
    if 'activo' in nombres:
        extra_c += ', `activo`'
        extra_v += ', 1'

    # UPDATE: todo menos PK y autocols
    upd = [f"        `{c['COLUMN_NAME']}` = p{c['COLUMN_NAME']}"
           for c in cols_parametro(t['columnas']) if c['COLUMN_NAME'] != pk]
    if 'updated_at' in nombres:
        upd.append("        `updated_at` = NOW()")
    upd_sql = ',\n'.join(upd)

    cond        = f"`{pk}` = p{pk}"
    cond_activo = cond + (" AND `activo` = 1" if 'activo' in nombres else '')
    baja = (f"        UPDATE `{t['tabla']}` SET `activo` = 0"
            + (", `updated_at` = NOW()" if 'updated_at' in nombres else '')
            + f" WHERE {cond};") if 'activo' in nombres \
        else "        -- tabla sin columna activo: borrado lógico no disponible"

    # Validaciones ENUM al inicio del SP
    enum_checks = []
    for c in cols_parametro(t['columnas']):
        if c['DATA_TYPE'].lower() == 'enum' and c.get('ENUM_VALS'):
            vals_sql = ', '.join(f"'{v}'" for v in c['ENUM_VALS'])
            campo = c['COLUMN_NAME']
            enum_checks.append(
                f"    IF p{campo} NOT IN ({vals_sql}) THEN\n"
                f"        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = "
                f"'{campo}: valor no permitido';\n"
                f"    END IF;")
    enum_block = ('\n'.join(enum_checks) + '\n\n') if enum_checks else ''

    if pk_auto:
        crear = f"""    -- C · crear (id AUTO_INCREMENT: lo asigna MySQL → atómico, sin colisión)
    IF p__op = 'C' THEN
        INSERT INTO `{t['tabla']}` ({ins_cols}{extra_c})
        VALUES ({ins_vals}{extra_v});
        SET p{pk} = LAST_INSERT_ID();
        SELECT * FROM `{t['tabla']}` WHERE {cond_activo};
    END IF;"""
    else:
        crear = f"""    -- C · crear (PK no auto: pid=0 calcula el siguiente id)
    IF p__op = 'C' THEN
        IF p{pk} = 0 THEN
            SET p{pk} = (SELECT IFNULL(MAX(`{pk}`) + 1, 1) FROM `{t['tabla']}`);
        END IF;
        INSERT INTO `{t['tabla']}` ({ins_cols}{extra_c})
        VALUES ({ins_vals}{extra_v});
        SELECT * FROM `{t['tabla']}` WHERE {cond_activo};
    END IF;"""

    return f"""\
DROP PROCEDURE IF EXISTS `pcru{cn}`//
CREATE PROCEDURE `pcru{cn}`(
    {(',' + chr(10) + '    ').join(params)}
)
BEGIN
{enum_block}{crear}

    -- R · leer por PK (solo activos)
    IF p__op = 'R' THEN
        SELECT * FROM `{t['tabla']}` WHERE {cond_activo};
    END IF;

    -- U · actualizar por PK
    IF p__op = 'U' THEN
        UPDATE `{t['tabla']}` SET
{upd_sql}
        WHERE {cond};
        SELECT * FROM `{t['tabla']}` WHERE {cond_activo};
    END IF;

    -- D · borrado lógico
    IF p__op = 'D' THEN
{baja}
        SELECT * FROM `{t['tabla']}` WHERE {cond};
    END IF;
END//"""


def _statements_sp(ruta_sql: str) -> List[str]:
    """Statements del 03_procedimientos.sql listos para mysql.connector:
    quita las líneas DELIMITER (que el conector no entiende) y separa por `//`."""
    with open(ruta_sql, encoding='utf-8') as f:
        lineas = [l for l in f.read().splitlines()
                  if not l.strip().upper().startswith('DELIMITER')]
    return [s.strip() for s in '\n'.join(lineas).split('//') if s.strip()]


def _nombre_create(stmt: str):
    import re
    m = re.search(r'CREATE\s+PROCEDURE\s+`?(\w+)`?', stmt, re.IGNORECASE)
    return m.group(1) if m else None


def _norm_sp(texto: str) -> str:
    import re
    return re.sub(r'\s+', ' ', texto or '').strip().lower()


def aplicar_procedimientos(bd: Dict, ruta_sql: str, aplicar: bool = True) -> Dict:
    """Compara los SPs pcru* del 03_procedimientos.sql contra la BD y, si
    `aplicar`, ejecuta (DROP+CREATE) los nuevos o distintos. Devuelve un
    reporte {nuevos, actualizados, iguales, errores} (o {'error': msg} si no
    conecta). La comparación normaliza espacios (es aproximada: ante la duda
    recrea, que es idempotente)."""
    try:
        conn = _bd.conectar(bd, timeout=20)
    except Exception as e:
        return {'error': _bd.mensaje_error(e)}

    creates = {}
    for s in _statements_sp(ruta_sql):
        if s.upper().startswith('CREATE PROCEDURE'):
            nombre = _nombre_create(s)
            if nombre:
                creates[nombre] = s

    reporte = {'nuevos': [], 'actualizados': [], 'iguales': [], 'errores': []}
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT ROUTINE_NAME, ROUTINE_DEFINITION "
            "FROM INFORMATION_SCHEMA.ROUTINES "
            "WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'PROCEDURE'",
            (bd['database'],))
        actuales = {_bd.texto(r[0]): _bd.texto(r[1]) for r in cur.fetchall()}
        for nombre, stmt in sorted(creates.items()):
            i = stmt.upper().find('BEGIN')
            generado = _norm_sp(stmt[i:] if i >= 0 else stmt)
            if nombre not in actuales:
                estado = 'nuevos'
            elif _norm_sp(actuales[nombre]) == generado:
                estado = 'iguales'
            else:
                estado = 'actualizados'
            if estado != 'iguales' and aplicar:
                try:
                    cur.execute(f"DROP PROCEDURE IF EXISTS `{nombre}`")
                    cur.execute(stmt)
                except Exception as e:
                    reporte['errores'].append(f"{nombre}: {e}")
                    continue
            reporte[estado].append(nombre)
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return reporte


def _vistas_de_sql(ruta_sql: str) -> Dict:
    """{nombre: statement} de las CREATE OR REPLACE VIEW de un script SQL
    generado (las vistas generadas son un único SELECT sin ';' interno)."""
    import re
    with open(ruta_sql, encoding='utf-8') as f:
        texto = f.read()
    return {m.group(1): m.group(0)
            for m in re.finditer(
                r'CREATE\s+OR\s+REPLACE\s+VIEW\s+`?(\w+)`?\s+AS\b.*?;',
                texto, re.IGNORECASE | re.DOTALL)}


def _seeds_de_sql(ruta_sql: str) -> List[str]:
    """Statements INSERT de la sección SEEDS del 01_seguridad.sql (todos
    idempotentes: INSERT IGNORE / ON DUPLICATE KEY UPDATE). Las descripciones
    sembradas NO llevan ';' (regla del proyecto desde v4.34.1), así que
    separar por ';' es seguro."""
    with open(ruta_sql, encoding='utf-8') as f:
        texto = f.read()
    idx = texto.find('-- SEEDS')
    if idx < 0:
        return []
    lineas = [l for l in texto[idx:].splitlines()
              if not l.strip().startswith('--')]
    stmts = [s.strip() for s in '\n'.join(lineas).split(';') if s.strip()]
    return [s + ';' for s in stmts if s.upper().startswith('INSERT')]


def sentencias_script(texto: str) -> List[str]:
    """Parte un script SQL de MySQL/MariaDB en sentencias ejecutables una a
    una, como lo haría el cliente `mysql`: respeta las líneas `DELIMITER x`,
    los comentarios (`-- …`, `# …`, `/* … */`) y no corta en un `;` que esté
    dentro de una cadena o de un identificador entre acentos graves."""
    sentencias: List[str] = []
    delim = ';'
    actual: List[str] = []
    cita = ''                       # carácter de la cadena abierta, o ''
    en_bloque = False               # dentro de /* … */

    def cerrar():
        s = ''.join(actual).strip()
        actual.clear()
        if s:
            sentencias.append(s)

    for linea in texto.replace('\r\n', '\n').split('\n'):
        limpia = linea.strip()
        if not cita and not en_bloque and limpia.upper().startswith('DELIMITER '):
            cerrar()
            delim = limpia.split(None, 1)[1].strip()
            continue
        i, n = 0, len(linea)
        while i < n:
            c = linea[i]
            if en_bloque:
                if linea.startswith('*/', i):
                    en_bloque = False
                    i += 2
                    continue
                i += 1
                continue
            if cita:
                actual.append(c)
                if c == '\\' and cita != '`' and i + 1 < n:
                    actual.append(linea[i + 1])
                    i += 2
                    continue
                if c == cita:
                    if i + 1 < n and linea[i + 1] == cita:    # '' escapada
                        actual.append(cita)
                        i += 2
                        continue
                    cita = ''
                i += 1
                continue
            if c in ('\'', '"', '`'):
                cita = c
                actual.append(c)
                i += 1
                continue
            if c == '#' or (linea.startswith('--', i)
                            and (i + 2 >= n or linea[i + 2] in ' \t')):
                break                                   # comentario de línea
            if linea.startswith('/*', i):
                en_bloque = True
                i += 2
                continue
            if linea.startswith(delim, i):
                cerrar()
                i += len(delim)
                continue
            actual.append(c)
            i += 1
        actual.append('\n')
    cerrar()
    return sentencias


def crear_seguridad(bd: Dict, ruta_sql: str) -> Dict:
    """Ejecuta el script de seguridad COMPLETO (tablas `tbl_seg_*`, vistas y
    seeds) en una base que todavía no lo tiene. Es lo que antes había que hacer
    a mano con un cliente de MySQL.

    No hace nada si `tbl_seg_usuario` ya existe: una base sembrada se mantiene
    con `aplicar_seguridad` (que no pisa lo administrado). Se detiene en el
    primer error. Devuelve {ya_existia, ejecutadas, total, tablas, error}
    (o {'error': msg} si no conecta)."""
    try:
        conn = _bd.conectar(bd, timeout=30)
    except Exception as e:
        return {'error': _bd.mensaje_error(e)}
    reporte = {'ya_existia': False, 'ejecutadas': 0, 'total': 0,
               'tablas': [], 'error': ''}

    def _tablas_seg(cur):
        cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'",
                    (bd['database'],))
        return sorted(t for t in (_bd.texto(r[0]).lower() for r in cur.fetchall())
                      if t.startswith('tbl_seg_'))
    try:
        cur = conn.cursor()
        if 'tbl_seg_usuario' in _tablas_seg(cur):
            reporte['ya_existia'] = True
            reporte['tablas'] = _tablas_seg(cur)
            return reporte
        with open(ruta_sql, encoding='utf-8-sig') as f:
            sentencias = sentencias_script(f.read())
        reporte['total'] = len(sentencias)
        for s in sentencias:
            try:
                cur.execute(s)
                reporte['ejecutadas'] += 1
            except Exception as e:
                reporte['error'] = f"{e} — en: {' '.join(s.split())[:90]}…"
                break
        conn.commit()
        reporte['tablas'] = _tablas_seg(cur)
        cur.close()
    finally:
        conn.close()
    return reporte


def aplicar_seguridad(bd: Dict, ruta_seguridad: str,
                      rutas_vistas: List[str] = ()) -> Dict:
    """Aplica en la BD los SEEDS del 01_seguridad.sql (idempotentes: agregan
    roles/módulos/permisos/parámetros NUEVOS y reconcilian admin/owner sin
    pisar lo que el administrador haya ajustado) y crea las vistas vis_* que
    FALTEN — una vista EXISTENTE nunca se reemplaza, porque puede haber sido
    personalizada después de su creación. Devuelve un reporte
    {seeds, seeds_err, vistas_creadas, vistas_respetadas, vistas_err}
    (o {'error': msg} si no conecta)."""
    try:
        conn = _bd.conectar(bd, timeout=20)
    except Exception as e:
        return {'error': _bd.mensaje_error(e)}

    reporte = {'seeds': 0, 'seeds_err': [], 'vistas_creadas': [],
               'vistas_respetadas': [], 'vistas_err': []}
    try:
        cur = conn.cursor()
        # misma zona horaria que fija el script (G-9): NOW() de seeds en UTC
        cur.execute("SET time_zone = '+00:00'")

        # 1) seeds (INSERT IGNORE / ON DUPLICATE — idempotentes)
        for stmt in _seeds_de_sql(ruta_seguridad):
            try:
                cur.execute(stmt)
                reporte['seeds'] += 1
            except Exception as e:
                reporte['seeds_err'].append(str(e))

        # 2) vistas: SOLO las que no existen (respetar personalizaciones)
        cur.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS "
            "WHERE TABLE_SCHEMA = %s", (bd['database'],))
        existentes = {r[0].lower() for r in cur.fetchall()}
        vistas = {}
        for ruta in (ruta_seguridad, *rutas_vistas):
            if ruta and os.path.isfile(ruta):
                vistas.update(_vistas_de_sql(ruta))
        for nombre, stmt in sorted(vistas.items()):
            if nombre.lower() in existentes:
                reporte['vistas_respetadas'].append(nombre)
                continue
            try:
                cur.execute(stmt)
                reporte['vistas_creadas'].append(nombre)
            except Exception as e:
                reporte['vistas_err'].append(f"{nombre}: {e}")
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return reporte


def generar_procedimientos(tablas: List[Dict], carpeta: str, proyecto: str) -> str:
    cuerpo = '\n\n'.join(_sp_tabla(t) for t in tablas)
    contenido = (
        f"-- =============================================================================\n"
        f"-- 03_procedimientos.sql — {proyecto} — {_fecha()}\n"
        f"-- {len(tablas)} SP(s) pcru* · D = borrado lógico activo=0 (funcional)\n"
        f"-- =============================================================================\n\n"
        f"DELIMITER //\n\n{cuerpo}\n\nDELIMITER ;\n")
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, '03_procedimientos.sql')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(contenido)
    return ruta
