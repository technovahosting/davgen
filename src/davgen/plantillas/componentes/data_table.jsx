// DataTable — tabla genérica. columnas: [{ campo, titulo }].
export default function DataTable({ columnas, datos, onEditar, onEliminar, cargando }) {
  if (cargando) return <p>Cargando…</p>
  if (!datos?.length) return <p>Sin registros.</p>
  const conAcciones = Boolean(onEditar || onEliminar)
  return (
    <table className="tabla">
      <thead>
        <tr>
          {columnas.map((c) => <th key={c.campo}>{c.titulo ?? c.campo}</th>)}
          {conAcciones && <th>Acciones</th>}
        </tr>
      </thead>
      <tbody>
        {datos.map((fila, i) => (
          <tr key={fila.id ?? i}>
            {columnas.map((c) => <td key={c.campo}>{String(fila[c.campo] ?? '')}</td>)}
            {conAcciones && (
              <td>
                {onEditar && <button type="button" onClick={() => onEditar(fila)}>Editar</button>}
                {onEliminar && <button type="button" onClick={() => onEliminar(fila)}>Dar de baja</button>}
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
