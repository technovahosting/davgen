# Pruebas generadas (PHPUnit)

> ⚠ Generadas por davgen — **NO editar** los archivos de esta carpeta ni de
> `tests/Datos/`. Las pruebas propias van en otros archivos de `tests/`.

Ejecutar todo:

```bash
php artisan test
```

Solo las generadas:

```bash
php artisan test --testsuite=Feature --filter=Generados
```

## Qué cubren (sin sembrar datos de negocio)

| Test | Verifica |
|---|---|
| `AuthTest` | login sin datos → 422, credenciales malas → 401, ruta protegida sin token → 401 |
| `RutasTest` | cada tabla expone su ruta y exige token (401, no 404) |
| `RateLimitTest` | `/auth/login` aplica el límite de tasa (429) |

No usan `RefreshDatabase`: el esquema de negocio lo crean los scripts SQL y los
SPs `pcru*`, no migraciones. Cada test hace `Cache::flush()` en `setUp` para
reiniciar los contadores de rate-limit.

## Necesitan la BD MySQL (con `tbl_seg_*`)

El límite de tasa y el login leen `tbl_seg_parametro`, así que estas pruebas
requieren una BD MySQL con el esquema. Si el entorno de test por defecto usa
`sqlite :memory:`, los tests se **omiten** (no fallan). Para ejecutarlos contra
MySQL, apunta las variables `DB_*` a tu BD de pruebas:

```bash
# PowerShell (ejemplo con la BD de desarrollo)
$env:DB_CONNECTION='mysql'; $env:DB_DATABASE='pedidos'; $env:DB_USERNAME='root'
php artisan test --filter=Generados
```

o configura una conexión MySQL de testing en `phpunit.xml`.

## Pruebas de CRUD (a escribir por ti)

Para el camino feliz necesitas un usuario autenticado y datos válidos. Usa los
helpers `Tests\Datos\{Entidad}Datos::ejemplo()` como punto de partida:

```php
$token = /* login del admin sembrado */;
$payload = \Tests\Datos\ProductoDatos::ejemplo();
$this->withToken($token)->postJson('/api/tbl_inv_producto/add', $payload)
     ->assertStatus(200);
```
