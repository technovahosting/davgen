# davgen __VERSION__ — Guía rápida

> Generador de sistemas Laravel + React dirigido por `_configtotal.ini`.
> Autor: __AUTOR__

---

## Inicio rápido

1. Completar `_configtotal.ini` (nombre del proyecto y módulo) y
   `_acceso.desarrollo.ini` (la base donde desarrollas).
2. Ejecutar `davgen seguridad` (crea `tbl_seg_*` en la BD; equivale a correr
   `02-Base-de-datos/00-seguridad.sql` a mano).
3. Ejecutar `davgen generar` en la raíz del proyecto.
4. El generador crea Controllers, Services, rutas API, páginas React, scripts
   SQL y pruebas. `davgen doctor` dice si falta algo en el equipo (PHP,
   composer, node).

> **Sin base de datos ni hosting** también se puede generar todo el código:
> `davgen generar --local` no escribe en la BD, no usa FTP y no instala nada.

---

## Secciones de `_configtotal.ini`

| Sección | Para qué |
|---|---|
| `[proyecto]` | Nombre del sistema |
| `[bd]` | Host, usuario, password, nombre de la BD — en `_acceso.<entorno>.ini` |
| `[entrada]` | `tipo = bd` (lee la BD) o `tipo = mockup` (HTML/bundle Bolt.new) |
| `[opciones]` | `solo_lectura`, `sin_baja`, `solo_consulta`, `publico` por tabla; `conexiones_persistentes` |
| `[generar]` | Flags booleanos (ver abajo) |
| `[seguridad]` | Admin inicial (`admin_email`, `admin_password`) y login con Google (apagado por defecto) |
| `[ftp]` | Host, usuario, password, ruta remota, URL pública — en `_acceso.produccion.ini` |

### Dos entornos

Los usuarios y contraseñas van en dos archivos que **no se versionan**:
`_acceso.desarrollo.ini` (donde se programa y se prueba) y
`_acceso.produccion.ini` (el sitio publicado). davgen usa el de desarrollo y
ahí **nunca publica**; para aplicar en la base de producción y subir por FTP:
`davgen generar --entorno produccion`.

---

## Flags de `[generar]`

### Acciones — escriben FUERA del proyecto

| Flag | Por defecto | Qué hace |
|---|---|---|
| `aplicar_sps` | `si` | Aplica en la BD los SPs `pcru*` nuevos o distintos, los seeds de seguridad y las vistas que falten |
| `produccion` | `no` | Sube el backend a la nube por FTP al terminar |
| `front` | `no` | Construye el frontend React y sube `dist/` al hosting |

En modo interactivo se muestra el destino real de cada acción y se pide
confirmación antes de empezar.

### Opcionales (`no` por defecto)

| Flag | Qué genera | Para qué sirve |
|---|---|---|
| `form_requests` | `app/Http/Requests/{Entidad}Request.php` por tabla | Valida automáticamente los datos antes de llegar al controller: campos obligatorios, tipos, longitud máxima de texto, valores permitidos en enums. Si algo falla devuelve error 422 con el mensaje al frontend. |
| `tests` | `tests/Feature/Generados/` con AuthTest, RutasTest y RateLimitTest | Pruebas automáticas para verificar que el login funciona, que las rutas protegidas exigen token y que el límite de intentos responde con 429. Correr con `php artisan test`. |
| `componentes_react` | `src/hooks/` y `src/components/generados/` | Genera componentes React reutilizables: **DataTable** (tabla con búsqueda), **CampoFormulario** (input según tipo de dato), **SelectRelacion** (dropdown que carga automáticamente los registros de la tabla relacionada para campos FK), **Paginacion** y hooks `useCrud`/`useAuth`. Con este flag activo, los campos `*_id` en los formularios muestran un desplegable en vez de un campo numérico. |
| `ci` | `.github/workflows/ci.yml` | Pipeline de integración continua en GitHub: corre los tests PHP, compila el frontend y ejecuta `davgen verificar` para detectar si alguien editó archivos generados. Si hay cambios no autorizados, el pipeline falla. |
| `openapi` | `_backendGenerado/documentacion/openapi.json` + `swagger.html` | Genera la especificación OpenAPI 3 de todos los endpoints de la API y una interfaz Swagger UI para explorarlos y probarlos desde el navegador. |
| `export` | Endpoint `POST /{tabla}/export` en cada tabla | Permite descargar los datos de cualquier tabla como archivo CSV. Requiere el mismo permiso de lectura (`sel`) que el listado. Útil para reportes sin necesidad de código adicional. |

> En modo interactivo aparece un **menú de toggle** antes de generar.
> Los cambios se guardan en `_configtotal.ini` y persisten.

---

## Seguridad del proyecto generado

- `davgen acceso cifrar` guarda los accesos **cifrados** con un token tuyo (lo
  pide al ejecutar) y entrega una llave maestra por si el token se pierde.
