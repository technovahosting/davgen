# Login con Google y cola de accesos (generado)

> ⚠ Estos tres archivos los **regenera davgen**: no los edites. Son aditivos —
> no tocan tu `App.jsx`, tu `Login.jsx` ni tu `authService.js`.

| Archivo | Qué hace |
|---|---|
| `services/googleAuthService.js` | `/auth/google`, `/config-publica`, `/accesos/*` |
| `components/generados/BotonGoogle.jsx` | Botón oficial de Google (se dibuja solo si la BD lo activa) |
| `components/generados/PanelAccesosPendientes.jsx` | Cola de aprobación (solo admin) |

## Montarlo (2 líneas)

En tu pantalla de login:

```jsx
import BotonGoogle from './components/generados/BotonGoogle'

<BotonGoogle
  onAutenticado={(user) => { /* lo mismo que hacés tras login() */ }}
  onError={(msg) => setError(msg)}
/>
```

En tu pantalla de administración:

```jsx
import PanelAccesosPendientes from './components/generados/PanelAccesosPendientes'

<PanelAccesosPendientes roles={['cliente']} />
```

## Lo que NO hay que hacer

- **No pongas el Client ID en el código ni en `.env`.** Se lee en runtime de
  `POST /config-publica`, que lo saca de `tbl_seg_parametro`. Así se activa,
  se apaga o se cambia **tocando solo la BD**, sin recompilar ni redesplegar.
- **No condiciones el botón a mano.** Si `google_auth_activo = 0` o no hay
  Client ID, `BotonGoogle` no renderiza nada. Dejalo montado siempre.

## Comportamiento esperado

| Caso | Qué pasa |
|---|---|
| Correo ya registrado | Entra directo (token de sesión, igual que el login normal) |
| Correo de un dominio de `google_dominios_permitidos` | Alta automática como `cliente` y entra |
| Correo desconocido | **403 «pendiente de aprobación»** → queda en `tbl_seg_acceso_solicitud`; `onError` recibe ese texto |
| Rol en `roles_solo_google` | No puede entrar por contraseña: Google es su única vía |

## Requisito fuera del código

El **origen** desde el que se sirve la app (ej. `https://midominio.com`) debe
estar en *Authorized JavaScript origins* del Client ID en Google Cloud Console.
Si el botón aparece pero el login falla, es casi siempre esto.
Ver `CONFIGURAR-GOOGLE-AUTH.md` en la raíz del proyecto.
