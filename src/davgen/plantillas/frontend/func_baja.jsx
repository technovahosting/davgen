
  async function confirmarBaja() {
    setOcupado(true)
    try {
      await servicio.desactivar(aBaja[PK])
      setAviso(`${TITULO} dado de baja`)
      setABaja(null)
      cargar(busqueda)
    } catch (error) {
      setAviso(`No se pudo dar de baja: ${error.message}`)
    } finally {
      setOcupado(false)
    }
  }