- Las contraseñas van en `_acceso.<entorno>.ini`, que están en `.gitignore`.
  Para git se usan sus `.ejemplo.ini` (davgen los escribe sin las contraseñas).
- El administrador inicial se siembra con `admin_email` y la `admin_password`
  del archivo de acceso del entorno (la escribes tú: davgen no trae ninguna). **Cambiarla al primer
  ingreso**: el seed nunca la vuelve a tocar.
- El login con Google viene **apagado**. Se activa con un Client ID propio:
  ver `CONFIGURAR-GOOGLE-AUTH.md`.

---

## ❌ No editar — se reemplazan al regenerar

- `app/Http/Controllers/*Controller.php`
- `app/Http/Controllers/AuthController.php`
- `app/Services/*Service.php` (incluido `BaseService`)
- `app/Http/Middleware/VerificarPermiso.php`
- `routes/api.php` y `routes/web.php`
- `src/services/*Service.js`
- `src/pages/generados/*.jsx` y `src/pages/generados/rutas.jsx`
- `src/services/googleAuthService.js`
- `src/components/generados/BotonGoogle.jsx` y `PanelAccesosPendientes.jsx`
- Procedimientos `pcru*` en la BD

## ✅ Sí personalizar — davgen no los toca

- **Extender Services**: `class MiServicio extends ProductoService { ... }`
- **Código propio PHP**: cualquier archivo tuyo bajo `app/` o `routes/`
  (convención recomendada: `app/**/Custom/` y `routes/Custom/`). davgen lo
  reconoce porque NO lleva la cabecera `@generated` y el delta FTP lo despliega.
- **Rutas propias**: todo `routes/Custom/*.php` se carga solo bajo `/api`
  (lo hace `bootstrap/app.php`); no hace falta registrarlo en un Provider.
- **Plantillas del generador**: `davgen plantillas copiar <grupo/archivo>` copia
  una plantilla a `_plantillas/` del proyecto; la tuya gana al regenerar.
- **SPs de dominio**: prefijo `pag_*` (ej. `pag_ven_pedido_confirmar`)
- **`App.jsx`**: solo se genera la primera vez
- **`src/api.js`** y **`authService.js`**: solo si no existen. Por eso las piezas
  de Google viven en archivos aparte (ver la lista de arriba): así llegan también
  a los proyectos que ya tenían su propio `authService.js`
- **Tus páginas** en `src/pages/` (fuera de `generados/`) y `src/components/`
- **Roles y permisos**: administrar en `tbl_seg_rol` / `tbl_seg_permiso`
- **Parámetros runtime**: `tbl_seg_parametro` (2FA, rate limits, Google login)

---

## Comandos

```
davgen nuevo [carpeta]      crea la estructura de un proyecto nuevo
davgen seguridad            crea las tablas tbl_seg_* en la BD (una sola vez)
davgen generar              genera todo (interactivo con menú)
davgen generar --si         no interactivo (usa flags del .ini)
davgen generar --local      solo archivos: sin BD, sin FTP, sin instalar nada
davgen sincronizar --si     regenera solo si la BD cambió
davgen verificar            detecta ediciones manuales en archivos generados
davgen comparar             muestra el diff exacto de lo que cambió
davgen plantillas listar    plantillas disponibles (y cuáles personalizaste)
davgen plantillas copiar X  copia una plantilla al proyecto para editarla
davgen doctor               requisitos y diagnóstico (PHP, composer, node, accesos)
davgen doctor --conexiones  prueba la base y el FTP y explica por qué fallan
davgen comparar --remoto    baja el backend publicado y lo compara en local
davgen proteger             cierra la carpeta publicada (.env, logs) de un sitio ya desplegado
davgen entornos             separa los accesos en desarrollo y producción
davgen acceso cifrar        guarda los accesos cifrados con un token
davgen acceso               estado · ver · descifrar · cambiar-token · reiniciar
davgen actualizar           renueva estas guías con la versión instalada
davgen --version            muestra la versión actual
```

---

## Despliegue FTP (hosting compartido)

- **Primer despliegue**: sube `servicio.zip` completo y lo descomprime en la nube.
- **Actualizaciones (delta)**: sube solo lo que cambió de `app/**` + `routes/**` +
  `bootstrap/app.php`, tanto lo generado como tu código propio.
- **Frontend**: `npm run build` → sube `dist/*` a la raíz del hosting. Se omite si
  nada cambió en `src/**`, `public/**` ni en la configuración de la raíz.
- El `.env` remoto nunca se sobreescribe.
- `[ftp] url` debe empezar con `https://` si el hosting fuerza HTTPS.
- El servidor necesita **PHP 8.2 o superior** (requisito de Laravel).
- La carpeta publicada va **protegida**: el `.env`, los logs y los archivos de los
  usuarios no se pueden bajar por web, y davgen lo comprueba al terminar. Un
  sitio publicado con una versión anterior se protege con `davgen proteger`.

