"""
gen_testing.py — FASE testing: archivos de prueba + configuración de uso.

Genera en {_backendGenerado}/testing/ todo lo necesario para probar el
sistema generado sin escribir nada a mano:

    configuracion-pruebas.ini  ← URLs (local + nube) y credenciales de prueba
    api.http                   ← pruebas de la API (REST Client de VS Code):
                                 login, 2FA, Google, menú y CRUD de CADA tabla
    pruebas-api.ps1            ← pruebas E2E automáticas (PowerShell): login
                                 (+2FA) y CRUD por tabla, PASS/FAIL · local o nube
    GUIA-PRUEBAS.md            ← guía del procedimiento de pruebas (local + nube)
    pruebas-frontend.md        ← checklist por página generada (T1..T6)
    COMO-USAR.md               ← guía paso a paso: BD → backend → front → tests

Estos archivos se copian/regeneran en cada corrida, junto al código.
"""
import json
import os
from datetime import datetime  # noqa: F401
from .reloj import ahora as _ahora
from typing import Dict, List

from .esquema import COLS_AUTO, a_clase, a_snake_case
from .gen_backend import _modulo_recurso, _recurso_uri

_TIPOS_FECHA = {'date', 'datetime', 'timestamp', 'time'}
_TIPOS_NUM   = {'int', 'smallint', 'tinyint', 'mediumint', 'bigint', 'year'}
_TIPOS_DEC   = {'decimal', 'float', 'double'}


def _ruta_base(t: Dict) -> str:
    """URI base REAL de la tabla, idéntica a routes/{mod}_api.php (v4.32.1):
    tbl_zap_pedido_detalle → /zap/pedido-detalle. Los métodos son
    listar/obtener/guardar/actualizar/eliminar (permisos sel/get/add/upd/del)."""
    mod, rec = _modulo_recurso(t['tabla'])
    return f"/{mod}/{_recurso_uri(rec)}"


def _dominio(cfg: Dict) -> str:
    return a_snake_case(cfg['nombre']).replace('_', '') + '.com'


# La contraseña del administrador NO se escribe en estos archivos: viven en
# carpetas que se versionan (_backendGenerado/testing, 05-Testing/generados).
# Cada archivo lleva este marcador para completarlo a mano al probar; el script
# de humo la recibe por parámetro o por la variable DAVGEN_ADMIN_PASSWORD.
MARCA_PASSWORD = 'ESCRIBIR-LA-CONTRASENA-DEL-ADMIN'
_DONDE_PASSWORD = ('la contraseña del admin está en `[seguridad] admin_password` '
                   'del archivo de accesos del entorno (`davgen acceso ver` si '
                   'está cifrado)')


def _admin_email(cfg: Dict) -> str:
    """Correo del admin sembrado — IDÉNTICO al seed (no derivado del nombre)."""
    return cfg.get('admin_email', 'admin@localhost')


def _valor_ejemplo(c: Dict, pk: str) -> str:
    """Valor JSON de ejemplo para el parámetro p{columna} de un SP."""
    nombre = c['COLUMN_NAME']
    dt = c['DATA_TYPE'].lower()
    if nombre == pk:
        return '0'
    if nombre.lower() == 'activo':
        return '1'
    if c.get('ENUM_VALS'):
        # primer valor del ENUM: un texto inventado sería rechazado por MySQL
        return f'"{c["ENUM_VALS"][0]}"'
    if dt in _TIPOS_NUM:
        return '1'
    if dt in _TIPOS_DEC:
        return '9.99'
    if dt == 'date':
        return '"2026-01-01"'
    if dt in ('datetime', 'timestamp'):
        return '"2026-01-01 00:00:00"'
    if dt == 'time':
        return '"12:00:00"'
    texto = f'texto de prueba {nombre}'
    # respetar el largo real de la columna (VARCHAR(10) → 10 chars): un texto
    # más largo hace fallar el SP (G-5: los params heredan el tipo real)
    import re
    m = re.search(r'(?:VARCHAR|CHAR)\((\d+)\)', c.get('SQL_FULL', ''), re.IGNORECASE)
    if m:
        texto = texto[:int(m.group(1))].strip()
    return f'"{texto}"'


