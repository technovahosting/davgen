"""
gen_backend.py — FASE backend: Laravel estandarizado.

Mejoras v4 sobre la familia v1-v3:
  - Envelope corregido: {"mensaje", "info"} (v1 arrastraba el typo 'mesaje').
  - routes/api.php se genera COMPLETO de una vez (sin parches posteriores):
    auth 2FA + archivos + tablas + rutas públicas.
  - ArchivoController: carga de PDF/imágenes/documentos POR USUARIO
    (subir, listar, descargar, eliminar) con validación de tipo y tamaño.
  - Plantillas con tokens __X__ (sin f-strings sobre PHP).
"""
import os
from datetime import datetime  # noqa: F401
from .reloj import ahora as _ahora
from typing import Dict, List

from collections import defaultdict

from .esquema import a_clase
from .gen_sql import cols_parametro
from .version import VERSION
from .plantillas import cargar as _plantilla

_FECHA = lambda: _ahora().strftime('%Y-%m-%d %H:%M')  # noqa: E731


def _cabecera(archivo: str, autor: str) -> str:
    autor_line = f" * @author    {autor}\n" if autor else ''
    return (f"<?php\n/**\n * @generated davgen v{VERSION} | {_FECHA()}\n"
            f" * @file      {archivo}\n{autor_line}"
            f" * ⚠ NO MODIFICAR — regenerado por davgen v{VERSION}. La administración\n"
            f" * y configuración se realiza en la BASE DE DATOS (tbl_seg_*).\n */\n\n")


def _escribir(carpeta: str, nombre: str, cuerpo: str, autor: str = '') -> str:
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(_cabecera(nombre, autor) + cuerpo)
    return ruta


# ═════════════════════════════════════════════
#  PaginationUtil
# ═════════════════════════════════════════════
_PAGINACION = _plantilla('backend/paginacion.php', __name__, '_PAGINACION')

# ═════════════════════════════════════════════
#  Parametro — configuración runtime desde tbl_seg_parametro
# ═════════════════════════════════════════════
_PARAMETRO = _plantilla('backend/parametro.php', __name__, '_PARAMETRO')

# ═════════════════════════════════════════════
#  VerificarPermiso — autorización por rol × módulo × operación (BD)
# ═════════════════════════════════════════════
_RETENCION = _plantilla('backend/retencion.php', __name__, '_RETENCION')

_VERIFICAR_PERMISO = _plantilla('backend/verificar_permiso.php', __name__, '_VERIFICAR_PERMISO')

# ═════════════════════════════════════════════
#  Totp (RFC 6238)
# ═════════════════════════════════════════════
_TOTP = _plantilla('backend/totp.php', __name__, '_TOTP')

# ═════════════════════════════════════════════
#  User model
# ═════════════════════════════════════════════
_USER = _plantilla('backend/user.php', __name__, '_USER')

# ═════════════════════════════════════════════
#  BaseController — selQuery con envelope 'mensaje'
# ═════════════════════════════════════════════
_BASE = _plantilla('backend/controller_base.php', __name__, '_BASE')

# ═════════════════════════════════════════════
#  Capa de SERVICIOS — toda operación valida auth normal + 2FA
# ═════════════════════════════════════════════
_EXCEPCION_SERVICIO = _plantilla('backend/excepcion_servicio.php', __name__, '_EXCEPCION_SERVICIO')

_SERVICE_BASE = _plantilla('backend/service_base.php', __name__, '_SERVICE_BASE')

_SERVICE_TABLA = _plantilla('backend/service_tabla.php', __name__, '_SERVICE_TABLA')


def generar_service_tabla(t: Dict, carpeta: str, autor: str) -> str:
    cn     = a_clase(t['tabla'])
    campos = ', '.join(f"'{c['COLUMN_NAME']}'" for c in t['columnas'])
    cuerpo = (_SERVICE_TABLA
              .replace('__CN__', cn)
              .replace('__VISTA__', t['vista'])
              .replace('__CAMPOS__', campos))
    return _escribir(carpeta, f'{cn}Service.php', cuerpo, autor)


# ═════════════════════════════════════════════
#  AuthController — 2FA por correo o app
# ═════════════════════════════════════════════
_AUTH = _plantilla('backend/auth_controller.php', __name__, '_AUTH')

# ═════════════════════════════════════════════
#  ArchivoController — PDFs y similares por usuario
# ═════════════════════════════════════════════
_ARCHIVO = _plantilla('backend/archivo_controller.php', __name__, '_ARCHIVO')

