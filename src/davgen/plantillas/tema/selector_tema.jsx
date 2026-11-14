// SelectorTema — tres botones: seguir al sistema, claro u oscuro.
//
//   import SelectorTema from './components/generados/SelectorTema'
//   <SelectorTema />            // en la barra superior, en el login…
import { useEffect, useState } from 'react'
import { fijarTema, temaGuardado } from '../../services/tema'

const OPCIONES = [
  { clave: 'sistema', etiqueta: 'Sistema', titulo: 'Seguir el tema del sistema operativo', icono: '🖥' },
  { clave: 'claro',   etiqueta: 'Claro',   titulo: 'Tema claro',  icono: '☀' },
  { clave: 'oscuro',  etiqueta: 'Oscuro',  titulo: 'Tema oscuro', icono: '🌙' },
]

export default function SelectorTema({ conTexto = false }) {
  const [tema, setTema] = useState(temaGuardado())

  // si otro selector de la página lo cambia, este se entera
  useEffect(() => {
    const oir = (e) => setTema(e.detail)
    window.addEventListener('tema', oir)
    return () => window.removeEventListener('tema', oir)
  }, [])

  return (
    <div className="join" role="group" aria-label="Tema de la aplicación">
      {OPCIONES.map(o => (
        <button
          key={o.clave} type="button" title={o.titulo}
          aria-pressed={tema === o.clave}
          className={'btn btn-sm join-item ' + (tema === o.clave ? 'btn-primary' : 'btn-ghost')}
          onClick={() => { fijarTema(o.clave); setTema(o.clave) }}
        >
          <span aria-hidden="true">{o.icono}</span>
          <span className={conTexto ? '' : 'sr-only'}>{o.etiqueta}</span>
        </button>
      ))}
    </div>
  )
}
