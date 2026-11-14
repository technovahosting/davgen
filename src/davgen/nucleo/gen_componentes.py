"""
gen_componentes.py — hooks y componentes React reutilizables OPCIONALES
([generar] componentes_react=si).

Son GENÉRICOS (no dependen de una tabla): reducen el código de las páginas y
resuelven el caso de las claves foráneas. Se escriben en:
  {src}/hooks/useCrud.js, useAuth.js
  {src}/components/generados/DataTable.jsx, CampoFormulario.jsx,
                            SelectRelacion.jsx, Paginacion.jsx
Sin dependencias extra (solo React + el cliente ./services/api ya generado).
"""
import os
from typing import Dict, List
from .plantillas import cargar as _plantilla

_NOTA = ("// GENERADO por davgen — NO editar (se regenera). Componente "
         "reutilizable.\n")

_USE_CRUD = _NOTA + _plantilla('componentes/use_crud.js', __name__, '_USE_CRUD')

_USE_AUTH = _NOTA + _plantilla('componentes/use_auth.js', __name__, '_USE_AUTH')

_DATATABLE = _NOTA + _plantilla('componentes/data_table.jsx', __name__, '_DATATABLE')

_CAMPO = _NOTA + _plantilla('componentes/campo_formulario.jsx', __name__, '_CAMPO')

_SELECT_RELACION = _NOTA + _plantilla('componentes/select_relacion.jsx', __name__, '_SELECT_RELACION')

_PAGINACION = _NOTA + _plantilla('componentes/paginacion.jsx', __name__, '_PAGINACION')

_LEEME = _plantilla('componentes/leeme.md', __name__, '_LEEME')


def generar_componentes(cfg: Dict, carpeta_src: str) -> List[str]:
    """Escribe hooks y componentes genéricos en {carpeta_src}. Devuelve rutas."""
    hooks = os.path.join(carpeta_src, 'hooks')
    comps = os.path.join(carpeta_src, 'components', 'generados')
    os.makedirs(hooks, exist_ok=True)
    os.makedirs(comps, exist_ok=True)

    archivos = {
        os.path.join(hooks, 'useCrud.js'): _USE_CRUD,
        os.path.join(hooks, 'useAuth.js'): _USE_AUTH,
        os.path.join(comps, 'DataTable.jsx'): _DATATABLE,
        os.path.join(comps, 'CampoFormulario.jsx'): _CAMPO,
        os.path.join(comps, 'SelectRelacion.jsx'): _SELECT_RELACION,
        os.path.join(comps, 'Paginacion.jsx'): _PAGINACION,
        os.path.join(comps, 'LEEME.md'): _LEEME,
    }
    rutas = []
    for ruta, contenido in archivos.items():
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido)
        rutas.append(ruta)
    return rutas