# ═════════════════════════════════════════════
#  Controllers de administración — datos en tbl_seg_* (gestión desde la BD
#  o desde el módulo Administración del portal; rutas /seguridad/*)
# ═════════════════════════════════════════════
_SEG_USUARIO = _plantilla('backend/seg_usuario.php', __name__, '_SEG_USUARIO')

_SEG_ROL = _plantilla('backend/seg_rol.php', __name__, '_SEG_ROL')

_SEG_PERMISO = _plantilla('backend/seg_permiso.php', __name__, '_SEG_PERMISO')

_SEG_PARAMETRO = _plantilla('backend/seg_parametro.php', __name__, '_SEG_PARAMETRO')

_SEG_BITACORA = _plantilla('backend/seg_bitacora.php', __name__, '_SEG_BITACORA')

# ═════════════════════════════════════════════
#  Helpers de módulo (v4.32.0)
# ═════════════════════════════════════════════
def _modulo_recurso(tabla: str) -> tuple:
    """Extrae (modulo, recurso) de tbl_{mod}_{entity}; fallback ('gen', tabla)."""
    if tabla.startswith('tbl_'):
        resto = tabla[4:]
        idx = resto.find('_')
        if idx > 0:
            return resto[:idx], resto[idx + 1:]
    return 'gen', tabla


def _recurso_uri(recurso: str) -> str:
    """Convierte snake_case a kebab-case para URIs REST."""
    return recurso.replace('_', '-')


# ═════════════════════════════════════════════
#  Controller por tabla
# ═════════════════════════════════════════════
_CONTROLLER_TABLA = _plantilla('backend/controller_tabla.php', __name__, '_CONTROLLER_TABLA')

# Método de exportación a CSV (opcional, [generar] export=si). Lee la vista
# completa y la devuelve como descarga; el permiso lo valida la ruta (op sel).
_EXPORT_METODO = _plantilla('backend/export_metodo.php', __name__, '_EXPORT_METODO')

_TIPOS_FECHA = {'date', 'datetime', 'timestamp', 'time'}
_TIPOS_NUM   = {'int', 'smallint', 'tinyint', 'mediumint', 'bigint', 'year',
                'decimal', 'float', 'double'}


def _params_php(columnas: List[Dict]) -> str:
    lineas = []
    for c in cols_parametro(columnas):
        nombre = f"p{c['COLUMN_NAME']}"
        dt     = c['DATA_TYPE'].lower()
        # Fechas y ENUM: vacío → null SIEMPRE (también si la columna es NOT
        # NULL). Con '' MySQL en modo estricto rechaza la llamada al SP aunque
        # sea un R o un D que solo usa el id ("Incorrect date value: ''").
        if dt in _TIPOS_FECHA or dt == 'enum':
            lineas.append(f"            '{nombre}' => $request->input('{nombre}') ?: null,")
        elif dt in _TIPOS_NUM:
            lineas.append(f"            '{nombre}' => $request->input('{nombre}', 0),")
        else:
            # ?? '' en vez de default en input(): ConvertEmptyStringsToNull
            # convierte "" → null antes de que input() lea la clave, así que
            # el default de input() no aplica cuando la clave existe con null.
            lineas.append(f"            '{nombre}' => $request->input('{nombre}') ?? '',")
    return '\n'.join(lineas)


_TIPOS_ID_ENTERO = {'tinyint', 'smallint', 'mediumint', 'int', 'integer', 'bigint'}


def _pk(columnas: List[Dict]):
    return next((c for c in columnas if c.get('COLUMN_KEY') == 'PRI'), None)


def _validar_id_php(columnas: List[Dict], accion_php: str) -> str:
    """PHP que rechaza con 422 un id que no es un entero (solo si la PK es
    entera). Sin esto, `pid = "1 OR 1=1"` llegaba al procedimiento y MySQL
    respondía con un error interno — no era inyectable (va enlazado), pero
    devolvía 500 y un mensaje de la base."""
    pk = _pk(columnas)
    if not pk or pk['DATA_TYPE'].lower() not in _TIPOS_ID_ENTERO:
        return ''
    campo = f"p{pk['COLUMN_NAME']}"
    return (f"        $idRecibido = $request->input('{campo}');\n"
            f"        if ({accion_php} === 'C'\n"
            f"                ? !($idRecibido === null || $idRecibido === '' || $this->esId($idRecibido))\n"
            f"                : !$this->esId($idRecibido)) {{\n"
            f"            return $this->error('Identificador inválido', 422);\n"
            f"        }}\n")