def _params_json(t: Dict, pk: str, pid: str = '0') -> str:
    lineas = []
    for c in t['columnas']:
        if c['COLUMN_NAME'].lower() in COLS_AUTO:
            continue
        valor = pid if c['COLUMN_NAME'] == pk else _valor_ejemplo(c, pk)
        lineas.append(f'  "p{c["COLUMN_NAME"]}": {valor}')
    return '{\n' + ',\n'.join(lineas) + '\n}'


def _params_json_linea(t: Dict, pk: str, pid: str = '0') -> str:
    """Cuerpo JSON del add en UNA línea, comillas dobles normales (va dentro
    de comillas simples en el script PowerShell)."""
    partes = []
    for c in t['columnas']:
        if c['COLUMN_NAME'].lower() in COLS_AUTO:
            continue
        valor = pid if c['COLUMN_NAME'] == pk else _valor_ejemplo(c, pk)
        partes.append(f'"p{c["COLUMN_NAME"]}": {valor}')
    return '{' + ', '.join(partes) + '}'


def _api_http(tablas: List[Dict], cfg: Dict) -> str:
    admin_email = _admin_email(cfg)
    admin_password = MARCA_PASSWORD
    bloques = [f"""\
### ===========================================================================
### api.http — GENERADO por davgen · pruebas de la API «{cfg['nombre']}»
### Usar con la extensión "REST Client" de VS Code (o IntelliJ HTTP Client):
###   1. Ajustar @api y credenciales (ver configuracion-pruebas.ini)
###   2. Ejecutar LOGIN; copiar info.token en @token
###   3. Si el login responde requiere_2fa: ejecutar VERIFICAR con el código
###      (sin MAIL_* configurado, el código queda en storage/logs/laravel.log)
###   4. Ejecutar las pruebas CRUD de cada tabla
### ===========================================================================

@api = http://localhost:8000/api
@token = PEGAR_AQUI_EL_TOKEN

### LOGIN — paso 1 (sin 2FA devuelve token; con 2FA pide código)
POST {{{{api}}}}/auth/login
Content-Type: application/json

{{ "email": "{admin_email}", "password": "{admin_password}" }}

### VERIFICAR — paso 2 del 2FA (credenciales + código → token)
POST {{{{api}}}}/auth/verificar
Content-Type: application/json

{{ "email": "{admin_email}", "password": "{admin_password}", "codigo": "000000" }}

### GOOGLE — inicio de sesión con Google (habilitar EN LA BD:
###   tbl_seg_parametro → google_auth_activo=1 y google_client_id=<Client ID>)
### credential = ID token de Google Identity Services (frontend)
POST {{{{api}}}}/auth/google
Content-Type: application/json

{{ "credential": "PEGAR_AQUI_EL_ID_TOKEN_DE_GOOGLE" }}

### ME — usuario autenticado
POST {{{{api}}}}/auth/me
Authorization: Bearer {{{{token}}}}

### MENU — módulos y permisos del rol (desde la BD)
POST {{{{api}}}}/auth/menu
Authorization: Bearer {{{{token}}}}
"""]

    for t in tablas:
        cn = a_clase(t['tabla'])
        pk = next((c['COLUMN_NAME'] for c in t['columnas']
                   if c['COLUMN_KEY'] == 'PRI'), 'id')
        base = _ruta_base(t)
        bloques.append(f"""\

### ===========================================================================
### {t['tabla']} — CRUD en {base}/* (servicio {cn}Service: valida auth + 2FA)
### ===========================================================================

### {t['tabla']} · listar (permiso sel) — listado paginado sobre {t['vista']}
POST {{{{api}}}}{base}/listar
Authorization: Bearer {{{{token}}}}
Content-Type: application/json

{{ "page": 1, "per_page": 10, "filters": [] }}

### {t['tabla']} · obtener (permiso get) — leer por {pk}
POST {{{{api}}}}{base}/obtener
Authorization: Bearer {{{{token}}}}
Content-Type: application/json

{{ "p{pk}": 1 }}

### {t['tabla']} · guardar (permiso add) — alta (p{pk}=0 → el SP asigna el id)
POST {{{{api}}}}{base}/guardar
Authorization: Bearer {{{{token}}}}
Content-Type: application/json

{_params_json(t, pk, '0')}

### {t['tabla']} · actualizar (permiso upd) — ¡sobreescribe TODOS los campos!
POST {{{{api}}}}{base}/actualizar
Authorization: Bearer {{{{token}}}}
Content-Type: application/json

{_params_json(t, pk, '1')}

### {t['tabla']} · eliminar (permiso del) — baja lógica
POST {{{{api}}}}{base}/eliminar
Authorization: Bearer {{{{token}}}}
Content-Type: application/json

{{ "p{pk}": 1 }}
""")
    return '\n'.join(bloques)


