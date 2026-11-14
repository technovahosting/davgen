
  async function reactivar(registro) {
    try {
      await servicio.reactivar(registro)
      setAviso(`${TITULO} reactivado`)
      cargar(busqueda)
    } catch (error) {
      setAviso(`No se pudo reactivar: ${error.message}`)
    }
  }