def _publico_fijos_php(columnas: List[Dict]) -> str:
    """En el alta PÚBLICA se pisan el id (0 = nuevo) y `activo` (1), vengan o no."""
    nombres = {c['COLUMN_NAME'] for c in cols_parametro(columnas)}
    pk = _pk(columnas)
    lineas = []
    if pk and f"{pk['COLUMN_NAME']}" in nombres:
        lineas.append(f"            $params['p{pk['COLUMN_NAME']}'] = 0;\n")
    if 'activo' in nombres:
        lineas.append("            $params['pactivo'] = 1;\n")
    return ''.join(lineas)


def generar_controller_tabla(t: Dict, carpeta_controllers: str, autor: str,
                             con_requests: bool = False,
                             con_export: bool = False) -> str:
    cn         = a_clase(t['tabla'])
    mod, rec   = _modulo_recurso(t['tabla'])
    ctrl_class = f"{mod.title()}{a_clase(rec)}Controller"
    campos     = ', '.join(f"'{c['COLUMN_NAME']}'" for c in t['columnas'])
    # FormRequest opcional: type-hint en add/upd (validación 422 automática)
    use_req    = f"use App\\Http\\Requests\\{cn}Request;\n" if con_requests else ''
    req        = f'{cn}Request' if con_requests else 'Request'
    export     = (_EXPORT_METODO.replace('__CN__', cn)
                  .replace('__VISTA__', t['vista'])
                  .replace('__TABLA__', t['tabla'])) if con_export else ''
    cuerpo     = (_CONTROLLER_TABLA
                  .replace('__USE_REQUEST__', use_req)
                  .replace('__REQADD__', req)
                  .replace('__REQUPD__', req)
                  .replace('__EXPORT_METODO__', export)
                  .replace('__MOD__', mod)
                  .replace('__CTRL_CLASS__', ctrl_class)
                  .replace('__CN__', cn)
                  .replace('__VISTA__', t['vista'])
                  .replace('__CAMPOS__', campos)
                  .replace('__PARAMS__', _params_php(t['columnas']))
                  .replace('__VALIDAR_ID_R__', _validar_id_php(t['columnas'], "'R'"))
                  .replace('__VALIDAR_ID__', _validar_id_php(t['columnas'], '$accion'))
                  .replace('__PUBLICO_FIJOS__', _publico_fijos_php(t['columnas'])))
    # Subcarpeta por módulo: Controllers/{mod}/
    carpeta_mod = os.path.join(carpeta_controllers, mod)
    return _escribir(carpeta_mod, f'{ctrl_class}.php', cuerpo, autor)


# ═════════════════════════════════════════════
#  FormRequest por tabla (opcional · [generar] form_requests=si)
#  Reglas de validación derivadas del esquema; claves p{columna} (el front
#  y el controller usan ese prefijo). authorize()=true: el permiso lo valida
#  VerificarPermiso. failedValidation mantiene el envelope { error:{text} }.
# ═════════════════════════════════════════════
_FORM_REQUEST = _plantilla('backend/form_request.php', __name__, '_FORM_REQUEST')


def _reglas_request(columnas: List[Dict]) -> str:
    import re
    lineas = []
    for c in cols_parametro(columnas):
        nombre = c['COLUMN_NAME']
        dt     = c['DATA_TYPE'].lower()
        sql    = c['SQL_FULL'].upper()
        reglas = []
        # requerido / opcional (la PK siempre llega: 0 = alta, >0 = edición)
        if c['COLUMN_KEY'] == 'PRI':
            reglas.append('required')
        elif c['IS_NULLABLE'] == 'YES':
            reglas.append('nullable')
        else:
            reglas.append('required')
        # tipo
        if dt == 'tinyint' and 'TINYINT(1)' in sql:
            reglas.append('boolean')
        elif dt in ('bigint', 'int', 'smallint', 'mediumint', 'tinyint', 'year'):
            reglas.append('integer')
        elif dt in ('decimal', 'float', 'double'):
            reglas.append('numeric')
        elif dt == 'date':
            reglas.append('date')
        elif dt in ('datetime', 'timestamp'):
            reglas.append('date')
        elif dt == 'time':
            reglas.append('date_format:H:i:s')
        elif dt == 'enum' and c.get('ENUM_VALS'):
            reglas.append('in:' + ','.join(c['ENUM_VALS']))
        else:  # varchar / char / text
            reglas.append('string')
            m = re.search(r'VARCHAR\((\d+)\)', sql)
            if m:
                reglas.append(f'max:{m.group(1)}')
        if re.search(r'(email|correo|mail)$', nombre):
            reglas.append('email')
        lista = ', '.join(f"'{r}'" for r in reglas)
        lineas.append(f"            'p{nombre}' => [{lista}],")
    return '\n'.join(lineas)


