// __CLASE__Page.jsx — GENERADO por davgen (NO editar a mano: se regenera).
// CRUD de __TABLA__ sobre __SRV__.js (API davgen: sel/get/add/upd/del).
// Patrón de ProductosPage: listado + búsqueda + modal de alta/edición +
// confirmación de baja lógica + toast de aviso (daisyUI).
import { useCallback, useEffect, useState } from 'react'
import { __SRV__ as servicio } from '../../services/__SRV__'
__IMPORT_RELACIONES__
const TITULO = '__TITULO__'
const PK = '__PK__'
const TIENE_ACTIVO = __TIENE_ACTIVO__
const CON_BUSQUEDA = __CON_BUSQUEDA__
const CAMPOS = [
__CAMPOS__
]
const COLUMNAS = [
__COLUMNAS__
]

function valorInicial() {
  return { __VALOR_INICIAL__ }
}

export default function __CLASE__Page() {
  const [items, setItems] = useState([])
  const [cargando, setCargando] = useState(true)
  const [errorCarga, setErrorCarga] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [filtro, setFiltro] = useState('')
  const [pagina, setPagina] = useState(1)
  const [porPagina, setPorPagina] = useState(25)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [totalItems, setTotalItems] = useState(0)
  const [verInactivos, setVerInactivos] = useState(false)
  const [formulario, setFormulario] = useState(null) // null | objeto (alta/edición)
__ESTADO_BAJA__  const [ocupado, setOcupado] = useState(false)
  const [aviso, setAviso] = useState('')

  const cargar = useCallback(async (txt, pg, pp) => {
    setCargando(true)
    setErrorCarga('')
    try {
      const { items: filas, paginacion } = await (CON_BUSQUEDA
        ? servicio.listar(txt, pg, pp)
        : servicio.listar(pg, pp))
      setItems(filas)
      const pag = paginacion || {}
      setTotalPaginas(pag.ultima_pagina || pag.last_page || 1)
      setTotalItems(pag.total || 0)
    } catch (error) {
      setErrorCarga(error.message)
    } finally {
      setCargando(false)
    }
  }, [])

  // recarga al cambiar filtro de búsqueda, página o filas por página
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { cargar(filtro, pagina, porPagina) }, [filtro, pagina, porPagina])

  useEffect(() => {
    if (!aviso) return
    const temporizador = setTimeout(() => setAviso(''), 4000)
    return () => clearTimeout(temporizador)
  }, [aviso])

  function buscar(e) {
    e.preventDefault()
    setFiltro(busqueda)
    setPagina(1)
  }

  async function guardar(e) {
    e.preventDefault()
    setOcupado(true)
    try {
      if (formulario[PK]) {
        // el upd de davgen sobreescribe TODO: se envía el registro completo
        await servicio.actualizar(formulario)
        setAviso(`${TITULO} actualizado`)
      } else {
        await servicio.crear(formulario)
        setAviso(`${TITULO} creado`)
      }
      setFormulario(null)
      cargar(busqueda)
    } catch (error) {
      setAviso(`Error al guardar: ${error.message}`)
    } finally {
      setOcupado(false)
    }
  }

