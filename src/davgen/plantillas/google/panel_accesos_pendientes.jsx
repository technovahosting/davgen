// PanelAccesosPendientes — cola de aprobación de accesos por Google.
//
// Un correo de Google desconocido NO entra: queda en
// tbl_seg_acceso_solicitud y un admin lo aprueba o lo deniega acá.
//
//   import PanelAccesosPendientes from '../components/generados/PanelAccesosPendientes'
//   <PanelAccesosPendientes roles={['cliente', 'secretaria']} />
//
// Solo admin (esAdmin() en el backend): a un rol sin permiso la API le
// responde 403 y el panel muestra ese mensaje en vez de una tabla vacía.
import { useCallback, useEffect, useState } from 'react'
import { googleAuthService } from '../../services/googleAuthService'

export default function PanelAccesosPendientes({
  roles = ['cliente'],
  onCambio,
}) {
  const [solicitudes, setSolicitudes] = useState([])
  const [rolElegido, setRolElegido] = useState({})
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(null)

  const cargar = useCallback(async () => {
    setCargando(true); setError('')
    try {
      const lista = await googleAuthService.pendientes()
      setSolicitudes(Array.isArray(lista) ? lista : [])
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  async function resolver(id, accion) {
    setOcupado(id); setError('')
    try {
      if (accion === 'aprobar') {
        await googleAuthService.aprobar(id, rolElegido[id] ?? roles[0])
      } else {
        await googleAuthService.denegar(id)
      }
      await cargar()
      onCambio?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(null)
    }
  }

  if (cargando && !solicitudes.length) return <p>Cargando solicitudes…</p>
  if (error) return <p style={{ color: '#b91c1c' }}>{error}</p>
  if (!solicitudes.length) return <p style={{ opacity: 0.7 }}>No hay solicitudes pendientes.</p>

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr>
          <th style={{ textAlign: 'left', padding: '0.5rem' }}>Correo</th>
          <th style={{ textAlign: 'left', padding: '0.5rem' }}>Nombre</th>
          <th style={{ textAlign: 'left', padding: '0.5rem' }}>Solicitado</th>
          <th style={{ textAlign: 'left', padding: '0.5rem' }}>Rol a asignar</th>
          <th style={{ padding: '0.5rem' }}>Acción</th>
        </tr>
      </thead>
      <tbody>
        {solicitudes.map(s => (
          <tr key={s.id} style={{ borderTop: '1px solid rgba(0,0,0,0.1)' }}>
            <td style={{ padding: '0.5rem' }}>{s.email}</td>
            <td style={{ padding: '0.5rem' }}>{s.nombre ?? '—'}</td>
            <td style={{ padding: '0.5rem' }}>{s.created_at ?? '—'}</td>
            <td style={{ padding: '0.5rem' }}>
              <select
                aria-label={`Rol a asignar a ${s.email ?? s.nombre ?? 'la solicitud'}`}
                value={rolElegido[s.id] ?? roles[0]}
                onChange={e => setRolElegido(r => ({ ...r, [s.id]: e.target.value }))}
              >
                {roles.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </td>
            <td style={{ padding: '0.5rem', whiteSpace: 'nowrap' }}>
              <button disabled={ocupado === s.id} onClick={() => resolver(s.id, 'aprobar')}>
                Aprobar
              </button>{' '}
              <button disabled={ocupado === s.id} onClick={() => resolver(s.id, 'denegar')}>
                Denegar
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