def generar_form_request(t: Dict, carpeta: str, autor: str) -> str:
    cn = a_clase(t['tabla'])
    cuerpo = (_FORM_REQUEST
              .replace('__REGLAS__', _reglas_request(t['columnas']))
              .replace('__CN__', cn)
              .replace('__TABLA__', t['tabla']))
    return _escribir(carpeta, f'{cn}Request.php', cuerpo, autor)


# ═════════════════════════════════════════════
#  routes/api.php — completo, sin parches
# ═════════════════════════════════════════════
def _ruta_con_permiso(uri: str, ctrl: str, metodo: str, modulo: str,
                      op: str) -> str:
    return (f"    Route::post('{uri}', [{ctrl}, '{metodo}'])\n"
            f"        ->middleware(VerificarPermiso::class . ':{modulo},{op}');")


def generar_rutas(middleware: str, carpeta: str, autor: str) -> str:
    """Genera routes/api.php con auth, archivos y admin. Sin rutas de tablas
    (esas van en {mod}_api.php generados por generar_rutas_modulo())."""
    imports = sorted({
        "use App\\Http\\Controllers\\AuthController;",
        "use App\\Http\\Controllers\\ArchivoController;",
        "use App\\Http\\Middleware\\VerificarPermiso;",
        "use App\\Utils\\Parametro;",
        "use Illuminate\\Cache\\RateLimiting\\Limit;",
        "use Illuminate\\Http\\Request;",
        "use Illuminate\\Support\\Facades\\RateLimiter;",
        "use Illuminate\\Support\\Facades\\Route;",
    })

    # Archivos: la operación del permiso se administra en tbl_seg_permiso
    archivos = '\n'.join(
        _ruta_con_permiso(f'/archivos/{uri}', 'ArchivoController::class',
                          metodo, 'archivos', op)
        for uri, metodo, op in (('subir', 'subir', 'add'),
                                ('sel', 'sel', 'sel'),
                                ('descargar', 'descargar', 'get'),
                                ('del', 'eliminar', 'del')))

    # Administración: rutas de seg/* se generan en seg_api.php (ver generar_rutas_seg)

    cuerpo = f"""\
{chr(10).join(imports)}

/*
|--------------------------------------------------------------------------
| API — davgen v4.0
|--------------------------------------------------------------------------
| Auth 2FA : login → (verificar) → token · 2fa/activar|confirmar|desactivar
| Menú     : /auth/menu — módulos y permisos del rol (desde la BD)
| Archivos : subir, sel, descargar, del (por usuario, PDF y similares)
| Tablas   : ver {{mod}}_api.php — rutas por módulo cargadas en bootstrap/app.php
| Admin    : ver seg_api.php — usuarios, roles, permisos, parámetros, bitácora
|            (los DATOS viven en tbl_seg_*: ahí se administra la app)
| Anti-DoS : límites de tasa (throttle) configurables en tbl_seg_parametro
|            (rate_limit_auth, rate_limit_api) — ver bloque RateLimiter abajo
*/

// ── Límites de tasa (anti fuerza bruta / DoS) — administrables en la BD ──
// Se leen de tbl_seg_parametro en cada petición (memo por request en
// Parametro); el contador usa el store de caché (CACHE_STORE), no la BD.
RateLimiter::for('autenticacion', function (Request $request) {{
    // login / verificar / google: por IP (la sesión aún no tiene usuario)
    return Limit::perMinute(Parametro::entero('rate_limit_auth', 5))
        ->by($request->ip());
}});
RateLimiter::for('publico', function (Request $request) {{
    // rutas públicas de negocio ([opciones] publico): por IP, con cupo propio
    // para que el catálogo o el portal no compitan con el límite del login
    return Limit::perMinute(Parametro::entero('rate_limit_publico', 60))
        ->by($request->ip());
}});
RateLimiter::for('api', function (Request $request) {{
    // rutas con token: por usuario autenticado (respaldo a IP)
    return Limit::perMinute(Parametro::entero('rate_limit_api', 120))
        ->by(optional($request->user())->id ?: $request->ip());
}});

// ── Autenticación (público, con límite anti fuerza bruta) ──
Route::middleware('throttle:autenticacion')->group(function () {{
    Route::post('/auth/login',     [AuthController::class, 'login']);
    Route::post('/auth/verificar', [AuthController::class, 'verificar']);   // 2FA paso 2
    Route::post('/auth/google',    [AuthController::class, 'googleLogin']); // si google_auth_activo=1 (BD)
}});

// Config pública del front (sin token): google_auth_activo + google_client_id
Route::post('/config-publica', [AuthController::class, 'configPublica']);

Route::middleware(['{middleware}', 'throttle:api'])->group(function () {{

    // ── Sesión ──
    Route::post('/auth/logout', [AuthController::class, 'logout']);
    Route::post('/auth/me',     [AuthController::class, 'me']);
    Route::post('/auth/menu',   [AuthController::class, 'menu']);

    // ── Solicitudes de acceso (cola de aprobación Google · admin) ──
    Route::post('/accesos/pendientes', [AuthController::class, 'accesosPendientes']);
    Route::post('/accesos/aprobar',    [AuthController::class, 'accesoAprobar']);
    Route::post('/accesos/denegar',    [AuthController::class, 'accesoDenegar']);

    // ── Verificación en dos pasos ──
    Route::post('/auth/2fa/activar',    [AuthController::class, 'dosfaActivar']);
    Route::post('/auth/2fa/confirmar',  [AuthController::class, 'dosfaConfirmar']);
    Route::post('/auth/2fa/desactivar', [AuthController::class, 'dosfaDesactivar']);

    // ── Archivos por usuario (PDF, imágenes, documentos) ──
{archivos}
}});
"""
    return _escribir(carpeta, 'api.php', cuerpo, autor)