__FUNCIONES_EXTRA__
  const visibles = TIENE_ACTIVO ? items.filter((r) => verInactivos || r.activo) : items

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{TITULO}</h1>
        <button className="btn btn-primary" onClick={() => setFormulario(valorInicial())}>
          + Nuevo
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
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
        {TIENE_ACTIVO && (
          <label className="label cursor-pointer gap-2">
            <input
              type="checkbox"
              className="checkbox checkbox-sm"
              checked={verInactivos}
              onChange={(e) => setVerInactivos(e.target.checked)}
            />
            <span className="label-text">Mostrar inactivos</span>
          </label>
        )}
      </div>

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
          ) : visibles.length === 0 ? (
            <div className="p-8 text-center text-base-content/60">
              {busqueda ? 'Sin resultados para esa búsqueda.' : 'Sin registros. Crea el primero con “+ Nuevo”.'}
            </div>
          ) : (
            <>
            <div className="overflow-x-auto">
              <table className="table table-sm">
                <caption className="sr-only">{TITULO}</caption>
                <thead>
                  <tr>
                    {COLUMNAS.map((c) => (
                      <th key={c.campo} scope="col">{c.etiqueta}</th>
                    ))}
                    {TIENE_ACTIVO && <th scope="col">Estado</th>}
                    <th scope="col" className="text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {visibles.map((r) => (
                    <tr key={r[PK]} className="hover">
                      {COLUMNAS.map((c) => (
                        <td key={c.campo} className={TIENE_ACTIVO && !r.activo ? 'text-base-content/40' : ''}>
                          {String(r[c.alterno] ?? r[c.campo] ?? '')}
                        </td>
                      ))}
                      {TIENE_ACTIVO && (
                        <td>
                          {r.activo ? (
                            <span className="badge badge-success badge-sm">Activo</span>
                          ) : (
                            <span className="badge badge-ghost badge-sm">Inactivo</span>
                          )}
                        </td>
                      )}
                      <td className="text-right">
                        <div className="join">
                          <button className="btn btn-ghost btn-sm join-item" aria-label={`Editar ${TITULO} ${r[PK]}`} onClick={() => setFormulario({ ...r })}>
                            Editar
                          </button>__BOTONES_EXTRA__
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 border-t p-2 text-sm">
              <span className="text-base-content/60">
                {totalItems > 0
                  ? `Mostrando ${(pagina - 1) * porPagina + 1}–${Math.min(pagina * porPagina, totalItems)} de ${totalItems}`
                  : `${visibles.length} registro(s)`}
              </span>
              <div className="join">
                <button className="join-item btn btn-xs" disabled={pagina <= 1} aria-label="Página anterior"
                  onClick={() => setPagina((p) => p - 1)}>«</button>
                <span className="join-item btn btn-xs btn-disabled no-animation" aria-live="polite">
                  <span className="sr-only">Página </span>{pagina} / {totalPaginas}
                </span>
                <button className="join-item btn btn-xs" disabled={pagina >= totalPaginas} aria-label="Página siguiente"
                  onClick={() => setPagina((p) => p + 1)}>»</button>
              </div>
              <select className="select select-xs select-bordered" aria-label="Filas por página"
                value={porPagina}
                onChange={(e) => { setPorPagina(Number(e.target.value)); setPagina(1) }}>
                {[10, 25, 50, 100].map((n) => (
                  <option key={n} value={n}>{n} / pág.</option>
                ))}
              </select>
            </div>
            </>
          )}
        </div>
      </div>

      {formulario !== null && (
        <div className="modal modal-open" role="dialog" aria-modal="true" aria-labelledby="titulo-formulario"
          onKeyDown={(e) => { if (e.key === 'Escape') setFormulario(null) }}>
          <div className="modal-box">
            <h3 id="titulo-formulario" className="mb-4 text-lg font-bold">
              {formulario[PK] ? `Editar ${TITULO}` : `Nuevo ${TITULO}`}
            </h3>
            <form onSubmit={guardar} className="space-y-3">
              {CAMPOS.map((c, i) => (
                <label key={c.campo} className="form-control w-full">
                  <span className="label-text mb-1">{c.etiqueta}</span>
                  {c.tipo === 'select' ? (
                    <select
                      autoFocus={i === 0}
                      className="select select-bordered w-full"
                      value={formulario[c.campo] ?? ''}
                      onChange={(e) => setFormulario({ ...formulario, [c.campo]: e.target.value })}
                      required={c.requerido}
                    >
                      <option value="">— seleccionar —</option>
                      {(c.opciones || []).map((op) => (
                        <option key={op} value={op}>{op.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  ) : c.tipo === 'textarea' ? (
                    <textarea
                      autoFocus={i === 0}
                      className="textarea textarea-bordered w-full"
                      value={formulario[c.campo] ?? ''}
                      onChange={(e) => setFormulario({ ...formulario, [c.campo]: e.target.value })}
                      required={c.requerido}
                      rows={3}
                    />
                  ) : c.tipo === 'select_relacion' ? (
                    <SelectRelacion
                      servicio={c.servicio}
                      nombre={c.campo}
                      valor={formulario[c.campo] ?? ''}
                      onChange={(campo, val) => setFormulario({ ...formulario, [campo]: Number(val) })}
                      label={c.etiqueta}
                    />
                  ) : (
                    <input
                      type={c.tipo}
                      autoFocus={i === 0}
                      step={c.paso || undefined}
                      className="input input-bordered w-full"
                      value={formulario[c.campo] ?? ''}
                      onChange={(e) => setFormulario({ ...formulario, [c.campo]: e.target.value })}
                      required={c.requerido}
                    />
                  )}
                </label>
              ))}
              <div className="modal-action">
                <button type="button" className="btn" onClick={() => setFormulario(null)}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary" disabled={ocupado}>
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

__MODAL_BAJA__      {aviso && (
        <div className="toast toast-top toast-end z-50" role={aviso.startsWith('Error') ? 'alert' : 'status'}>
          <div className={`alert ${aviso.startsWith('Error') ? 'alert-error' : 'alert-success'} py-2 text-sm shadow-lg`}>{aviso}</div>
        </div>
      )}
    </div>
  )
}
