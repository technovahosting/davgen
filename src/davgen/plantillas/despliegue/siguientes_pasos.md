## Siguientes pasos

1. **Para una BD NUEVA** (o si `[generar] aplicar_sps=no`): crear la base de
   datos MySQL (utf8mb4) y ejecutar EN ORDEN los scripts de
   `03-Backend/_backendGenerado/database/`: `01_seguridad.sql` →
   `02_negocio.sql` → `03_procedimientos.sql`. Son idempotentes: al agregar
   tablas, regenerar y volver a ejecutarlos — los seeds NUNCA pisan lo que el
   administrador haya ajustado en la BD.
   _(Si `aplicar_sps=si`, davgen YA aplicó los `pcru*` en la BD configurada;
   estos scripts solo hacen falta para desplegar a OTRA base de datos.)_
2. Entrar con `admin_email` (de `_configtotal.ini`) y la `admin_password` que escribiste en `_acceso.produccion.ini` y
   CAMBIAR la contraseña.
3. El backend se genera en `03-Backend/_backendGenerado/backend/`;
   copiarlo sobre el proyecto Laravel (`03-Backend/backend/`, requiere
   Sanctum) y configurar `.env` (BD, `MAIL_*` para 2FA por correo, APP_URL).
4. Administrar la aplicación DESDE LA BD (o desde el módulo
   Administración del portal): roles y permisos en `tbl_seg_rol` /
   `tbl_seg_permiso`, menú en `tbl_seg_modulo`, parámetros en
   `tbl_seg_parametro`. El código generado NO se edita.
5. **(OPCIONAL) Habilitar inicio de sesión con Google**: seguir la guía
   `CONFIGURAR-GOOGLE-AUTH.md` (raíz del proyecto) — crear el Client ID en
   Google Cloud, activar `google_auth_activo`/`google_client_id` en
   `tbl_seg_parametro` e integrar el botón en el frontend. Sin regenerar código.
