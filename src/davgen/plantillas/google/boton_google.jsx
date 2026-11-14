// BotonGoogle — botón oficial de Google Identity Services.
//
// Se dibuja SOLO si la BD tiene google_auth_activo=1 y un google_client_id
// (POST /config-publica). Si Google está apagado no renderiza nada: se puede
// dejar montado en el login sin condicionales.
//
//   import BotonGoogle from '../components/generados/BotonGoogle'
//   <BotonGoogle onAutenticado={(user) => ...} onError={(msg) => ...} />
import { useEffect, useRef, useState } from 'react'
import { googleAuthService } from '../../services/googleAuthService'

const URL_GIS = 'https://accounts.google.com/gsi/client'

/** Carga el script de Google una sola vez por página (aunque haya varios
 *  botones montados). Devuelve una promesa que resuelve con window.google. */
let promesaGis = null
function cargarGis() {
  if (promesaGis) return promesaGis
  promesaGis = new Promise((resolver, rechazar) => {
    if (window.google?.accounts?.id) return resolver(window.google)
    const previo = document.querySelector(`script[src="${URL_GIS}"]`)
    const script = previo ?? document.createElement('script')
    script.addEventListener('load', () => resolver(window.google))
    script.addEventListener('error', () =>
      rechazar(new Error('No se pudo cargar el script de Google (¿sin internet?)')))
    if (!previo) {
      script.src = URL_GIS
      script.async = true
      document.head.appendChild(script)
    }
  })
  return promesaGis
}

export default function BotonGoogle({
  onAutenticado,
  onError,
  texto = 'signin_with',   // signin_with | signup_with | continue_with
  ancho = 320,
}) {
  const contenedor = useRef(null)
  const [activo, setActivo] = useState(false)
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    let vivo = true

    async function montar() {
      let config
      try {
        config = await googleAuthService.configPublica()
      } catch {
        return   // sin /config-publica (backend viejo): Google no se ofrece
      }
      // La BD manda: apagado o sin Client ID → no se dibuja nada.
      // La API puede entregar el parámetro como booleano, número o texto.
      const encendido = ['1', 'true', 'si', 'sí'].includes(
        String(config?.google_auth_activo ?? '0').trim().toLowerCase())
      const clientId = config?.google_client_id ?? ''
      if (!vivo || !encendido || !clientId) return

      let google
      try {
        google = await cargarGis()
      } catch (e) {
        onError?.(e.message)
        return
      }
      if (!vivo || !contenedor.current) return

      google.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }) => {
          setCargando(true)
          try {
            const info = await googleAuthService.login(credential)
            onAutenticado?.(info?.user ?? null)
          } catch (e) {
            // 403 = correo desconocido → quedó en la cola de aprobación.
            onError?.(e.message)
          } finally {
            setCargando(false)
          }
        },
      })
      google.accounts.id.renderButton(contenedor.current, {
        theme: 'outline', size: 'large', text: texto,
        shape: 'rectangular', width: ancho, locale: 'es',
      })
      setActivo(true)
    }

    montar()
    return () => { vivo = false }
  }, [texto, ancho, onAutenticado, onError])

  // El contenedor se dibuja SIEMPRE (Google necesita el nodo para pintar el
  // botón dentro); mientras Google no esté listo queda oculto y no ocupa
  // lugar. Con `return null` el ref nunca existía y el botón no aparecía.
  return (
    <div style={{ display: activo ? 'grid' : 'none', gap: 8, justifyItems: 'center' }}>
      <div ref={contenedor} />
      {cargando && (
        <span style={{ fontSize: '0.8rem', opacity: 0.7 }}>Verificando con Google…</span>
      )}
    </div>
  )
}
