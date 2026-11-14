// Paginacion — controles previo/siguiente a partir del objeto pagination de la API.
export default function Paginacion({ paginacion, onCambiar }) {
  if (!paginacion) return null
  const { current_page = 1, last_page = 1 } = paginacion
  return (
    <nav className="paginacion" aria-label="Paginación">
      <button type="button" disabled={current_page <= 1} onClick={() => onCambiar(current_page - 1)}>
        Anterior
      </button>
      <span aria-live="polite">Página {current_page} de {last_page}</span>
      <button type="button" disabled={current_page >= last_page} onClick={() => onCambiar(current_page + 1)}>
        Siguiente
      </button>
    </nav>
  )
}