def generar_rutas_seg(middleware: str, carpeta: str, autor: str) -> str:
    """Genera routes/seg_api.php — módulo de seguridad (prefix /seg)."""
    cuerpo = f"""\
use App\\Http\\Controllers\\seg\\SegBitacoraController;
use App\\Http\\Controllers\\seg\\SegParametroController;
use App\\Http\\Controllers\\seg\\SegPermisoController;
use App\\Http\\Controllers\\seg\\SegRolController;
use App\\Http\\Controllers\\seg\\SegUsuarioController;
use App\\Http\\Middleware\\VerificarPermiso;
use Illuminate\\Support\\Facades\\Route;

Route::middleware(['{middleware}', 'throttle:api'])->prefix('seg')->group(function () {{

    // ── Usuarios ──
    Route::post('/usuarios/listar',     [SegUsuarioController::class, 'sel'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_usuario,sel');
    Route::post('/usuarios/guardar',    [SegUsuarioController::class, 'add'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_usuario,add');
    Route::post('/usuarios/actualizar', [SegUsuarioController::class, 'upd'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_usuario,upd');
    Route::post('/usuarios/reset',      [SegUsuarioController::class, 'resetPassword'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_usuario,upd');

    // ── Roles ──
    Route::post('/roles/listar',     [SegRolController::class, 'sel'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_rol,sel');
    Route::post('/roles/guardar',    [SegRolController::class, 'add'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_rol,add');
    Route::post('/roles/actualizar', [SegRolController::class, 'upd'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_rol,upd');

    // ── Permisos ──
    Route::post('/permisos/matriz',   [SegPermisoController::class, 'matriz'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_permiso,sel');
    Route::post('/permisos/guardar',  [SegPermisoController::class, 'guardar'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_permiso,upd');

    // ── Parámetros ──
    Route::post('/parametros/listar',     [SegParametroController::class, 'sel'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_parametro,sel');
    Route::post('/parametros/actualizar', [SegParametroController::class, 'upd'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_parametro,upd');

    // ── Bitácora ──
    Route::post('/bitacora/listar', [SegBitacoraController::class, 'sel'])
        ->middleware(VerificarPermiso::class . ':tbl_seg_bitacora,sel');

}});
"""
    return _escribir(carpeta, 'seg_api.php', cuerpo, autor)


