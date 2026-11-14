// CampoFormulario — input genérico por tipo (text|email|number|date|datetime-local|
// time|textarea|checkbox|select). onChange(nombre, valor).
export default function CampoFormulario({
  tipo = 'text', nombre, valor, onChange, label, opciones, requerido,
}) {
  const set = (v) => onChange(nombre, v)
  const id = `campo-${nombre}`
  let control
  if (tipo === 'textarea') {
    control = <textarea id={id} value={valor ?? ''} onChange={(e) => set(e.target.value)} />
  } else if (tipo === 'checkbox') {
    control = (
      <input id={id} type="checkbox" checked={Boolean(Number(valor))}
        onChange={(e) => set(e.target.checked ? 1 : 0)} />
    )
  } else if (tipo === 'select') {
    control = (
      <select id={id} value={valor ?? ''} onChange={(e) => set(e.target.value)}>
        <option value="">—</option>
        {(opciones ?? []).map((o) => (
          <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>
        ))}
      </select>
    )
  } else {
    control = (
      <input id={id} type={tipo} value={valor ?? ''} required={requerido}
        onChange={(e) => set(e.target.value)} />
    )
  }
  return (
    <div className="campo">
      <label htmlFor={id}>{label ?? nombre}</label>
      {control}
    </div>
  )
}
