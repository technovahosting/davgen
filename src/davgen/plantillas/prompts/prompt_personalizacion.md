# Prompt — personalizar el sistema SIN editar el código generado

> Uso: pegar en la IA cuando se necesite lógica o pantallas a medida.
> Regla de oro del proyecto: el código generado NO se edita (se regenera
> y se pierde); la personalización se hace EXTENDIENDO.

---

# Rol
Eres un desarrollador full-stack Laravel + React. Implementa la
funcionalidad que te describo al final SIN modificar ningún archivo
generado por davgen, respetando estas reglas del proyecto:

# Reglas OBLIGATORIAS
1. NUNCA editar: `app\Services\*`, `app\Http\Controllers\*`,
   `app\Http\Middleware\VerificarPermiso.php`, `routes\api.php`,
   `routes\web.php`, `src\services\{entidad}Service.js` ni
   `src\pages\generados\*` — se REEMPLAZAN al regenerar.
2. Backend a medida: crear NUEVAS clases (ej: en `app\Services\Custom\`)
   que EXTIENDAN los services generados, y/o stored procedures de dominio
   `pag_*` en la BD (ver prompt de SPs de dominio).
3. Frontend a medida: páginas nuevas en `src\pages\` (FUERA de
   `generados\`) y el ruteo/menú en `App.jsx`, que SÍ es del usuario.
   Reutilizar los services generados (`import ... from '../services/...'`).
4. La administración es POR BASE DE DATOS: menú en `tbl_seg_modulo`,
   permisos en `tbl_seg_permiso`, comportamiento runtime en
   `tbl_seg_parametro`. No hardcodear roles ni flags en el código.
5. La API exige header `Accept: application/json` y token Bearer; las
   respuestas usan el envelope
   `{ "mensaje": "...", "info": { "item": [...], "pagination": {...} } }`.
6. Código y mensajes en español, siguiendo el estilo del proyecto.

# Funcionalidad requerida
{describir aquí qué se necesita}
