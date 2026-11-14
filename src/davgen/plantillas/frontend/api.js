// api.js — GENERADO por davgen (cliente HTTP de la API).
// Contrato del backend Laravel generado:
//   * TODO viaja por POST (también las lecturas).
//   * Éxito:  { mensaje, info }   ·   Error: { error: { text } }
//   * Autenticación: Sanctum Bearer token (POST /auth/login [+ 2FA]).
// Configurar en .env:  VITE_API_URL=http://localhost:8000/api

const API_URL = import.meta.env.VITE_API_URL ?? ''
const CLAVE_TOKEN = 'token'
const CLAVE_USUARIO = 'usuario'

export const hayApiConfigurada = Boolean(import.meta.env.VITE_API_URL)

export const sesion = {
  token: () => localStorage.getItem(CLAVE_TOKEN),
  usuario: () => {
    const guardado = localStorage.getItem(CLAVE_USUARIO)
    return guardado ? JSON.parse(guardado) : null
  },
  guardar: (token, usuario) => {
    localStorage.setItem(CLAVE_TOKEN, token)
    localStorage.setItem(CLAVE_USUARIO, JSON.stringify(usuario))
  },
  limpiar: () => {
    localStorage.removeItem(CLAVE_TOKEN)
    localStorage.removeItem(CLAVE_USUARIO)
    olvidarArchivos()   // lo descargado era de esta sesión
  },
  activa: () => Boolean(localStorage.getItem(CLAVE_TOKEN)),
}

export async function post(ruta, cuerpo = {}) {
  const cabeceras = { 'Content-Type': 'application/json', Accept: 'application/json' }
  const token = sesion.token()
  if (token) cabeceras.Authorization = `Bearer ${token}`

  const respuesta = await fetch(`${API_URL}${ruta}`, {
    method: 'POST',
    headers: cabeceras,
    body: JSON.stringify(cuerpo),
  })

  let datos = null
  try {
    datos = await respuesta.json()
  } catch {
    // respuesta sin cuerpo JSON (p. ej. 500 con HTML): se maneja abajo
  }

  if (respuesta.status === 401 && token) {
    sesion.limpiar()
    throw new Error('Sesión expirada: vuelve a iniciar sesión')
  }
  if (!respuesta.ok) {
    throw new Error(datos?.error?.text ?? `Error ${respuesta.status} del servidor`)
  }
  return datos // { mensaje, info }
}

// ── Archivos con sesión (fotos, PDF) ───────────────────────────────────────
// Un archivo protegido se pide con POST y token, y el navegador no guarda en
// caché ese tipo de pedido: sin esto, cada vez que una foto vuelve a pantalla
// es otro pedido al servidor (y otra conexión a la base, que en hosting
// compartido tiene cupo por hora). Aquí se guarda en memoria y se reutiliza.
const MAX_ARCHIVOS = 60                  // cuántos se recuerdan
const MAX_BYTES = 80 * 1024 * 1024       // y cuánto pueden pesar en total
const archivos = new Map()               // clave → { url, bytes } (orden = uso)
const enCamino = new Map()               // clave → promesa (pedidos repetidos)

function recordar(clave, url, bytes) {
  archivos.set(clave, { url, bytes })
  let total = 0
  for (const a of archivos.values()) total += a.bytes
  for (const [k, a] of archivos) {
    if (archivos.size <= MAX_ARCHIVOS && total <= MAX_BYTES) break
    if (k === clave) continue
    URL.revokeObjectURL(a.url)
    archivos.delete(k)
    total -= a.bytes
  }
}

/**
 * Dirección local (object URL) de un archivo protegido, para usar en
 * <img src>, <iframe src> o <a href download>. El mismo archivo se pide al
 * servidor UNA vez por sesión. No llamar a URL.revokeObjectURL sobre el
 * resultado: lo administra esta caché.
 *   const url = await descargar('/archivos/descargar', { pid: 7 })
 */
export function descargar(ruta, cuerpo = {}) {
  const clave = `${ruta}|${JSON.stringify(cuerpo)}`
  const guardado = archivos.get(clave)
  if (guardado) {
    archivos.delete(clave)               // pasa a ser el más reciente
    archivos.set(clave, guardado)
    return Promise.resolve(guardado.url)
  }
  if (enCamino.has(clave)) return enCamino.get(clave)

  const pedido = (async () => {
    const token = sesion.token()
    const respuesta = await fetch(`${API_URL}${ruta}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(cuerpo),
    })
    if (respuesta.status === 401 && token) {
      sesion.limpiar()
      throw new Error('Sesión expirada: vuelve a iniciar sesión')
    }
    if (!respuesta.ok) {
      let datos = null
      try { datos = await respuesta.json() } catch { /* sin cuerpo JSON */ }
      throw new Error(datos?.error?.text ?? `Error ${respuesta.status} del servidor`)
    }
    const contenido = await respuesta.blob()
    const url = URL.createObjectURL(contenido)
    recordar(clave, url, contenido.size)
    return url
  })().finally(() => enCamino.delete(clave))
  enCamino.set(clave, pedido)
  return pedido
}

/** Olvida los archivos guardados (al cerrar sesión, o si uno cambió). */
export function olvidarArchivos() {
  for (const a of archivos.values()) URL.revokeObjectURL(a.url)
  archivos.clear()
}

// Fecha en formato MySQL DATETIME — los procedimientos pcru* sobreescriben
// TODOS los campos, fechas incluidas: cada add/upd debe enviarlas.
export function ahoraSql() {
  return new Date().toISOString().slice(0, 19).replace('T', ' ')
}