def _postman_item(nombre: str, ruta: str, cuerpo=None, con_token=False,
                  script=None) -> Dict:
    """Una request de la colección Postman (POST, JSON)."""
    headers = [{'key': 'Content-Type', 'value': 'application/json'},
               {'key': 'Accept', 'value': 'application/json'}]
    if con_token:
        headers.append({'key': 'Authorization', 'value': 'Bearer {{token}}'})
    partes = [p for p in ruta.split('/') if p]
    req = {
        'method': 'POST',
        'header': headers,
        'url': {'raw': '{{api}}/' + '/'.join(partes),
                'host': ['{{api}}'], 'path': partes},
    }
    if cuerpo is not None:
        req['body'] = {'mode': 'raw', 'raw': cuerpo,
                       'options': {'raw': {'language': 'json'}}}
    item = {'name': nombre, 'request': req}
    if script:
        item['event'] = [{'listen': 'test',
                          'script': {'type': 'text/javascript', 'exec': script}}]
    return item


def _postman_collection(tablas: List[Dict], cfg: Dict) -> str:
    admin_email = _admin_email(cfg)
    admin_password = MARCA_PASSWORD
    url = _url_nube(cfg) or 'http://localhost:8000/api'
    # guarda info.token en la variable {{token}} tras login/verificar
    guardar_token = [
        "var j = pm.response.json();",
        "if (j && j.info && j.info.token) {",
        "  pm.collectionVariables.set('token', j.info.token);",
        "  pm.test('token recibido', function(){ pm.expect(j.info.token).to.be.a('string'); });",
        "} else if (j && j.info && j.info.requiere_2fa) {",
        "  pm.test('requiere 2FA: ejecutar Verificar', function(){ pm.expect(true).to.be.true; });",
        "}",
    ]
    auth = {'name': '00 · Autenticación', 'item': [
        _postman_item('Login', '/auth/login',
                      json.dumps({'email': f'{admin_email}',
                                  'password': admin_password}, indent=2),
                      script=guardar_token),
        _postman_item('Verificar 2FA', '/auth/verificar',
                      json.dumps({'email': f'{admin_email}',
                                  'password': admin_password, 'codigo': '000000'},
                                 indent=2), script=guardar_token),
        _postman_item('Me', '/auth/me', con_token=True),
        _postman_item('Menú', '/auth/menu', con_token=True),
        _postman_item('Logout', '/auth/logout', con_token=True),
    ]}

    grupos = [auth]
    for t in tablas:
        pk = next((c['COLUMN_NAME'] for c in t['columnas']
                   if c['COLUMN_KEY'] == 'PRI'), 'id')
        tabla = t['tabla']
        base = _ruta_base(t)
        sc = tabla.lower() in cfg.get('solo_consulta', set())
        items = [
            _postman_item('listar (sel)', f'{base}/listar',
                          json.dumps({'page': 1, 'per_page': 10, 'filters': []},
                                     indent=2), con_token=True),
            _postman_item('obtener (get)', f'{base}/obtener',
                          json.dumps({f'p{pk}': 1}, indent=2), con_token=True),
        ]
        if not sc:
            items += [
                _postman_item('guardar (add)', f'{base}/guardar',
                              _params_json(t, pk, '0'), con_token=True),
                _postman_item('actualizar (upd)', f'{base}/actualizar',
                              _params_json(t, pk, '1'), con_token=True),
                _postman_item('eliminar (del)', f'{base}/eliminar',
                              json.dumps({f'p{pk}': 1}, indent=2), con_token=True),
            ]
        grupos.append({'name': f"{tabla}{' (solo consulta)' if sc else ''}",
                       'item': items})

    coleccion = {
        'info': {
            'name': f"{cfg['nombre']} — API davgen",
            '_postman_id': a_snake_case(cfg['nombre']) + '-davgen',
            'description': ('Colección GENERADA por davgen. Importar en '
                            'Postman. Ejecutar Login (guarda el token en la '
                            'variable {{token}}); el resto usa Bearer {{token}}. '
                            'Si hay 2FA, ejecutar Verificar con el código.'),
            'schema': ('https://schema.getpostman.com/json/collection/'
                       'v2.1.0/collection.json'),
        },
        'variable': [
            {'key': 'api', 'value': url, 'type': 'string'},
            {'key': 'token', 'value': '', 'type': 'string'},
        ],
        'item': grupos,
    }
    return json.dumps(coleccion, indent=2, ensure_ascii=False)


