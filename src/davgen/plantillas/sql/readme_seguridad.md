# README — SEGURIDAD Y AUTENTICACIÓN (davgen v{version})

> ⚠ **CÓDIGO Y ESQUEMA GENÉRICOS DEL GENERADOR — NADIE DEBE MODIFICARLOS.**
> Se regeneran completos en cada corrida de davgen: cualquier cambio manual
> se PIERDE. La administración (usuarios, roles, permisos, parámetros) se
> hace en la BASE DE DATOS o desde el módulo Administración del portal.
> La lógica propia del proyecto va en clases que EXTIENDEN los servicios
> generados (`app/Services/`), nunca dentro de ellos.

## Tablas de autenticación — creación OBLIGATORIA

En temas de autenticación es **OBLIGATORIO** crear estas tablas ANTES de
usar el backend: sin ellas no hay login, ni 2FA, ni permisos, ni auditoría.
Todas las crea `database/01_seguridad.sql`, que viene **incluido por
defecto** al generar el backend. El script es idempotente
(`CREATE TABLE IF NOT EXISTS` + seeds que nunca pisan lo ajustado en la
BD): ejecutarlo en cada despliegue es seguro.

| # | Tabla | Rol en la autenticación |
|---|---|---|
| 1 | `tbl_seg_usuario` | Usuarios: email, password (bcrypt), rol, método 2FA (`ninguno`/`correo`/`app`), secreto TOTP, activo |
| 2 | `personal_access_tokens` | Tokens Bearer de Sanctum. El nombre del token registra si la sesión superó el 2FA (`api-token-2fa`) — la capa de servicios lo exige |
| 3 | `tbl_seg_codigo_verificacion` | Códigos 2FA por correo (hash SHA-256, vigencia configurable, un solo uso) |
| 4 | `tbl_seg_token_reset` | Tokens de restablecimiento de contraseña |
| 5 | `tbl_seg_rol` | Roles; `es_admin=1` da acceso total (ignora la matriz de permisos) |
| 6 | `tbl_seg_modulo` | Módulos del menú: clave, título, orden, visible, activo |
| 7 | `tbl_seg_permiso` | Matriz rol × módulo × operación (`sel/get/add/upd/del`) — la valida el middleware `VerificarPermiso` en cada ruta |
| 8 | `tbl_seg_parametro` | Parámetros runtime: `2fa_obligatorio`, `sesion_unica`, `codigo_2fa_minutos`, `bitacora_activa`, `google_auth_activo`, `google_client_id`, `rate_limit_auth`/`rate_limit_api` (anti-DoS), tamaño/extensiones de archivos |
| 9 | `tbl_seg_bitacora` | Auditoría de logins y escrituras exitosas (solo lectura) |
| 10 | `tbl_seg_archivo` | Archivos subidos por usuario (PDF, imágenes…) con validación de tipo y tamaño |

## Cómo se usan (flujo)

1. `POST /api/auth/login` valida credenciales contra `tbl_seg_usuario`.
2. Si el usuario tiene 2FA (o `2fa_obligatorio=1` en `tbl_seg_parametro`),
   se exige código (correo → `tbl_seg_codigo_verificacion`, o app TOTP) en
   `POST /api/auth/verificar`; el token queda en `personal_access_tokens`.
3. **Google (opcional, se habilita EN LA BD)**: con `google_auth_activo=1`
   y `google_client_id` configurado en `tbl_seg_parametro`,
   `POST /api/auth/google` recibe el ID token de Google Identity Services,
   lo verifica contra Google (firma/vigencia/audiencia) y emite el token
   de la API para el usuario YA registrado con ese email (cuenta como
   verificación fuerte). Con `google_auth_activo=0` el endpoint responde 403.
4. Cada ruta CRUD pasa por `auth:sanctum` + `VerificarPermiso`
   (`tbl_seg_permiso`) y además la capa de servicios (`BaseService`)
   re-valida autenticación normal **y 2FA** antes de tocar datos.
5. Las escrituras exitosas quedan en `tbl_seg_bitacora`.

## Código genérico protegido (NO tocar — viene incluido al generar el backend)

| Archivo | Función |
|---|---|
| `app/Services/BaseService.php` + `{{Tabla}}Service.php` | Validación auth+2FA en cada operación; listar/CRUD |
| `app/Http/Controllers/AuthController.php` | Login, 2FA (correo/TOTP), menú, logout |
| `app/Http/Controllers/Seg*Controller.php` | Administración (usuarios, roles, permisos, parámetros, bitácora) |
| `app/Http/Middleware/VerificarPermiso.php` | Permisos por BD + bitácora de escrituras |
| `app/Models/User.php` · `app/Utils/*` | Modelo de usuario (tbl_seg_usuario), TOTP, parámetros, paginación |
| `routes/api.php` | Todas las rutas de la API |

Credencial semilla: `{admin_email}` / la de `[seguridad] admin_password` — **cambiarla al primer
ingreso**. Generado: {fecha}.
