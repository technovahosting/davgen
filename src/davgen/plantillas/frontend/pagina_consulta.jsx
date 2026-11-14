// __CLASE__Page.jsx — GENERADO por davgen (NO editar a mano: se regenera).
// Página de SOLO CONSULTA de __TABLA__ (configurada en solo_consulta):
// el dominio escribe esta tabla mediante sus propios procedimientos, así
// que aquí solo hay listado paginado + búsqueda (sin alta/edición/baja).
import { useCallback, useEffect, useState } from 'react'
import { __SRV__ as servicio } from '../../services/__SRV__'

const TITULO = '__TITULO__'
const PK = '__PK__'
const CON_BUSQUEDA = __CON_BUSQUEDA__
const COLUMNAS = [
__COLUMNAS__
]

export default function __CLASE__Page() {
  const [items, setItems] = useState([])
  const [cargando, setCargando] = useState(true)
  const [errorCarga, setErrorCarga] = useState('')
  const [busqueda, setBusqueda] = useState('')

  const cargar = useCallback(async (texto = '') => {
    setCargando(true)
    setErrorCarga('')
    try {
      const { items: filas } = await (CON_BUSQUEDA ? servicio.listar(texto) : servicio.listar())
      setItems(filas)
    } catch (error) {
      setErrorCarga(error.message)
    } finally {
      setCargando(false)
    }
  }, [])

  // carga inicial (mismo patrón que ProductosPage; la regla nueva de
  // react-hooks lo marca, pero aquí es intencional)
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { cargar() }, [cargar])

  function buscar(e) {
    e.preventDefault()
    cargar(busqueda)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{TITULO}</h1>
        <span className="badge badge-ghost">solo consulta</span>
      </div>

      {CON_BUSQUEDA && (
        <form onSubmit={buscar} className="join">
          <input
            type="search"
            className="input input-bordered join-item w-64"
            placeholder="Buscar…"
            aria-label={`Buscar en ${TITULO}`}
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
          <button type="submit" className="btn join-item">Buscar</button>
        </form>
      )}

      <div className="card bg-base-100 shadow-sm">
        <div className="card-body p-0 sm:p-2">
          {cargando ? (
            <div className="space-y-2 p-4" role="status" aria-label="Cargando">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="skeleton h-10 w-full" />
              ))}
            </div>
          ) : errorCarga ? (
            <div className="p-6 text-center">
              <p role="alert" className="mb-3 text-error"><span aria-hidden="true">⚠ </span>{errorCarga}</p>
              <button className="btn btn-sm" onClick={() => cargar(busqueda)}>Reintentar</button>
            </div>
          ) : items.length === 0 ? (
            <div className="p-8 text-center text-base-content/60">
              {busqueda ? 'Sin resultados para esa búsqueda.' : 'Sin registros.'}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table">
                <caption className="sr-only">{TITULO}</caption>
                <thead>
                  <tr>
                    {COLUMNAS.map((c) => (
                      <th key={c.campo} scope="col">{c.etiqueta}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {items.map((r) => (
                    <tr key={r[PK]} className="hover">
                      {COLUMNAS.map((c) => (
                        <td key={c.campo}>{String(r[c.alterno] ?? r[c.campo] ?? '')}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