### Límites del hosting

- El hosting compartido limita las conexiones **nuevas** a MySQL por hora (un
  valor habitual es 500 por usuario de la base). Al agotarse, **todo** el sitio
  responde 500 —también el login— hasta la hora siguiente. En
  `storage/logs/laravel.log` se ve como
  `[1226] ... has exceeded the 'max_connections_per_hour' resource`.
- Qué hacer: esperar a que se libere y **no correr davgen contra producción**
  mientras tanto (gasta del mismo cupo).
- Para evitarlo el backend usa **conexiones persistentes**
  (`[opciones] conexiones_persistentes = si`, por defecto). Un sitio ya publicado
  las recibe con solo regenerar y desplegar.
- Si en cambio aparece el error **1203** (demasiadas conexiones abiertas a la
  vez), apagarlas: `DB_PERSISTENT=false` en el `.env` del servidor, o
  `conexiones_persistentes = no` y regenerar.

---

## Integridad del código generado

```
davgen verificar   → exit 0 = intacto, 1 = hay ediciones manuales
davgen comparar    → diff línea a línea (verde = añadido, rojo = eliminado)
```

Las carpetas generadas llevan `_NO-MODIFICAR.md` como recordatorio.

---

---

## Lo que davgen ya maneja automáticamente

Estos puntos **no requieren código extra** — el generador ya los resuelve:

| Situación | Cómo lo resuelve davgen |
|---|---|
| Columna ENUM en la BD | Genera `<select>` con todas las opciones del ENUM (no un `<input type=text>`) |
| Validación ENUM en el backend | Con `form_requests=si` añade `in:val1,val2,...` al FormRequest → devuelve 422 si el valor no es válido |
| `ConvertEmptyStringsToNull` de Laravel | El controller usa `$request->input('p_campo') ?? ''` en los textos (nunca llegan como `null` a los SPs) y `null` en fechas y ENUM vacíos (MySQL estricto rechaza `''` en esos tipos) |
| Tipos de input en formularios | DATE→`date`, DATETIME→`datetime-local`, TIME→`time`, DECIMAL→`number(step=0.01)`, TEXT→`textarea`, campos `*correo*`→`email`, `*telefono*`→`tel` |
| `--listar` sin destruir archivos | Modo 100 % read-only: no limpia, no crea, no escribe nada |
| Nombres de campo sin vendor/ | `generar --listar` acepta un Laravel sin `vendor/` instalado |

---

## Contratos de uso — precauciones importantes

### El prefijo `p` es obligatorio en los parámetros

El controller siempre envía `p<campo>` al SP (ej: `pmpi`, `pnombre`).
Si el cliente manda los datos sin el prefijo, el SP los ignora y guarda un registro vacío **sin error**.

```js
// ✅ correcto (lo hace el Service generado automáticamente)
await servicio.add({ pnombre: 'Juan', papellido: 'Pérez' })

// ❌ incorrecto — guarda fila vacía
await servicio.add({ nombre: 'Juan', apellido: 'Pérez' })
```

> El Service generado (`{Entidad}Service.js`) ya construye los parámetros con el prefijo `p` correctamente. Solo es un riesgo si se llama a la API manualmente o desde Postman.

---

### `upd` sobreescribe TODOS los campos

El SP `pcruXxx('U')` actualiza todas las columnas con los valores recibidos.
Enviar un registro incompleto borra los campos que no se manden.

**Patrón correcto:** antes de editar, hacer un `get` del registro completo, modificar solo los campos necesarios y enviar el objeto completo al `upd`.

```js
const registro = await servicio.get(id)   // carga todos los campos
registro.estado = 'activo'                // modifica solo lo necesario
await servicio.upd(registro)              // envía el objeto completo
```

> El formulario generado ya sigue este patrón (carga el registro en `useEffect` al abrir el modal de edición).

---

### Orden de parámetros del SP = orden de columnas en la BD

El controller arma el `CALL pcru*(...)` por posición, siguiendo el orden de las columnas tal como las devuelve `INFORMATION_SCHEMA`. Si se agrega una columna con `ALTER TABLE`, usar siempre `ADD COLUMN ... AFTER <columna>` para controlar el orden, y **regenerar inmediatamente** el SP, el controller y el service juntos (los tres deben quedar alineados con la misma lectura del esquema).

---

### opcache tras desplegar PHP por FTP

LiteSpeed/Apache puede servir la versión anterior del controller hasta que opcache revalide (TTL típico: 60 s).
Si tras un despliegue la API sigue con el comportamiento viejo, esperar 1 minuto o reiniciar opcache manualmente desde el panel del hosting.

---

*Generado por davgen __VERSION__ — __AUTOR__*