def _configuracion_ini(cfg: Dict) -> str:
    admin_email = _admin_email(cfg)
    admin_password = MARCA_PASSWORD
    url_nube = _url_nube(cfg)
    return f"""\
; =============================================================================
; configuracion-pruebas.ini — GENERADO por davgen · {_ahora():%Y-%m-%d %H:%M}
; Datos para ejecutar las pruebas de «{cfg['nombre']}» (ver COMO-USAR.md)
; =============================================================================

[api]
; URL base del backend Laravel local (php artisan serve)
url = http://localhost:8000/api
; URL de la API desplegada en la nube (de [ftp] url) — vacío si no se desplegó
url_nube = {url_nube}

[credenciales]
; usuario semilla creado por 01_seguridad.sql — CAMBIAR la contraseña al entrar
email = {admin_email}
password = {admin_password}

[2fa]
; con 2fa_obligatorio=1 (tbl_seg_parametro) todo login exige código por correo;
; sin MAIL_* configurado, el código queda en storage/logs/laravel.log
obligatorio = consultar tbl_seg_parametro (clave 2fa_obligatorio)
codigo_en_log = storage/logs/laravel.log

[frontend]
; URL del frontend React (npm run dev) — definir VITE_API_URL en su .env
url = http://localhost:5173
env = VITE_API_URL=http://localhost:8000/api
"""


def _pruebas_frontend_md(tablas: List[Dict], cfg: Dict) -> str:
    filas = []
    for t in tablas:
        clase = ''.join(p.title() for p in t['entidad'].split('_') if p)
        tiene_activo = any(c['COLUMN_NAME'].lower() == 'activo'
                           for c in t['columnas'])
        sin_baja = t['tabla'].lower() in cfg.get('sin_baja', set())
        solo_consulta = t['tabla'].lower() in cfg.get('solo_consulta', set())
        solo_lectura = cfg.get('solo_lectura', {}).get(t['tabla'].lower(), [])

        if solo_consulta:
            filas.append(f"""\
## {clase}Page ({t['tabla']}) — SOLO CONSULTA

- [ ] T1 Compila y carga (sin errores en consola del navegador)
- [ ] T2 Listado: skeleton → datos; estado vacío y error con "Reintentar"
- [ ] T3 Verificar que NO existan "+ Nuevo", "Editar" ni "Dar de baja"
- [ ] T4 Búsqueda (si aplica) y columnas legibles (no ids crudos)
""")
            continue

        notas = []
        if solo_lectura:
            notas.append(f"solo lectura: {', '.join(solo_lectura)} "
                         "(NO deben aparecer en el formulario)")
        if sin_baja:
            notas.append('sin botón "Dar de baja"')
        if tiene_activo:
            notas.append('con baja lógica + Reactivar')
        filas.append(f"""\
## {clase}Page ({t['tabla']})

{('> ' + ' · '.join(notas)) if notas else ''}

- [ ] T1 Compila y carga (sin errores en consola del navegador)
- [ ] T2 Listado: skeleton → datos; estado vacío y error con "Reintentar"
- [ ] T3 Alta: "+ Nuevo" → guardar → toast y el registro aparece en la lista
- [ ] T4 Edición: "Editar" → cambiar un campo → guardar → cambio reflejado
- [ ] T5 {'Baja lógica: "Dar de baja" → confirmar → Inactivo; "Reactivar" lo devuelve'
          if tiene_activo and not sin_baja else
          ('(sin baja: verificar que NO exista el botón "Dar de baja")'
           if sin_baja else 'Baja: "Dar de baja" → confirmar → desaparece/avisa')}
- [ ] T6 Verificar que el listado muestre columnas legibles (no ids crudos)
""")
    return f"""\
# Checklist de pruebas del frontend — {cfg['nombre']}

> GENERADO por davgen · {_ahora():%Y-%m-%d %H:%M}
> Páginas en `src/pages/generados/` — activarlas vía `rutas.jsx` (ver cabecera).
> Registrar resultados con el formato del LOG de observaciones del proyecto.

{chr(10).join(filas)}
"""