def generar_rutas_modulo(tablas_mod: List[Dict], mod: str, publico: Dict,
                          middleware: str, carpeta: str, autor: str,
                          con_export: bool = False) -> str:
    """Genera routes/{mod}_api.php con las rutas del módulo.
    Rutas autenticadas con prefix /{mod}; rutas públicas fuera del grupo.
    """
    # Importar controllers del módulo
    imports = set()
    for t in tablas_mod:
        mod_t, rec = _modulo_recurso(t['tabla'])
        ctrl_class = f"{mod_t.title()}{a_clase(rec)}Controller"
        imports.add(f"use App\\Http\\Controllers\\{mod_t}\\{ctrl_class};")
    imports.add("use App\\Http\\Middleware\\VerificarPermiso;")
    imports.add("use Illuminate\\Support\\Facades\\Route;")
    imports_str = '\n'.join(sorted(imports))

    # Rutas públicas (sin token) para tablas de este módulo
    lineas_publico = []
    metodo_pub = {'sel': 'listarPublico', 'get': 'obtenerPublico', 'add': 'guardarPublico'}
    for t in tablas_mod:
        tabla = t['tabla']
        if tabla not in publico:
            continue
        mod_t, rec = _modulo_recurso(tabla)
        ctrl_class = f"{mod_t.title()}{a_clase(rec)}Controller"
        uri_rec    = _recurso_uri(rec)
        for op in publico[tabla]:
            metodo = metodo_pub.get(op)
            if not metodo:
                continue
            lineas_publico.append(
                f"    Route::post('/{mod}/{uri_rec}/{metodo}', [{ctrl_class}::class, '{metodo}']);")
    # Rutas públicas con límite anti-abuso por IP PROPIO (throttle:publico,
    # parámetro rate_limit_publico): con el del login (5/min) una tienda o un
    # portal público no podían ni listar su catálogo.
    publico_bloque = (
        "\n// ── Rutas públicas (sin token, con límite anti-abuso por IP) ──\n"
        "Route::middleware('throttle:publico')->group(function () {\n"
        + '\n'.join(lineas_publico) + "\n});\n") if lineas_publico else ''

    # Rutas autenticadas por tabla
    bloques = []
    for t in tablas_mod:
        mod_t, rec = _modulo_recurso(t['tabla'])
        ctrl_class = f"{mod_t.title()}{a_clase(rec)}Controller"
        uri_rec    = _recurso_uri(rec)
        label      = f"{mod_t.title()}{a_clase(rec)}"
        ops = [
            ('sel', 'listar'),
            ('get', 'obtener'),
            ('add', 'guardar'),
            ('upd', 'actualizar'),
            ('del', 'eliminar'),
        ]
        if con_export:
            ops.append(('sel', 'exportar'))
        rutas_t = [
            f"    Route::post('/{uri_rec}/{metodo}', [{ctrl_class}::class, '{metodo}'])\n"
            f"        ->middleware(VerificarPermiso::class . ':{t['tabla']},{op}');"
            for op, metodo in ops
        ]
        bloques.append('\n'.join([f"    // ── {label} ──"] + rutas_t))

    cuerpo = f"""\
{imports_str}
{publico_bloque}
Route::middleware(['{middleware}', 'throttle:api'])->prefix('{mod}')->group(function () {{

{chr(10).join(bloques)}
}});
"""
    return _escribir(carpeta, f'{mod}_api.php', cuerpo, autor)


def _bloque_persistentes(activas: bool) -> str:
    """Tramo de bootstrap/app.php que activa las conexiones persistentes a
    MySQL, o '' si [opciones] conexiones_persistentes = no.

    Va en bootstrap/app.php y no en config/database.php porque el despliegue
    incremental sí lleva este archivo: un proyecto ya publicado recibe el
    cambio con solo regenerar, sin tocar su configuración ni su .env."""
    if not activas:
        return ''
    return """\
    ->booting(function (): void {
        // Conexiones PERSISTENTES a MySQL. PHP abre una conexión por petición
        // y el hosting compartido limita las conexiones nuevas por hora de
        // cada usuario de la base (error 1226 «max_connections_per_hour»):
        // con pocos usuarios el sitio entero queda caído hasta la hora
        // siguiente. Reutilizarlas lo evita. Para apagarlas: DB_PERSISTENT=false
        // en el .env, o [opciones] conexiones_persistentes = no y regenerar.
        if (!filter_var(env('DB_PERSISTENT', true), FILTER_VALIDATE_BOOL)) {
            return;
        }
        foreach (['mysql', 'mariadb'] as $conexion) {
            $clave = "database.connections.{$conexion}";
            if (is_array(config($clave))) {
                // «+» conserva las demás opciones (p. ej. el certificado SSL).
                config(["{$clave}.options" => [\\PDO::ATTR_PERSISTENT => true]
                    + (array) config("{$clave}.options", [])]);
            }
        }
    })
"""


