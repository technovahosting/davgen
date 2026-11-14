# Componentes y hooks reutilizables (generados)

> ⚠ Generados por davgen — **NO editar** (se regeneran). Son genéricos: úsalos
> desde tus páginas para escribir mucho menos código.

| Archivo | Qué hace |
|---|---|
| `hooks/useCrud.js` | Estado + listar/crear/actualizar/desactivar de un servicio |
| `hooks/useAuth.js` | login (+2FA), logout y usuario actual |
| `components/generados/DataTable.jsx` | Tabla genérica con acciones |
| `components/generados/CampoFormulario.jsx` | Input por tipo (text, number, date, select…) |
| `components/generados/SelectRelacion.jsx` | Dropdown de clave foránea (carga la tabla relacionada) |
| `components/generados/Paginacion.jsx` | Controles de paginación |

## Ejemplo

```jsx
import { useCrud } from '../hooks/useCrud'
import DataTable from '../components/generados/DataTable'
import Paginacion from '../components/generados/Paginacion'
import { productoService } from '../services/productoService'

export default function Productos() {
  const { items, paginacion, cargando, error, cargar, eliminar } = useCrud(productoService)
  return (
    <>
      {error && <p className="error">{error}</p>}
      <DataTable
        columnas={[{ campo: 'nombre', titulo: 'Nombre' }, { campo: 'precio', titulo: 'Precio' }]}
        datos={items}
        cargando={cargando}
        onEliminar={(f) => eliminar(f.id)}
      />
      <Paginacion paginacion={paginacion} onCambiar={(p) => cargar('', p)} />
    </>
  )
}
```