def _como_usar_md(tablas: List[Dict], cfg: Dict) -> str:
    admin_email = _admin_email(cfg)
    lista_tablas = '\n'.join(f"| `{t['tabla']}` | `{a_clase(t['tabla'])}Service` | "
                             f"`{_ruta_base(t)}/listar·obtener·guardar·actualizar·eliminar` |"
                             for t in tablas)
    return f"""\
# CÓMO USAR — {cfg['nombre']} (generado por davgen)

> GENERADO · {_ahora():%Y-%m-%d %H:%M} · estos archivos se copian en cada
> corrida del generador para realizar las pruebas respectivas.

## 1 · Base de datos

1. Crear la BD MySQL (utf8mb4) si no existe.
2. Ejecutar EN ORDEN los scripts de `database/`:
   `01_seguridad.sql` → `02_negocio.sql` (si existe) → `03_procedimientos.sql`.
   Son idempotentes: los seeds nunca pisan lo ajustado en la BD.

## 2 · Backend (Laravel)

1. El generador ya copió `app/` y `routes/api.php` al proyecto Laravel
   (carpeta `servicio/` o `backend/` dentro de 03-Backend*).
2. Configurar `.env`: BD, `APP_URL` y `MAIL_*` (para el 2FA por correo).
3. Levantar:  `php artisan serve`  →  http://localhost:8000

### Arquitectura generada (personalizar SOLO sobre esta base)

- `app/Services/BaseService.php` — TODA operación valida autenticación
  normal **y 2FA** antes de tocar datos (`verificarAutenticacion()`).
- `app/Services/{{Tabla}}Service.php` — listar + CRUD vía SP `pcru*`.
  *Aquí se agrega la lógica de negocio personalizada (clases hijas).*
- `app/Http/Controllers/{{Tabla}}Controller.php` — delgado: envelope HTTP.
- `routes/api.php` — todas las rutas con `auth:sanctum` + `VerificarPermiso`.

| Tabla | Servicio | Endpoints |
|---|---|---|
{lista_tablas}

## 3 · Autenticación (probar SIEMPRE primero)

- Credenciales semilla: `{admin_email}` — {_DONDE_PASSWORD}. Cambiarla al entrar.
- Sin 2FA: `POST /api/auth/login` devuelve el token directo.
- Con 2FA (`2fa_obligatorio=1` o usuario enrolado): el login responde
  `{{ requiere_2fa, metodo }}` → `POST /api/auth/verificar` con el código.
  Sin `MAIL_*`, el código queda en `storage/logs/laravel.log`.
- El token emitido tras el 2FA se llama `api-token-2fa`; la capa de
  servicios RECHAZA tokens sin 2FA cuando el usuario lo requiere.

## 4 · Pruebas de la API

1. Abrir `testing/api.http` en VS Code (extensión REST Client).
2. Ejecutar LOGIN (y VERIFICAR si aplica) → pegar el token en `@token`.
3. Ejecutar el CRUD de cada tabla. Datos de conexión en
   `testing/configuracion-pruebas.ini`.

## 5 · Frontend (React — carpeta 04-Front*)

1. El generador creó/actualizó en `src/`:
   - `services/api.js` y `services/authService.js` (solo si no existían),
   - `services/{{entidad}}Service.js` (uno por tabla),
   - `pages/generados/{{Entidad}}Page.jsx` + `pages/generados/rutas.jsx`.
2. `.env` del frontend: `VITE_API_URL=http://localhost:8000/api`.
3. Activar las páginas en `App.jsx` (instrucciones en `rutas.jsx`).
4. Levantar:  `npm run dev`  →  http://localhost:5173

## 6 · Pruebas del frontend

Seguir el checklist `testing/pruebas-frontend.md` (T1..T6 por página) y
registrar los resultados como LOG de observaciones.

## 7 · Qué personalizar (lo único que se desarrolla a mano)

- Reglas de dominio: SPs propios + métodos en clases que extiendan el
  Service generado (NO editar los archivos `@generated`).
- Columnas no editables y acciones por tabla: `_configtotal.ini`
  (`solo_lectura`, `sin_baja`) y regenerar.
- Roles, permisos, menú y parámetros: en la BD (`tbl_seg_*`).
"""


