// Tema de la aplicación: claro, oscuro o el del sistema operativo.
//
// Por defecto se sigue al sistema (prefers-color-scheme). Si la persona elige
// claro u oscuro, la elección queda guardada en este navegador.
// Se aplica al importarlo, antes de que React dibuje: no hay parpadeo.
//
//   import './services/tema'                         // una vez, en App.jsx
//   import { fijarTema, temaGuardado } from './services/tema'
const CLAVE = 'tema'
export const TEMAS = ['sistema', 'claro', 'oscuro']
const NOMBRE_DAISY = { claro: 'light', oscuro: 'dark' }

function prefiereOscuro() {
  return typeof window !== 'undefined'
    && !!window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** Lo que eligió la persona: 'sistema' (por defecto), 'claro' u 'oscuro'. */
export function temaGuardado() {
  try {
    const t = localStorage.getItem(CLAVE)
    return TEMAS.includes(t) ? t : 'sistema'
  } catch {
    return 'sistema'
  }
}

/** El tema que se ve ahora mismo: 'claro' u 'oscuro'. */
export function temaEfectivo(tema = temaGuardado()) {
  if (tema !== 'sistema') return tema
  return prefiereOscuro() ? 'oscuro' : 'claro'
}

export function aplicarTema(tema = temaGuardado()) {
  if (typeof document === 'undefined') return
  const raiz = document.documentElement
  // 'sistema' = sin atributo: el CSS decide con prefers-color-scheme
  if (tema === 'sistema') raiz.removeAttribute('data-theme')
  else raiz.setAttribute('data-theme', NOMBRE_DAISY[tema])
  // para que los controles nativos (barras, selects, fechas) acompañen
  raiz.style.colorScheme = temaEfectivo(tema) === 'oscuro' ? 'dark' : 'light'
}

export function fijarTema(tema) {
  if (!TEMAS.includes(tema)) return
  try { localStorage.setItem(CLAVE, tema) } catch { /* modo privado: solo esta sesión */ }
  aplicarTema(tema)
  window.dispatchEvent(new CustomEvent('tema', { detail: tema }))
}

if (typeof window !== 'undefined') {
  // si el sistema cambia de claro a oscuro con la app abierta, se acompaña
  const medio = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)')
  if (medio && medio.addEventListener) {
    medio.addEventListener('change', () => { if (temaGuardado() === 'sistema') aplicarTema('sistema') })
  }
  aplicarTema()
}
