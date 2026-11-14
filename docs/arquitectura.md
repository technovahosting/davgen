# Arquitectura

Dos arquitecturas conviven aquí y conviene no mezclarlas: la del **generador**
(este repositorio, Python) y la del **sistema generado** (Laravel + React +
MySQL, en el proyecto del usuario).

## 1 · El generador

```text
src/davgen/
├── cli.py                 comandos y orquestación (pasos 0..10 de `generar`)
├── nucleo/
│   ├── version.py         VERSION — única fuente (pyproject la lee de aquí)
│   ├── configuracion.py   _configtotal.ini: carga, validación, ejemplo sin secretos
│   ├── entrada.py         mockup (HTML / TSX / bundle) o BD → entidades
│   ├── esquema.py         entidades → tablas normalizadas (tipos, FK, orden)
│   ├── plantillas.py      resolución de plantillas: proyecto → paquete
│   ├── bd.py              ÚNICO punto de conexión a MySQL (PyMySQL)
│   ├── reloj.py           fecha de los sellos (SOURCE_DATE_EPOCH → reproducible)
│   ├── consola.py         salida con color
│   ├── gen_sql.py         01_seguridad, 02_negocio, 03_procedimientos + aplicar en BD
│   ├── gen_backend.py     Laravel: services, controllers, rutas, bootstrap
│   ├── gen_servicios.py   React: api.js, services, páginas CRUD, rutas.jsx
│   ├── gen_google.py      React: botón de Google + cola de aprobación
│   ├── gen_componentes.py React: hooks y componentes reutilizables (extra)
│   ├── gen_pruebas.py     PHPUnit (extra)
│   ├── gen_testing.py     api.http, Postman, script de humo, guías de prueba
│   ├── gen_devops.py      OpenAPI + Swagger UI, workflow de CI (extras)
│   ├── gen_prompts.py     prompts de IA por fase
│   ├── gen_plantillas.py  documentos del proyecto (requisitos, guía, leeme)
│   └── resumen.py         registro, manifiestos, verificar/comparar, FTP
└── plantillas/            los archivos que se generan, como DATOS
    ├── backend/  frontend/  google/  componentes/  sql/
    └── documentos/  prompts/  pruebas/  despliegue/  proyecto/
```

### Flujo de `davgen generar`

```text
_configtotal.ini ─► configuracion.cargar ─► cfg
                                             │
mockup / BD ─► entrada ─► esquema ─► tablas ─┤
                                             ▼
        ┌──────────── generadores (cada uno: tablas + cfg + plantillas → archivos)
        │   gen_sql → gen_backend → gen_servicios → gen_google → gen_testing → …
        ▼
03-Backend/_backendGenerado/          ← ESPEJO: todo lo generado, verificable
        │  copia
        ├─► 03-Backend/servicio|backend/   (proyecto Laravel real)
        ├─► 04-Front*/frontend/src/        (proyecto React real)
        ├─► 02-Base*/  y  05-Test*/generados/
        │
        └─► acciones que salen del proyecto (solo si están activas y confirmadas)
              aplicar_sps → BD      produccion → FTP      front → FTP
```

Tres reglas sostienen el diseño:

1. **Todo lo generado pasa por el espejo.** `_backendGenerado/` es la copia de
   referencia: contra ella trabajan `verificar` (¿se editó algo a mano?),
   `comparar` (¿qué?) y el despliegue incremental (¿qué cambió desde la última
   subida?). Con `--local` y sin proyecto Laravel/React, el espejo *es* el
   resultado.
2. **Lo que sale del proyecto es explícito.** Escribir en la base o subir por
   FTP son «acciones», separadas de «generar archivos»: se muestran con su
   destino real, se confirman, y `--local` las apaga todas.
3. **Las plantillas son datos.** Ver [plantillas.md](plantillas.md).

### Puntos de aislamiento (lo que hace posible probarlo)