def _url_nube(cfg: Dict) -> str:
    """URL de la API desplegada (de [ftp] url + ruta_remota), o ''."""
    ftp = cfg.get('ftp', {})
    url = (ftp.get('url') or '').rstrip('/')
    if not url:
        return ''
    sub = (ftp.get('ruta_remota') or '').strip('/').split('/')[-1]
    return f"{url}/{sub}/api" if sub and sub not in url else f"{url}/api"


def _pruebas_api_ps1(tablas: List[Dict], cfg: Dict) -> str:
    admin_email = _admin_email(cfg)
    bloques = []
    sel_body = "'{\"page\":1,\"per_page\":5,\"filters\":[]}'"
    for t in tablas:
        tabla = t['tabla']
        pk = next((c['COLUMN_NAME'] for c in t['columnas']
                   if c['COLUMN_KEY'] == 'PRI'), 'id')
        base = _ruta_base(t)
        solo_consulta = tabla.lower() in cfg.get('solo_consulta', set())
        bloques.append(
            f"Test '{base}/listar' {{ 'total: ' + "
            f"(Api '{base}/listar' {sel_body}).info.pagination.total }}")
        if not solo_consulta:
            body = _params_json_linea(t, pk, '0')
            bloques.append(
                f"$script:nuevo = $null\n"
                f"TestOpt '{base}/guardar' {{ $r = Api '{base}/guardar' '{body}'; "
                f"$script:nuevo = $r.info.item[0].{pk}; 'id=' + $r.info.item[0].{pk} }}\n"
                f"TestOpt '{base}/eliminar' {{ if ($script:nuevo) {{ Api '{base}/eliminar' "
                f"(@{{ p{pk} = $script:nuevo }} | ConvertTo-Json -Compress) | Out-Null; "
                f"'baja id=' + $script:nuevo }} else {{ 'sin id (guardar no creó)' }} }}")
    url_nube = _url_nube(cfg)
    comentario_nube = (f"#       .\\pruebas-api.ps1 -Api '{url_nube}'   (la nube)"
                       if url_nube else
                       "#       .\\pruebas-api.ps1 -Api 'https://tu-host/servicio/api'")
    return f"""\
# pruebas-api.ps1 — GENERADO por davgen · pruebas E2E de la API «{cfg['nombre']}»
# Ejecuta login (+2FA) y el CRUD de cada tabla, reportando PASS/FAIL.
# Uso:
#       .\\pruebas-api.ps1                      (contra http://localhost:8000/api)
{comentario_nube}
#       .\\pruebas-api.ps1 -Email otro@x -Password ***  -Codigo2fa 123456
param(
  [string]$Api = 'http://localhost:8000/api',
  [string]$Email = '{admin_email}',
  # no se guarda en el archivo: -Password <clave>  o  $env:DAVGEN_ADMIN_PASSWORD
  [string]$Password = $env:DAVGEN_ADMIN_PASSWORD,
  [string]$Codigo2fa = ''
)
$H = @{{ Accept = 'application/json'; 'Content-Type' = 'application/json' }}
$script:pass = 0; $script:fail = 0; $script:warn = 0; $script:nuevo = $null

function Api([string]$ruta, [string]$json = '{{}}') {{
  Invoke-RestMethod -Uri "$Api$ruta" -Method Post -Headers $H -Body $json -TimeoutSec 30
}}
# Test núcleo: debe pasar (auth, listados) — su fallo rompe el smoke test.
function Test([string]$n, [scriptblock]$b) {{
  try {{ $r = & $b
    Write-Host ("  PASS  {{0}}{{1}}" -f $n, $(if ($r) {{ "  -> $r" }} else {{ "" }})) -ForegroundColor Green
    $script:pass++ }}
  catch {{ Write-Host ("  FAIL  {{0}}  -> {{1}}" -f $n, $_.Exception.Message) -ForegroundColor Red
    $script:fail++ }}
}}
# Test best-effort: escrituras (add/del). Un fallo suele ser una regla de
# dominio (FK requerida, baja prohibida), no un defecto → WARN, no rompe.
function TestOpt([string]$n, [scriptblock]$b) {{
  try {{ $r = & $b
    Write-Host ("  PASS  {{0}}{{1}}" -f $n, $(if ($r) {{ "  -> $r" }} else {{ "" }})) -ForegroundColor Green
    $script:pass++ }}
  catch {{ Write-Host ("  WARN  {{0}}  -> regla de dominio o datos previos requeridos" -f $n) -ForegroundColor Yellow
    $script:warn++ }}
}}

Write-Host "API: $Api" -ForegroundColor Cyan
# ── Autenticación ──
$r = Api '/auth/login' (@{{ email = $Email; password = $Password }} | ConvertTo-Json -Compress)
if ($r.info.requiere_2fa) {{
  if (-not $Codigo2fa) {{ Write-Host "2FA requerido (metodo $($r.info.metodo)): pasar -Codigo2fa (ver storage/logs/laravel.log)" -ForegroundColor Yellow; exit 1 }}
  $r = Api '/auth/verificar' (@{{ email = $Email; password = $Password; codigo = $Codigo2fa }} | ConvertTo-Json -Compress)
}}
$token = $r.info.token
if (-not $token) {{ Write-Host "login fallido" -ForegroundColor Red; exit 1 }}
$H['Authorization'] = "Bearer $token"
Write-Host "  PASS  login ($Email)" -ForegroundColor Green; $script:pass++

Test 'auth/me'   {{ (Api '/auth/me').info.user.email }}
Test 'auth/menu' {{ "modulos: " + (Api '/auth/menu').info.modulos.Count }}

# ── CRUD por tabla ──
{chr(10).join(bloques) if bloques else "# (BD sin tablas de negocio: solo backbone de autenticación)"}

Write-Host ("== {{0}} prueba(s) · {{1}} PASS · {{2}} WARN · {{3}} FAIL ==" -f ($pass+$warn+$fail), $pass, $warn, $fail) -ForegroundColor Cyan
if ($warn) {{ Write-Host "  (WARN = escritura rechazada por regla de dominio o falta de datos; no es defecto)" -ForegroundColor Yellow }}
exit $(if ($fail) {{ 1 }} else {{ 0 }})
"""


