# Configurar autenticación con Google (OAuth 2.0)

> **Acción OPCIONAL por proyecto.** El backbone generado YA trae el endpoint
> `POST /api/auth/google` y la verificación del token contra Google. Solo falta
> tu Client ID de Google y habilitarlo en la base de datos — **sin regenerar ni
> editar código**. Se administra desde `tbl_seg_parametro`.

## Cómo funciona (flujo)

1. El **frontend** usa Google Identity Services y obtiene un **ID token**
   (`credential`) cuando el usuario elige su cuenta de Google.
2. El frontend llama `POST /api/auth/google` con `{ "credential": "<ID token>" }`
   (el service generado ya lo hace: `googleAuthService.login(credential)`, y el
   componente `BotonGoogle` ya lo llama por vos — ver Paso 4).
3. El **backend** (`AuthController::googleLogin`):
   - exige `google_auth_activo = 1` (si no, responde **403**),
   - toma `google_client_id` de la BD como **audiencia** esperada,
   - verifica el token contra `https://oauth2.googleapis.com/tokeninfo`
     (firma/vigencia, que `aud` = tu Client ID y `email_verified = true`),
   - busca el **email** del token en `tbl_seg_usuario`: si existe y está activo,
     emite el token de la API (cuenta como **verificación fuerte / 2FA superado**).
4. Si el email **NO existe**, desde v4.34 ya no es un rechazo seco:
   - si su dominio está en `google_dominios_permitidos` → **alta automática**
     como `cliente` y entra;
   - si no → se registra en `tbl_seg_acceso_solicitud` y responde **403
     "pendiente de aprobación"** (ver Paso 5).
5. El endpoint va con rate limit `throttle:autenticacion` (parámetro
   `rate_limit_auth`, por IP) — protege contra fuerza bruta.

> ⚠ El alta la decide la BD, no el código: `google_dominios_permitidos` define
> quién entra solo y quién pasa por la cola de aprobación.

---

## Paso 1 · Crear el Client ID en Google Cloud Console

1. Entra a <https://console.cloud.google.com/> y crea (o elige) un proyecto.
2. **APIs y servicios → Pantalla de consentimiento de OAuth**: tipo *External*,
   completa nombre de la app, correo de soporte y dominios autorizados.
3. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de
   OAuth → Tipo de aplicación: Aplicación web**.
4. **Orígenes de JavaScript autorizados**: las URLs del FRONTEND, por ejemplo:
   - `https://tu-dominio.com` (producción)
   - `http://localhost:5173` (desarrollo con Vite)
5. *(Con Google Identity Services no se usan "URIs de redirección"; basta con los
   orígenes de JavaScript.)*
6. Copia el **Client ID** (termina en `.apps.googleusercontent.com`).

---

## Paso 2 · Habilitarlo en la base de datos (`tbl_seg_parametro`)

Ejecuta en tu BD (NO requiere regenerar ni redesplegar el backend):

```sql
UPDATE tbl_seg_parametro SET valor = '1'
  WHERE clave = 'google_auth_activo';
UPDATE tbl_seg_parametro SET valor = 'TU_CLIENT_ID.apps.googleusercontent.com'
  WHERE clave = 'google_client_id';
```

Para **desactivarlo** en cualquier momento: `google_auth_activo = '0'`.

---

## Paso 3 · Asegurar el usuario en `tbl_seg_usuario`

El email que devuelve Google debe existir en `tbl_seg_usuario` (activo, con su
rol). Ejemplo:

```sql
INSERT INTO tbl_seg_usuario (nombre, email, password, rol, metodo_2fa, activo, created_at)
VALUES ('Nombre Apellido', 'persona@gmail.com', '', 'usuario', 'ninguno', 1, NOW());
```

*(El `password` puede ir vacío si esa cuenta solo entra por Google; si también
usará login normal, ponle un hash bcrypt.)*

---

## Paso 4 · Montar el botón en el frontend (2 líneas)

**Desde v4.36.0 no hay que escribir nada de esto a mano**: davgen genera el botón
y la cola de aprobación, y los REGENERA en cada corrida (son aditivos, no pisan
tu `App.jsx`, tu `Login.jsx` ni tu `authService.js`):

| Archivo generado | Qué hace |
|---|---|
| `src/services/googleAuthService.js` | `/auth/google`, `/config-publica`, `/accesos/*` |
| `src/components/generados/BotonGoogle.jsx` | Botón oficial de Google Identity Services |
| `src/components/generados/PanelAccesosPendientes.jsx` | Cola de aprobación (solo admin) |
| `src/components/generados/LEEME-GOOGLE.md` | Esta misma referencia, dentro del front |

