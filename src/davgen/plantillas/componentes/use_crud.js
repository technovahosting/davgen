// useCrud(servicio) — estado y operaciones CRUD para un servicio de tabla
// (listar/crear/actualizar/desactivar). Asume la firma listar(busqueda,
// pagina) de los servicios generados con columna de texto; para tablas sin
// búsqueda, llamar a cargar() y adaptar.
import { useCallback, useEffect, useState } from 'react'

export function useCrud(servicio) {
  const [items, setItems] = useState([])
  const [paginacion, setPaginacion] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  const cargar = useCallback(async (busqueda = '', pagina = 1) => {
    setCargando(true)
    setError('')
    try {
      const r = await servicio.listar(busqueda, pagina)
      setItems(r.items ?? [])
      setPaginacion(r.paginacion ?? null)
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }, [servicio])

  useEffect(() => { cargar() }, [cargar])

  const guardar = async (registro) => {
    setError('')
    try {
      if (registro.id) await servicio.actualizar(registro)
      else await servicio.crear(registro)
      await cargar()
      return true
    } catch (e) {
      setError(e.message)
      return false
    }
  }

  const eliminar = async (id) => {
    setError('')
    try {
      await servicio.desactivar(id)
      await cargar()
      return true
    } catch (e) {
      setError(e.message)
      return false
    }
  }

  return { items, paginacion, cargando, error, cargar, guardar, eliminar, setError }
}