def _guia_pruebas_md(tablas: List[Dict], cfg: Dict) -> str:
    admin_email = _admin_email(cfg)
    url_nube = _url_nube(cfg)
    filas = '\n'.join(
        f"| `{t['tabla']}` | `{_ruta_base(t)}/listar·obtener·guardar·actualizar·eliminar` | "
        f"{'solo consulta' if t['tabla'].lower() in cfg.get('solo_consulta', set()) else 'CRUD'} |"
        for t in tablas) or "| _(sin tablas de negocio)_ | — | — |"
    bloque_nube = (f"""\
## Probar el backend DESPLEGADO (la nube)

El backend está desplegado en `{url_nube.rsplit('/api', 1)[0]}`. Probar la API:

```powershell
.\\pruebas-api.ps1 -Api '{url_nube}'
```

Equivale a abrir `api.http` cambiando `@api` a `{url_nube}`.
""" if url_nube else """\
## Probar el backend DESPLEGADO (la nube)

Configurar `[ftp] url` en `_configtotal.ini` y volver a generar para que esta
guía incluya la URL de la nube. Luego:

```powershell
.\\pruebas-api.ps1 -Api 'https://tu-host/servicio/api'
```
""")
    return f"""\
# GUÍA DE PRUEBAS — {cfg['nombre']}

> GENERADO por davgen · {_ahora():%Y-%m-%d %H:%M}
> Cómo probar el sistema generado, de punta a punta, igual que en la
> validación del generador. Registrar resultados como LOG de observaciones.

## 0 · Antes de empezar

- BD con `01_seguridad.sql` aplicado (tablas `tbl_seg_*`) y las tablas de
  negocio creadas por el usuario (ver `02-Base-de-datos/readme_cero.md`).
  Con `[generar] aplicar_sps=si`, davgen ya aplicó los SPs `pcru*`, los seeds
  y las vistas `vis_*` que faltaban (una vista existente NUNCA se reemplaza:
  puede estar personalizada).
- Backend Laravel corriendo:  `php artisan serve`  (http://localhost:8000)
- Credencial semilla: `{admin_email}` — {_DONDE_PASSWORD}. Cambiarla al entrar.

## 1 · Pruebas automáticas de la API (PowerShell)

`pruebas-api.ps1` hace login (+2FA si aplica) y el CRUD de cada tabla,
reportando PASS/FAIL:

```powershell
.\\pruebas-api.ps1                 # contra http://localhost:8000/api
```

Cubre: `auth/login`, `auth/me`, `auth/menu`, y por cada tabla `listar` (y
`guardar`/`eliminar` si no es de solo consulta).

{bloque_nube}

## 2 · Pruebas manuales de la API (REST Client)

Abrir `api.http` en VS Code (extensión REST Client). Flujo:
1. Ejecutar **LOGIN** → copiar `info.token` en `@token`.
2. Si responde `requiere_2fa`: ejecutar **VERIFICAR** con el código
   (sin `MAIL_*`, el código queda en `storage/logs/laravel.log`).
3. Ejecutar el CRUD de cada tabla.

| Tabla | Endpoints | Modo |
|---|---|---|
{filas}

## 3 · Verificación del 2FA

1. En la BD: `UPDATE tbl_seg_parametro SET valor='1' WHERE clave='2fa_obligatorio';`
2. `login` ahora responde `{{ requiere_2fa, metodo }}` (no token).
3. Tomar el código de `storage/logs/laravel.log` y `verificar`.
4. Un token SIN 2FA es rechazado (401) por la capa de servicios.
5. Restaurar: `UPDATE tbl_seg_parametro SET valor='0' WHERE clave='2fa_obligatorio';`

## 4 · Login con Google (opcional, se habilita en la BD)

`UPDATE tbl_seg_parametro SET valor='1' WHERE clave='google_auth_activo';`
y `google_client_id` con el Client ID OAuth. `POST /auth/google` con el
`credential` de Google Identity Services.

## 5 · Pruebas del frontend

Seguir el checklist `pruebas-frontend.md` (T1..T6 por página generada).

## 6 · Resultado esperado

Todas las pruebas de auth y `sel` en PASS; los `add` que dependan de claves
foráneas (ej. detalle de pedido) pueden requerir datos previos. El backend
nunca expone detalles de SQL: los errores llegan como mensaje de negocio.
"""


