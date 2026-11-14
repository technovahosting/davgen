# ⚠ NO MODIFICAR ESTA CARPETA — código GENERADO por davgen

Todo archivo de esta carpeta se REEMPLAZA al regenerar (`davgen generar`
o `davgen sincronizar`): cualquier edición manual SE PIERDE (queda una
copia en `_backendGenerado\_respaldo-ediciones\`, pero no vuelve al código).

## Dónde personalizar SIN perder trabajo

- **Backend**: clases NUEVAS que extienden los Services generados (ej. en
  `app\Services\Custom\`) y stored procedures de dominio `pag_*` en la BD.
- **Frontend**: páginas NUEVAS fuera de `pages\generados\` y el ruteo/menú
  en `App.jsx` (ese archivo SÍ es del usuario).
- **Comportamiento**: en la BASE DE DATOS — menú en `tbl_seg_modulo`,
  permisos en `tbl_seg_permiso`, parámetros en `tbl_seg_parametro`.

Ver `_prompts\prompt-4-personalizacion.md` para pedirle esto a una IA.
