// authService.js — GENERADO por davgen (login + 2FA contra /auth/*).
// Flujo: login(email, password) →
//   · sin 2FA: { token, user } (sesión guardada)
//   · con 2FA: { requiere_2fa: true, metodo } → verificar(email, password, codigo)
import { post, sesion } from './api'

export const authService = {
  /** Paso 1. Devuelve info de la API; si trae token, guarda la sesión. */
  async login(email, password) {
    const { info } = await post('/auth/login', { email, password })
    if (info?.token) sesion.guardar(info.token, info.user)
    return info // { token, user } | { requiere_2fa, metodo }
  },

  /** Paso 2 (solo con 2FA): credenciales + código → token. */
  async verificar(email, password, codigo) {
    const { info } = await post('/auth/verificar', { email, password, codigo })
    if (info?.token) sesion.guardar(info.token, info.user)
    return info
  },

  /** Inicio de sesión con Google (requiere google_auth_activo=1 en la BD).
   *  `credential` es el ID token que entrega Google Identity Services. */
  async loginConGoogle(credential) {
    const { info } = await post('/auth/google', { credential })
    if (info?.token) sesion.guardar(info.token, info.user)
    return info
  },

  /** Config pública (sin token): { google_auth_activo, google_client_id }.
   *  Permite activar/cambiar Google SOLO tocando la BD, sin recompilar el front. */
  async getConfigPublica() {
    const { info } = await post('/config-publica')
    return info
  },

  /** Solicitudes de acceso Google pendientes (solo admin/owner). */
  async accesosPendientes() {
    const { info } = await post('/accesos/pendientes')
    return info
  },
  async aprobarAcceso(id, rol) {
    return (await post('/accesos/aprobar', { id, rol })).info
  },
  async denegarAcceso(id) {
    return (await post('/accesos/denegar', { id })).info
  },

  async logout() {
    try {
      await post('/auth/logout')
    } finally {
      sesion.limpiar()
    }
  },

  async me() {
    const { info } = await post('/auth/me')
    return info.user
  },

  /** Módulos y permisos del rol (menú dinámico desde la BD). */
  async menu() {
    const { info } = await post('/auth/menu')
    return info.modulos ?? []
  },

  usuarioActual: () => sesion.usuario(),
  haySesion: () => sesion.activa(),
}
