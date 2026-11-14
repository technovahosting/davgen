"""gen_tema.py — tema claro / oscuro / del sistema para el frontend generado.

Igual que `gen_google.py`: archivos que se regeneran SIEMPRE y son ADITIVOS
(no pisan `App.jsx`, que es del usuario), para que el selector de tema llegue
también a los proyectos que ya existían:

    src/services/tema.js
    src/components/generados/SelectorTema.jsx
    src/components/generados/LEEME-TEMA.md

El `App.jsx` de un proyecto nuevo ya los trae montados y usa los colores
semánticos de daisyUI, así que toda la aplicación acompaña el tema.
"""
import os
from typing import Dict, List

from .plantillas import cargar as _plantilla

_NOTA = ("// GENERADO por davgen — se regenera en cada corrida: no editar.\n"
         "// Para cambiarlo: `davgen plantillas copiar tema/<archivo>`.\n")

_TEMA_JS = _NOTA + _plantilla('tema/tema.js', __name__, '_TEMA_JS')
_SELECTOR = _NOTA + _plantilla('tema/selector_tema.jsx', __name__, '_SELECTOR')
_LEEME = _plantilla('tema/leeme.md', __name__, '_LEEME')


def generar_tema(cfg: Dict, carpeta_src: str) -> List[str]:
    """Escribe los archivos del tema en `carpeta_src` (el src/ del proyecto
    React). Devuelve las rutas escritas."""
    servicios = os.path.join(carpeta_src, 'services')
    comps = os.path.join(carpeta_src, 'components', 'generados')
    archivos = {
        os.path.join(servicios, 'tema.js'): _TEMA_JS,
        os.path.join(comps, 'SelectorTema.jsx'): _SELECTOR,
        os.path.join(comps, 'LEEME-TEMA.md'): _LEEME,
    }
    rutas = []
    for ruta, contenido in archivos.items():
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
            f.write(contenido)
        rutas.append(ruta)
    return rutas
