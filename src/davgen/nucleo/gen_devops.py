"""
gen_devops.py — extras de automatización OPCIONALES.

- generar_ci()      → .github/workflows/ci.yml  ([generar] ci=si): corre
  `php artisan test`, build del frontend y `davgen verificar` (rompe el build
  si el código generado fue editado a mano).
- generar_openapi() → openapi.json + swagger.html  ([generar] openapi=si):
  especificación OpenAPI 3 derivada del esquema + visor Swagger UI (CDN).
"""
import json
import os
from typing import Dict, List

from .esquema import a_clase
from .gen_sql import cols_parametro
from .version import VERSION


# ═════════════════════════════════════════════
#  CI — GitHub Actions
# ═════════════════════════════════════════════
def generar_ci(raiz: str, laravel_rel: str, front_rel, autor: str) -> str:
    """Escribe {raiz}/.github/workflows/ci.yml. laravel_rel y front_rel son
    rutas relativas (con /) a la raíz del repo; front_rel puede ser None."""
    laravel_rel = (laravel_rel or '.').replace('\\', '/')
    front_block = ''
    if front_rel:
        front_rel = front_rel.replace('\\', '/')
        front_block = f"""
  frontend:
    name: Frontend (build)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: {front_rel}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run build --if-present
      - run: npm test --if-present
"""

    contenido = f"""\
# .github/workflows/ci.yml — GENERADO por davgen v{VERSION} ({autor})
# NO editar a mano: se regenera. CI del sistema generado.
name: CI

on:
  push:
    branches: [main, master]
  pull_request:

jobs:
  backend:
    name: Backend (php artisan test)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: {laravel_rel}
    steps:
      - uses: actions/checkout@v4
      - name: Setup PHP
        uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
          extensions: pdo_mysql, mbstring, bcmath
      - name: Instalar dependencias
        run: composer install --no-interaction --prefer-dist --no-progress
      - name: Preparar entorno
        run: |
          cp .env.example .env || true
          php artisan key:generate
      - name: Ejecutar pruebas
        run: php artisan test
{front_block}
  integridad:
    name: Integridad del codigo generado (davgen verificar)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Instalar davgen {VERSION}
        run: pip install "davgen=={VERSION}"
      - name: davgen verificar
        run: davgen verificar
"""
    carpeta = os.path.join(raiz, '.github', 'workflows')
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, 'ci.yml')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(contenido)
    return ruta


# ═════════════════════════════════════════════
#  OpenAPI 3 + Swagger UI
# ═════════════════════════════════════════════
def _tipo_openapi(c: Dict) -> Dict:
    dt = c['DATA_TYPE'].lower()
    if dt in ('bigint', 'int', 'smallint', 'mediumint', 'tinyint', 'year'):
        return {'type': 'integer'}
    if dt in ('decimal', 'float', 'double'):
        return {'type': 'number'}
    if dt == 'date':
        return {'type': 'string', 'format': 'date'}
    if dt in ('datetime', 'timestamp'):
        return {'type': 'string', 'format': 'date-time'}
    if dt == 'enum' and c.get('ENUM_VALS'):
        return {'type': 'string', 'enum': list(c['ENUM_VALS'])}
    return {'type': 'string'}


def _body(schema_ref: str) -> Dict:
    return {'required': True, 'content': {
        'application/json': {'schema': {'$ref': schema_ref}}}}


def _resp_ok() -> Dict:
    return {'200': {'description': 'OK — envelope { mensaje, info }'},
            '401': {'description': 'No autenticado'},
            '422': {'description': 'Validación'}}


