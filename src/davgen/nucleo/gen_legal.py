"""gen_legal.py — privacidad y términos de uso del frontend generado.

Igual que `gen_tema.py`: archivos que se regeneran SIEMPRE y son ADITIVOS (no
pisan `App.jsx`), para que lleguen también a los proyectos que ya existían:

    src/components/generados/AvisoLegal.jsx
    src/components/generados/LEEME-LEGAL.md

Los textos describen lo que el sistema generado hace con los datos (cuenta,
bitácora, códigos, almacenamiento local) y toman de `[legal]` quién responde,
cómo contactarlo y cuánto se conserva la bitácora. No se genera aviso de
cookies porque el sistema no usa ninguna (ver LEEME-LEGAL.md).
"""
import os
from typing import Dict, List

from .plantillas import cargar as _plantilla

_NOTA = ("// GENERADO por davgen — se regenera en cada corrida: no editar.\n"
         "// Para cambiarlo: `davgen plantillas copiar legal/<archivo>`.\n")

_AVISO = _NOTA + _plantilla('legal/aviso_legal.jsx', __name__, '_AVISO')
_LEEME = _plantilla('legal/leeme.md', __name__, '_LEEME')

RETENCION_BITACORA_DIAS = 365       # valor por defecto de [legal] retencion_bitacora_dias


def _texto_js(valor: str) -> str:
    """`valor` listo para ir dentro de una cadena JS entre comillas simples y
    mostrarse como texto: sin los caracteres que cerrarían la cadena o el JSX."""
    return ''.join(c for c in (valor or '') if c not in '\'"`\\{}<>\r\n').strip()


def generar_legal(cfg: Dict, carpeta_src: str) -> List[str]:
    """Escribe el aviso legal en `carpeta_src` (el src/ del proyecto React).
    Devuelve las rutas escritas."""
    legal = cfg.get('legal', {})
    aviso = (_AVISO
             .replace('__NOMBRE__', _texto_js(cfg.get('nombre', '')) or 'este sistema')
             .replace('__RESPONSABLE__', _texto_js(legal.get('responsable', '')))
             .replace('__CONTACTO__', _texto_js(legal.get('contacto', '')))
             .replace('__JURISDICCION__', _texto_js(legal.get('jurisdiccion', '')))
             .replace('__ALOJAMIENTO__', _texto_js(legal.get('alojamiento', '')))
             .replace('__VIGENTE_DESDE__', _texto_js(legal.get('vigente_desde', '')))
             .replace('__DIAS_BITACORA__',
                      str(int(legal.get('retencion_bitacora_dias', RETENCION_BITACORA_DIAS))))
             .replace('__CON_GOOGLE__',
                      'true' if cfg.get('google_auth_activo') else 'false'))
    comps = os.path.join(carpeta_src, 'components', 'generados')
    archivos = {
        os.path.join(comps, 'AvisoLegal.jsx'): aviso,
        os.path.join(comps, 'LEEME-LEGAL.md'): _LEEME,
    }
    rutas = []
    for ruta, contenido in archivos.items():
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
            f.write(contenido)
        rutas.append(ruta)
    return rutas
