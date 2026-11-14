"""
gen_pruebas.py — suite de pruebas PHP OPCIONAL ([generar] tests=si).

Genera tests de Feature (PHPUnit, ejecutables con `php artisan test` sin
dependencias extra) que cubren la capa de seguridad sin depender de datos de
negocio sembrados:
  - AuthTest      : login 422/401, ruta protegida sin token → 401
  - RutasTest     : cada tabla exige token (401) y su ruta existe (no 404)
  - RateLimitTest : /auth/login aplica el límite de tasa (429)
Y, por tabla, un helper de DATOS de ejemplo (Tests\\Datos\\{Cn}Datos) con un
payload listo para escribir tests de CRUD propios (NO es un seeder).

Cada test hace Cache::flush() en setUp para reiniciar los contadores de
rate-limit y no contaminarse entre sí. No usan RefreshDatabase (el esquema de
negocio lo crean los scripts SQL + SPs, no migraciones).
"""
import os
import shutil
from datetime import datetime  # noqa: F401
from .reloj import ahora as _ahora
from typing import Dict, List

from .esquema import a_clase
from .gen_sql import cols_parametro
from .version import VERSION
from .plantillas import cargar as _plantilla

_FECHA = lambda: _ahora().strftime('%Y-%m-%d %H:%M')  # noqa: E731


def _cab(archivo: str, autor: str) -> str:
    autor_line = f" * @author    {autor}\n" if autor else ''
    return (f"<?php\n/**\n * @generated davgen v{VERSION} | {_FECHA()}\n"
            f" * @file      {archivo}\n{autor_line}"
            f" * ⚠ NO MODIFICAR — regenerado por davgen. Las pruebas propias\n"
            f" * van en OTROS archivos (fuera de tests/Feature/Generados).\n */\n\n")


def _escribir(carpeta: str, nombre: str, cuerpo: str, autor: str) -> str:
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(_cab(nombre, autor) + cuerpo)
    return ruta


_SETUP = _plantilla('pruebas/setup.php', __name__, '_SETUP')


def _auth_test(carpeta: str, autor: str) -> str:
    cuerpo = f"""\
namespace Tests\\Feature\\Generados;

use Tests\\TestCase;

class AuthTest extends TestCase
{{
{_SETUP}
    public function test_login_requiere_credenciales(): void
    {{
        $this->postJson('/api/auth/login', [])->assertStatus(422);
    }}

    public function test_login_credenciales_invalidas(): void
    {{
        $this->postJson('/api/auth/login', [
            'email'    => 'no-existe@example.com',
            'password' => 'contrasena-mala',
        ])->assertStatus(401);
    }}

    public function test_ruta_protegida_sin_token(): void
    {{
        // sin token y con Accept: application/json debe ser 401 (no 500)
        $this->postJson('/api/auth/me')->assertStatus(401);
    }}
}}
"""
    return _escribir(carpeta, 'AuthTest.php', cuerpo, autor)


def _rutas_test(carpeta: str, tablas: List[Dict], autor: str) -> str:
    metodos = []
    for t in tablas:
        tabla = t['tabla']
        metodos.append(f"""\
    public function test_{tabla}_sel_requiere_token(): void
    {{
        // la ruta existe y está protegida: sin token responde 401 (no 404)
        $this->postJson('/api/{tabla}/sel')->assertStatus(401);
    }}
""")
    cuerpo_metodos = '\n'.join(metodos) if metodos else \
        "    public function test_sin_tablas_de_negocio(): void\n" \
        "    {\n        $this->assertTrue(true);\n    }\n"
    cuerpo = f"""\
namespace Tests\\Feature\\Generados;

use Tests\\TestCase;

class RutasTest extends TestCase
{{
{_SETUP}
{cuerpo_metodos}}}
"""
    return _escribir(carpeta, 'RutasTest.php', cuerpo, autor)