def generar_openapi(tablas: List[Dict], cfg: Dict, carpeta: str) -> List[str]:
    """Escribe openapi.json + swagger.html en `carpeta`. Devuelve sus rutas."""
    servers = [{'url': 'http://localhost:8000/api', 'description': 'Local'}]
    url = (cfg.get('ftp') or {}).get('url')
    if url:
        servers.insert(0, {'url': url.rstrip('/') + '/servicio/api',
                           'description': 'Nube'})

    paths = {
        '/auth/login': {'post': {'tags': ['Auth'], 'summary': 'Login (paso 1)',
            'requestBody': _body('#/components/schemas/Login'),
            'responses': {'200': {'description': 'token o requiere_2fa'},
                          '401': {'description': 'Credenciales'}}}},
        '/auth/verificar': {'post': {'tags': ['Auth'], 'summary': '2FA (paso 2)',
            'responses': _resp_ok()}},
        '/auth/me': {'post': {'tags': ['Auth'], 'summary': 'Usuario actual',
            'security': [{'bearerAuth': []}], 'responses': _resp_ok()}},
        '/auth/menu': {'post': {'tags': ['Auth'], 'summary': 'Menú del rol',
            'security': [{'bearerAuth': []}], 'responses': _resp_ok()}},
    }
    schemas = {
        'Login': {'type': 'object', 'required': ['email', 'password'],
                  'properties': {'email': {'type': 'string', 'format': 'email'},
                                 'password': {'type': 'string'}}},
    }

    for t in tablas:
        cn = a_clase(t['tabla'])
        tabla = t['tabla']
        pk = next((c['COLUMN_NAME'] for c in t['columnas']
                   if c['COLUMN_KEY'] == 'PRI'), 'id')
        props = {f"p{c['COLUMN_NAME']}": _tipo_openapi(c)
                 for c in cols_parametro(t['columnas'])}
        schemas[f'{cn}Input'] = {'type': 'object', 'properties': props}
        ref = f'#/components/schemas/{cn}Input'
        seg = [{'bearerAuth': []}]
        paths[f'/{tabla}/sel'] = {'post': {'tags': [cn], 'summary': f'Listar {cn}',
            'security': seg, 'requestBody': {'content': {'application/json': {'schema': {
                'type': 'object', 'properties': {
                    'page': {'type': 'integer'}, 'per_page': {'type': 'integer'},
                    'filters': {'type': 'array', 'items': {'type': 'object'}}}}}}},
            'responses': _resp_ok()}}
        paths[f'/{tabla}/get'] = {'post': {'tags': [cn], 'summary': f'Obtener {cn}',
            'security': seg, 'requestBody': {'content': {'application/json': {'schema': {
                'type': 'object', 'properties': {f'p{pk}': {'type': 'integer'}}}}}},
            'responses': _resp_ok()}}
        paths[f'/{tabla}/add'] = {'post': {'tags': [cn], 'summary': f'Crear {cn}',
            'security': seg, 'requestBody': _body(ref), 'responses': _resp_ok()}}
        paths[f'/{tabla}/upd'] = {'post': {'tags': [cn], 'summary': f'Actualizar {cn}',
            'security': seg, 'requestBody': _body(ref), 'responses': _resp_ok()}}
        paths[f'/{tabla}/del'] = {'post': {'tags': [cn], 'summary': f'Baja {cn}',
            'security': seg, 'requestBody': {'content': {'application/json': {'schema': {
                'type': 'object', 'properties': {f'p{pk}': {'type': 'integer'}}}}}},
            'responses': _resp_ok()}}
        if (cfg.get('generar') or {}).get('export'):
            paths[f'/{tabla}/export'] = {'post': {'tags': [cn],
                'summary': f'Exportar {cn} a CSV', 'security': seg,
                'responses': {'200': {'description': 'CSV', 'content': {'text/csv': {}}}}}}

    spec = {
        'openapi': '3.0.3',
        'info': {'title': f"{cfg['nombre']} — API", 'version': VERSION,
                 'description': 'Generado por davgen. Todas las operaciones son '
                                'POST; envelope { mensaje, info } / { error:{text} }.'},
        'servers': servers,
        'components': {
            'securitySchemes': {'bearerAuth': {'type': 'http', 'scheme': 'bearer'}},
            'schemas': schemas,
        },
        'paths': paths,
    }

    os.makedirs(carpeta, exist_ok=True)
    ruta_json = os.path.join(carpeta, 'openapi.json')
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(spec, f, indent=1, ensure_ascii=False)

    html = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>API — Swagger UI</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css">
</head>
<body>
  <div id="swagger"></div>
  <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => SwaggerUIBundle({ url: './openapi.json', dom_id: '#swagger' })
  </script>
</body>
</html>
"""
    ruta_html = os.path.join(carpeta, 'swagger.html')
    with open(ruta_html, 'w', encoding='utf-8') as f:
        f.write(html)
    return [ruta_json, ruta_html]