def generar_bootstrap_app(modulos: List[str], carpeta_bootstrap: str,
                          autor: str, persistentes: bool = True) -> str:
    """Genera bootstrap/app.php con then: que carga seg_api.php + {mod}_api.php."""
    todos = ['seg'] + [m for m in sorted(modulos) if m != 'seg']
    then_lineas = []
    for mod in todos:
        then_lineas.append(
            f"            \\Illuminate\\Support\\Facades\\Route::middleware('api')\n"
            f"                ->prefix('api')\n"
            f"                ->group(base_path('routes/{mod}_api.php'));")
    # Punto de extensión: todo routes/Custom/*.php se carga solo. El glob solo
    # ve lo que existe, así que un archivo que aún no se subió al servidor no
    # tumba la API (que es lo que pasaba al hacer require desde un Provider).
    then_lineas.append(
        "            // Código propio: cada routes/Custom/*.php se carga solo bajo /api.\n"
        "            // davgen nunca escribe ni borra esa carpeta.\n"
        "            foreach (glob(base_path('routes/Custom/*.php')) ?: [] as $rutasPropias) {\n"
        "                \\Illuminate\\Support\\Facades\\Route::middleware('api')\n"
        "                    ->prefix('api')\n"
        "                    ->group($rutasPropias);\n"
        "            }")
    then_bloque = '\n'.join(then_lineas)

    archivo = 'app.php'
    autor_line = f" * @author    {autor}\n" if autor else ''
    cabecera = (f"<?php\n/**\n * @generated davgen v{VERSION} | {_FECHA()}\n"
                f" * @file      bootstrap/{archivo}\n{autor_line}"
                f" * ⚠ NO MODIFICAR — regenerado por davgen v{VERSION}.\n */\n\n")

    cuerpo = cabecera + f"""\
use Illuminate\\Foundation\\Application;
use Illuminate\\Foundation\\Configuration\\Exceptions;
use Illuminate\\Foundation\\Configuration\\Middleware;
use Illuminate\\Http\\Request;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
        then: function () {{
{then_bloque}
        }},
    )
    ->withMiddleware(function (Middleware $middleware): void {{
        // Es una API: quien no trae token recibe 401 en JSON. Sin esto, una
        // petición sin «Accept: application/json» intentaba redirigir a una
        // ruta `login` que no existe y respondía 500.
        $middleware->redirectGuestsTo(fn () => null);
    }})
{_bloque_persistentes(persistentes)}    ->withExceptions(function (Exceptions $exceptions): void {{
        $exceptions->shouldRenderJsonWhen(
            fn (Request $request) => $request->is('api/*'),
        );
    }})->create();
"""
    os.makedirs(carpeta_bootstrap, exist_ok=True)
    ruta = os.path.join(carpeta_bootstrap, archivo)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(cuerpo)
    return ruta


# ═════════════════════════════════════════════
#  routes/web.php — health-check JSON en la raíz (sin vista welcome)
# ═════════════════════════════════════════════
_WEB = _plantilla('backend/rutas_web.php', __name__, '_WEB')


def generar_rutas_web(carpeta: str, nombre: str, autor: str) -> str:
    cuerpo = _WEB.replace('__NOMBRE__', nombre.replace("'", ''))
    # web.php no declara namespace propio; quitar la línea namespace del molde
    cuerpo = cuerpo.replace("namespace App\\Http\\Web;\n\n", "")
    return _escribir(carpeta, 'web.php', cuerpo, autor)