def _ratelimit_test(carpeta: str, autor: str) -> str:
    cuerpo = f"""\
namespace Tests\\Feature\\Generados;

use Tests\\TestCase;

class RateLimitTest extends TestCase
{{
{_SETUP}
    public function test_login_aplica_limite_de_tasa(): void
    {{
        // rate_limit_auth (tbl_seg_parametro) limita /auth/login por IP.
        // Tras superarlo debe responder 429. Se prueba hasta 40 intentos.
        $excedido = false;
        for ($i = 0; $i < 40; $i++) {{
            $r = $this->postJson('/api/auth/login', [
                'email'    => 'flood@example.com',
                'password' => 'x',
            ]);
            if ($r->status() === 429) {{ $excedido = true; break; }}
        }}
        $this->assertTrue($excedido, 'No se aplicó el límite de tasa en /auth/login');
    }}
}}
"""
    return _escribir(carpeta, 'RateLimitTest.php', cuerpo, autor)


_FAKE = {
    'bigint': '1', 'int': '1', 'smallint': '1', 'mediumint': '1',
    'tinyint': '1', 'year': '2025', 'decimal': '9.99', 'float': '9.99',
    'double': '9.99', 'date': "'2025-01-01'", 'datetime': "'2025-01-01 00:00:00'",
    'timestamp': "'2025-01-01 00:00:00'", 'time': "'12:00:00'",
}


def _valor_fake(c: Dict) -> str:
    nombre = c['COLUMN_NAME'].lower()
    dt = c['DATA_TYPE'].lower()
    if c['COLUMN_KEY'] == 'PRI':
        return '0'   # 0 = alta (el SP calcula el id)
    if dt == 'tinyint' and 'TINYINT(1)' in c['SQL_FULL'].upper():
        return '1'
    if nombre.endswith(('email', 'correo', 'mail')):
        return "'demo@example.com'"
    if dt == 'enum' and c.get('ENUM_VALS'):
        return f"'{c['ENUM_VALS'][0]}'"
    return _FAKE.get(dt, "'texto'")


def _datos_tabla(carpeta: str, t: Dict, autor: str) -> str:
    cn = a_clase(t['tabla'])
    lineas = [f"            'p{c['COLUMN_NAME']}' => {_valor_fake(c)},"
              for c in cols_parametro(t['columnas'])]
    cuerpo = f"""\
namespace Tests\\Datos;

/**
 * Payload de EJEMPLO para {t['tabla']} (claves p{{columna}}, como las espera
 * el controller). Ajustar los valores reales antes de probar el alta —las FK
 * deben existir en la BD—. NO es un seeder ni una factory de Eloquent.
 */
class {cn}Datos
{{
    public static function ejemplo(): array
    {{
        return [
{chr(10).join(lineas)}
        ];
    }}
}}
"""
    return _escribir(carpeta, f'{cn}Datos.php', cuerpo, autor)


_README = _plantilla('pruebas/readme.md', __name__, '_README')


def generar_pruebas(tablas: List[Dict], cfg: Dict, carpeta_backend: str) -> List[str]:
    """Genera la suite PHPUnit en {carpeta_backend}/tests. carpeta_backend es el
    mirror del Laravel (_backendGenerado/backend); luego se copia a servicio/."""
    autor = cfg['autor']
    tests = os.path.join(carpeta_backend, 'tests', 'Feature', 'Generados')
    datos = os.path.join(carpeta_backend, 'tests', 'Datos')
    # limpiar lo generado antes (no arrastrar tests de tablas que ya no existen)
    for d in (tests, datos):
        shutil.rmtree(d, ignore_errors=True)

    generados = [
        _auth_test(tests, autor),
        _rutas_test(tests, tablas, autor),
        _ratelimit_test(tests, autor),
    ]
    generados += [_datos_tabla(datos, t, autor) for t in tablas]
    os.makedirs(tests, exist_ok=True)
    ruta_readme = os.path.join(tests, 'LEEME.md')
    with open(ruta_readme, 'w', encoding='utf-8') as f:
        f.write(_README)
    generados.append(ruta_readme)
    return generados