| Dependencia externa | Dónde se aísla | En las pruebas |
|---|---|---|
| Base de datos | `nucleo/bd.py` (`conectar`) | `bd.usar_fabrica(doble)` |
| Reloj | `nucleo/reloj.py` | `SOURCE_DATE_EPOCH` fijo |
| Composer / npm / FTP | solo se invocan fuera de `--local` | no se ejecutan |
| Carpeta de trabajo | todo parte de `os.getcwd()` | `tmp_path` |
| Abrir archivos con el SO | `cli._abrir_archivo` | `DAVGEN_NO_ABRIR=1` |

Lo que todavía **no** está cubierto por pruebas automáticas, porque necesita
servicios reales: la subida por FTP en sí (sí se prueba qué archivos elige),
la creación del proyecto con `composer`/`npm`, y `leer_bd` contra un MySQL
real. Ver «Pendientes» en [CHANGELOG.md](../CHANGELOG.md).

## 2 · El sistema generado

```text
Navegador ── React (SPA)                         raíz del sitio
               │  POST JSON + Bearer token
               ▼
           /servicio/api ── Laravel
               │   routes/api.php              auth, límites de tasa
               │   routes/seg_api.php          administración (tbl_seg_*)
               │   routes/{mod}_api.php        una por módulo de negocio
               │   routes/Custom/*.php         ← TUYO (se carga solo)
               │
               │   Controller (delgado) ─► Service ─► CALL pcru<Tabla>(?, …)
               │        │                    │
               │   VerificarPermiso      BaseService (auth + 2FA)
               ▼
            MySQL / MariaDB
               tbl_seg_*      usuarios, roles, permisos, menú, parámetros, bitácora
               tbl_{mod}_*    tablas de negocio      vis_{mod}_*   vistas de listado
               pcru<Tabla>    un SP por tabla: C · R · U · D (baja lógica)
```

Decisiones que la definen:

- **La administración vive en la base de datos.** Roles, permisos, menú,
  segundo factor, límites de tasa y Google se cambian en `tbl_seg_*` sin
  recompilar ni redesplegar.
- **La escritura pasa por procedimientos almacenados** con parámetros
  enlazados; los listados salen de vistas con filtros validados contra una
  lista blanca. No hay SQL armado con texto del usuario.
- **Un contrato único de respuesta**: `{ "mensaje", "info": { "item",
  "pagination" } }` y, en error, `{ "error": { "text" } }`.
- **Pensado para hosting compartido**: sesión y caché en archivos, sin colas,
  `public/` aplanado bajo `/servicio`, despliegue por FTP con delta.
- **Fechas en UTC** en la base; la aplicación convierte al mostrar.

### Código propio

El código generado lleva la cabecera `@generated davgen` y **no se edita**: se
regenera. Lo propio del negocio va aparte, y davgen lo reconoce justamente
porque *no* lleva esa cabecera:

| Qué | Dónde | Notas |
|---|---|---|
| Rutas propias | `routes/Custom/*.php` | Se cargan solas bajo `/api`; no hay que registrarlas |
| Controllers y services propios | `app/**/Custom/` (o cualquier carpeta tuya bajo `app/`) | Pueden extender los generados: `class X extends TblVenPedidoService` |
| SPs de dominio | prefijo `pag_{mod}_*` | davgen solo toca los `pcru*` |
| Pantallas propias | `src/pages/` (fuera de `generados/`), `src/components/` | `App.jsx`, `api.js` y `authService.js` se escriben una sola vez |
| Aspecto de lo generado | `_plantillas/` | [plantillas.md](plantillas.md) |
| Roles, permisos, menú, parámetros | tablas `tbl_seg_*` | Sin tocar código |

El despliegue incremental sube **todo** PHP propio de `app/` y `routes/` (más
`bootstrap/providers.php`), esté en la carpeta que esté, y nunca lo borra del
servidor por no encontrarlo en local.

### Contratos que conviene conocer

- Los parámetros de la API llevan prefijo `p` (`pnombre`, `pid`): es el nombre
  del parámetro del SP.
- `actualizar` **sobrescribe todas las columnas**: se envía el registro
  completo (el formulario generado ya lo hace).
- El orden de los parámetros del SP es el orden de las columnas en la tabla.
  Tras un `ALTER TABLE` hay que regenerar SP, controller y service juntos.
- La API exige `Accept: application/json`.