# ═════════════════════════════════════════════
#  Generación completa del backend
# ═════════════════════════════════════════════
def generar_backend(tablas: List[Dict], cfg: Dict, carpeta_backend: str) -> List[str]:
    import shutil
    autor        = cfg['autor']
    extras       = cfg.get('generar', {})
    con_requests = bool(extras.get('form_requests'))
    con_export   = bool(extras.get('export'))
    controllers  = os.path.join(carpeta_backend, 'app', 'Http', 'Controllers')
    requests_dir = os.path.join(carpeta_backend, 'app', 'Http', 'Requests')
    middleware   = os.path.join(carpeta_backend, 'app', 'Http', 'Middleware')
    modelos      = os.path.join(carpeta_backend, 'app', 'Models')
    utils        = os.path.join(carpeta_backend, 'app', 'Utils')
    services     = os.path.join(carpeta_backend, 'app', 'Services')
    rutas_dir    = os.path.join(carpeta_backend, 'routes')

    # _backendGenerado es un MIRROR de salida: limpiar lo generado antes para
    # no arrastrar controllers/services de tablas que ya no existen (al
    # regenerar con menos tablas o sin tablas de negocio).
    for d in (os.path.join(carpeta_backend, 'app'), rutas_dir):
        shutil.rmtree(d, ignore_errors=True)

    extensiones = ', '.join(f"'{e}'" for e in cfg['extensiones_archivo'])
    archivo_php = (_ARCHIVO
                   .replace('__EXTENSIONES__', extensiones)
                   .replace('__MAX_MB__', str(cfg['max_archivo_mb'])))

    # 1 · base + SERVICIOS (validan auth normal + 2FA en cada operación)
    generados = [
        _escribir(utils, 'PaginationUtil.php', _PAGINACION, autor),
        _escribir(utils, 'Totp.php', _TOTP, autor),
        _escribir(utils, 'Parametro.php', _PARAMETRO, autor),
        _escribir(utils, 'Retencion.php', _RETENCION.replace(
            '__DIAS_BITACORA__',
            str(int(cfg.get('legal', {}).get('retencion_bitacora_dias', 365)))), autor),
        _escribir(middleware, 'VerificarPermiso.php', _VERIFICAR_PERMISO, autor),
        _escribir(modelos, 'User.php', _USER, autor),
        _escribir(services, 'ExcepcionServicio.php', _EXCEPCION_SERVICIO, autor),
        _escribir(services, 'BaseService.php', _SERVICE_BASE, autor),
    ]
    generados += [generar_service_tabla(t, services, autor) for t in tablas]

    # 2 · CONTROLLERS (delgados: delegan en los servicios)
    generados += [
        _escribir(controllers, 'BaseController.php', _BASE, autor),
        _escribir(controllers, 'AuthController.php', _AUTH, autor),
        _escribir(controllers, 'ArchivoController.php', archivo_php, autor),
    ]
    carpeta_seg = os.path.join(controllers, 'seg')
    generados += [
        _escribir(carpeta_seg, 'SegUsuarioController.php', _SEG_USUARIO, autor),
        _escribir(carpeta_seg, 'SegRolController.php', _SEG_ROL, autor),
        _escribir(carpeta_seg, 'SegPermisoController.php', _SEG_PERMISO, autor),
        _escribir(carpeta_seg, 'SegParametroController.php', _SEG_PARAMETRO, autor),
        _escribir(carpeta_seg, 'SegBitacoraController.php', _SEG_BITACORA, autor),
    ]
    # Agrupar tablas por módulo y crear controllers en subcarpeta {mod}/
    tablas_por_mod = defaultdict(list)
    for t in tablas:
        mod, _ = _modulo_recurso(t['tabla'])
        tablas_por_mod[mod].append(t)
    generados += [generar_controller_tabla(t, controllers, autor,
                                           con_requests=con_requests,
                                           con_export=con_export)
                  for t in tablas]

    # 2b · FormRequests opcionales (validación 422 derivada del esquema)
    if con_requests:
        generados += [generar_form_request(t, requests_dir, autor) for t in tablas]

    # 3 · API: routes/api.php (auth+archivos) + seg_api.php + {mod}_api.php
    #          + web.php + bootstrap/app.php con then: por módulo
    generados.append(generar_rutas(cfg['middleware'], rutas_dir, autor))
    generados.append(generar_rutas_seg(cfg['middleware'], rutas_dir, autor))
    for mod, tablas_mod in sorted(tablas_por_mod.items()):
        generados.append(generar_rutas_modulo(
            tablas_mod, mod, cfg['publico'], cfg['middleware'],
            rutas_dir, autor, con_export=con_export))
    generados.append(generar_rutas_web(rutas_dir, cfg['nombre'], autor))

    # 4 · bootstrap/app.php — carga los {mod}_api.php vía then:
    carpeta_bootstrap = os.path.join(carpeta_backend, 'bootstrap')
    generados.append(generar_bootstrap_app(
        list(tablas_por_mod.keys()), carpeta_bootstrap, autor,
        persistentes=cfg.get('conexiones_persistentes', True)))

    return generados
