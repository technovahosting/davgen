# README CERO — Base de datos del proyecto (davgen v{version})

> GENERADO por davgen · {fecha} · se regenera en cada corrida.

## ⚠ PASO OBLIGATORIO — ejecutar `00-seguridad.sql` en la BD (UNA SOLA VEZ)

**Antes de correr `davgen generar` debes ejecutar `00-seguridad.sql` en tu
base de datos UNA SOLA VEZ** (al preparar la BD del proyecto). Crea las tablas
`tbl_seg_*` (login, 2FA, roles, módulos, permisos, parámetros, bitácora,
archivos): son el backbone de seguridad sin el cual el sistema no funciona.

> ℹ️ **Se ejecuta una sola vez.** Una vez creadas las `tbl_seg_*`, NO hace
> falta volver a correrlo en cada generación. (El script es idempotente
> —`CREATE TABLE IF NOT EXISTS`— así que re-ejecutarlo no rompe nada, pero no
> es necesario.)

> 🚫 **Si esas tablas NO existen en la BD, davgen DETIENE la generación** y te
> pide ejecutar este script.

Cómo ejecutarlo (ejemplo): `mysql -u USUARIO -p NOMBRE_BD < 00-seguridad.sql`
o pégalo en tu cliente (phpMyAdmin, HeidiSQL, DBeaver…).

## `00-seguridad.sql` — seguridad del sistema (NO crear otras tablas de este tipo)

El archivo **`00-seguridad.sql`** tiene las **tablas y vistas de la parte de
seguridad que controlan el login del usuario**: autenticación (normal,
2FA y Google), tokens, roles, módulos, permisos, parámetros, bitácora y
archivos (`tbl_seg_*`, `personal_access_tokens` y sus vistas `vis_seg_*`).

**Por lo cual NO se deben crear otras tablas de seguridad**: ese esquema ya
cubre todo el acceso al sistema, lo genera davgen y se administra en la
propia base de datos (editar datos en `tbl_seg_*`, nunca su estructura).

## Qué tablas SÍ puede crear el usuario

La generación/creación de tablas debe ser **particularmente de la
aplicación** — ejemplo: tablas de un sistema contable, activos fijos,
inventarios, ventas, pedidos…

- ✅ El usuario **podrá crear tablas de negocio** (convención
  `tbl_{{modulo}}_*`, con `id` PK, `activo` para baja lógica y
  `created_at`/`updated_at`): al regenerar, davgen les crea vista, SP
  `pcru*`, servicio, controller, API y página automáticamente.
- ❌ El usuario **NO deberá crear tablas de autenticación o de acceso al
  sistema** (usuarios, roles, permisos, sesiones, tokens, logins…):
  para eso ya existen las `tbl_seg_*` de `00-seguridad.sql`.

## Orden de ejecución de los scripts

1. `00-seguridad.sql` — seguridad — **UNA SOLA VEZ** al preparar la BD
   (idempotente; re-ejecutarlo es seguro pero innecesario).
2. Scripts de tablas/vistas/SPs del NEGOCIO de esta carpeta o de
   `03-Backend/_backendGenerado/database/`.

## 🕒 Zona horaria — las fechas se guardan en UTC

Los scripts fijan `SET time_zone = '+00:00'` y los SP usan `NOW()`, de modo que
`created_at`/`updated_at` se almacenan en **UTC**. Ejemplo: un registro creado a
las 15:05 en Bolivia (UTC-4) queda con `created_at = 19:05`. Es intencional
(estándar para servidores). **La aplicación debe convertir a hora local al
mostrar** (o ajusta `time_zone` en tu conexión/servidor si prefieres hora local).
