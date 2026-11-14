import { post, sesion } from './api'

export const googleAuthService = {
  /** Config pública (sin token): { google_auth_activo, google_client_id }.
   *  Es la ÚNICA fuente del Client ID en el frontend. */
  async configPublica() {
    const { info } = await post('/config-publica')
    return info
  },

  /** Login con Google. `credential` es el ID token de Google Identity Services.
   *  Guarda la sesión si la API devuelve token (mismo almacén que authService:
   *  el resto de la app no nota la diferencia).
   *  Si el correo es desconocido la API responde 403 «pendiente de aprobación»
   *  y post() lanza ese texto como Error — mostrarlo tal cual al usuario. */
  async login(credential) {
    const { info } = await post('/auth/google', { credential })
    if (info?.token) sesion.guardar(info.token, info.user)
    return info
  },

  /** Cola de aprobación (solo admin). */
  async pendientes() {
    const { info } = await post('/accesos/pendientes')
    return info?.solicitudes ?? info ?? []
  },
  async aprobar(id, rol = 'cliente') {
    return (await post('/accesos/aprobar', { id, rol })).info
  },
  async denegar(id) {
    return (await post('/accesos/denegar', { id })).info
  },
}
