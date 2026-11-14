// SelectRelacion — dropdown para una clave foránea: carga las opciones desde el
// servicio de la tabla relacionada y muestra `etiqueta` como texto visible.
//   <SelectRelacion servicio={categoriaService} nombre="categoria_id"
//                   valor={form.categoria_id} onChange={setCampo}
//                   etiqueta="nombre" label="Categoría" />
//
// La lista de cada servicio se pide UNA vez y se comparte entre todos los
// desplegables durante unos minutos: un formulario con varias relaciones, o
// abrirlo muchas veces, no repite el pedido (cada pedido es una conexión a la
// base, que en hosting compartido tiene cupo por hora). Tras dar de alta una
// opción nueva, `olvidarOpciones(servicio)` la hace aparecer enseguida.
import { useEffect, useState } from 'react'

const VIGENCIA_MS = 3 * 60 * 1000
const listas = new WeakMap()             // servicio → { cuando, promesa }

function opcionesDe(servicio) {
  const guardada = listas.get(servicio)
  if (guardada && Date.now() - guardada.cuando < VIGENCIA_MS) return guardada.promesa
  const promesa = servicio.listar('', 1, 100).then((r) => r.items ?? [])
  listas.set(servicio, { cuando: Date.now(), promesa })
  promesa.catch(() => listas.delete(servicio))   // un fallo no se recuerda
  return promesa
}

// eslint-disable-next-line react-refresh/only-export-components
export function olvidarOpciones(servicio) {
  listas.delete(servicio)
}

export default function SelectRelacion({
  servicio, valor, onChange, nombre, etiqueta = 'nombre', valueField = 'id', label,
}) {
  const [opciones, setOpciones] = useState([])
  useEffect(() => {
    let vivo = true
    opcionesDe(servicio)
      // eslint-disable-next-line react-hooks/set-state-in-effect
      .then((items) => { if (vivo) setOpciones(items) })
      .catch(() => {})
    return () => { vivo = false }
  }, [servicio])
  const id = `rel-${nombre}`
  return (
    <div className="campo">
      {label && <label htmlFor={id}>{label}</label>}
      <select id={id} value={valor ?? ''} onChange={(e) => onChange(nombre, e.target.value)}>
        <option value="">—</option>
        {opciones.map((o) => (
          <option key={o[valueField]} value={o[valueField]}>{o[etiqueta] ?? o[valueField]}</option>
        ))}
      </select>
    </div>
  )
}