En tu pantalla de login:

```jsx
import BotonGoogle from './components/generados/BotonGoogle'

<BotonGoogle
  onAutenticado={(user) => { /* lo mismo que hacés tras login() */ }}
  onError={(msg) => setError(msg)}
/>
```

Y en tu pantalla de administración:

```jsx
import PanelAccesosPendientes from './components/generados/PanelAccesosPendientes'

<PanelAccesosPendientes roles={['cliente']} />
```

### Lo que NO hay que hacer

- **No pongas el Client ID en el código ni en un `.env`.** `BotonGoogle` lo lee en
  **runtime** de `POST /api/config-publica`, que lo saca de `tbl_seg_parametro`:
  activar, apagar o cambiar Google es **tocar solo la BD**, sin recompilar el
  front. Ya **no** se usa `VITE_GOOGLE_CLIENT_ID`. El Client ID es público (no es
  secreto); el Client **Secret** no se usa en este flujo.
- **No condiciones el botón a mano.** Si `google_auth_activo = 0` o falta el
  Client ID, `BotonGoogle` no renderiza nada. Dejalo montado siempre.

> Si tu proyecto es anterior a v4.36.0 y ya tenía un botón de Google escrito a
> mano, sigue funcionando: los archivos generados son nuevos y no lo tocan.
> Podés migrar cuando quieras, o quedarte con el tuyo.

---

## Paso 5 · Owner, dominios permitidos y cola de aprobación

Configurable en `[seguridad]` del `_configtotal.ini` (se siembra en
`tbl_seg_usuario` / `tbl_seg_parametro`):

- **`owner_email = cuenta@gmail.com`** — correo DUEÑO. davgen lo siembra como
  `admin` verificado, así **entra con Google desde el minuto cero** y puede
  **aprobar/denegar** el acceso de los demás. (Sin owner, Google solo sirve para
  usuarios ya cargados a mano.)
- **`google_dominios_permitidos = miempresa.com`** — un Gmail de esos
  dominios entra **directo** (alta automática como `cliente`); los demás quedan en
  **cola de aprobación**.
- **`roles_solo_google = cliente`** — los roles listados **solo** pueden entrar con
  Google; el login por contraseña se les rechaza (y al revés, los internos usan
  contraseña). Política conmutable desde `tbl_seg_parametro`.

**Cola de aprobación:** cuando un Gmail desconocido (fuera de los dominios)
intenta entrar, en vez de un rechazo seco se registra en
`tbl_seg_acceso_solicitud` (estado `pendiente`) y se responde *"acceso pendiente
de aprobación"*. El owner/admin lo resuelve (crea/activa el usuario):

```
POST /api/accesos/pendientes            -> lista de solicitudes pendientes
POST /api/accesos/aprobar { id, rol }   -> crea/activa el usuario con ese rol
POST /api/accesos/denegar { id }        -> marca la solicitud como denegada
```

En el front no hace falta llamarlos a mano: el componente generado
`PanelAccesosPendientes` ya los usa (Paso 4). Si querés armar tu propia
pantalla: `googleAuthService.pendientes()`, `.aprobar(id, rol)`, `.denegar(id)`.

## Verificación y problemas comunes

| Síntoma | Causa probable |
|---|---|
| `403` "Autenticación con Google deshabilitada" | `google_auth_activo` ≠ `1` |
| `500` "Falta configurar google_client_id" | parámetro `google_client_id` vacío |
| `401` "Token de Google inválido" | el `aud` del token ≠ tu Client ID, o `email_verified=false` |
| `403` "Tu acceso quedó PENDIENTE de aprobación" | Gmail desconocido fuera de `google_dominios_permitidos` → quedó en la cola; apruébalo |
| `502` "No se pudo verificar el token con Google" | el servidor no tiene salida HTTPS hacia `oauth2.googleapis.com` |
| `429` | rate limit (`rate_limit_auth`) — demasiados intentos por IP |

## Notas de seguridad

- El **Client ID NO es secreto** (viaja en el frontend); la seguridad está en que
  el backend valide la *audiencia* y `email_verified`.
- Este flujo usa **ID token** (Google Identity Services), **no** Client Secret ni
  el flujo Authorization Code: no hay secreto que guardar en el servidor.
- Todo es **conmutable desde la BD** (`tbl_seg_parametro`), coherente con la regla
  del proyecto de administrar la autenticación por base de datos.