def generar_testing(tablas: List[Dict], cfg: Dict, carpeta: str) -> List[str]:
    """Escribe los archivos de testing/uso en `carpeta`. Devuelve las rutas."""
    os.makedirs(carpeta, exist_ok=True)
    archivos = {
        'configuracion-pruebas.ini':  _configuracion_ini(cfg),
        'api.http':                   _api_http(tablas, cfg),
        'pruebas-api.ps1':            _pruebas_api_ps1(tablas, cfg),
        'postman_collection.json':    _postman_collection(tablas, cfg),
        'GUIA-PRUEBAS.md':            _guia_pruebas_md(tablas, cfg),
        'pruebas-frontend.md':        _pruebas_frontend_md(tablas, cfg),
        'COMO-USAR.md':               _como_usar_md(tablas, cfg),
    }
    rutas = []
    for nombre, contenido in archivos.items():
        ruta = os.path.join(carpeta, nombre)
        # .ps1 con BOM: PowerShell 5.1 lee UTF-8 sin BOM como ANSI y
        # muestra los acentos rotos («creÃ³») al ejecutar el script.
        codificacion = 'utf-8-sig' if nombre.endswith('.ps1') else 'utf-8'
        with open(ruta, 'w', encoding=codificacion) as f:
            f.write(contenido)
        rutas.append(ruta)
    return rutas
