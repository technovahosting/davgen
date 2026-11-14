"""
gen_prompts.py — prompts de IA para el desarrollo del proyecto.

Genera en {raiz}\\_prompts\\ un prompt listo para copiar en una IA por cada
fase donde el usuario produce artefactos a mano: el mockup (fase 1), las
tablas de negocio (fase 2, tipo=bd), los SPs de dominio y la
personalización del código generado. El token __MODULO__ se sustituye por
el módulo de _configtotal.ini (o queda como {modulo} en proyecto nuevo).
"""
import os
from typing import List
from .plantillas import cargar as _plantilla

_PROMPT_MOCKUP = _plantilla('prompts/prompt_mockup.md', __name__, '_PROMPT_MOCKUP')

_PROMPT_TABLAS = _plantilla('prompts/prompt_tablas.md', __name__, '_PROMPT_TABLAS')

_PROMPT_SP_DOMINIO = _plantilla('prompts/prompt_sp_dominio.md', __name__, '_PROMPT_SP_DOMINIO')

_PROMPT_PERSONALIZACION = _plantilla('prompts/prompt_personalizacion.md', __name__, '_PROMPT_PERSONALIZACION')

_PROMPT_IMPLEMENTAR_REACT = _plantilla('prompts/prompt_implementar_react.md', __name__, '_PROMPT_IMPLEMENTAR_REACT')

_PROMPTS = [
    ('prompt-1-mockup.md',                _PROMPT_MOCKUP),
    ('prompt-2-tablas-desde-mockup.md',   _PROMPT_TABLAS),
    ('prompt-3-sp-dominio.md',            _PROMPT_SP_DOMINIO),
    ('prompt-4-personalizacion.md',       _PROMPT_PERSONALIZACION),
    ('prompt-5-implementar-diseno-react.md', _PROMPT_IMPLEMENTAR_REACT),
]

_LEEME = _plantilla('prompts/leeme.md', __name__, '_LEEME')


_AVISO_NO_MODIFICAR = _plantilla('prompts/aviso_no_modificar.md', __name__, '_AVISO_NO_MODIFICAR')


def escribir_avisos_no_modificar(carpetas: List[str]) -> List[str]:
    """Deja un _NO-MODIFICAR.md en cada carpeta de código generado."""
    rutas = []
    for carpeta in carpetas:
        if not carpeta or not os.path.isdir(carpeta):
            continue
        ruta = os.path.join(carpeta, '_NO-MODIFICAR.md')
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(_AVISO_NO_MODIFICAR)
        rutas.append(ruta)
    return rutas


def generar_prompts(raiz: str, modulo: str = '') -> List[str]:
    """Escribe los prompts en {raiz}\\_prompts\\ y devuelve sus rutas.
    Sin módulo (proyecto nuevo) deja el placeholder {modulo} visible."""
    carpeta = os.path.join(raiz, '_prompts')
    os.makedirs(carpeta, exist_ok=True)
    mod = modulo or '{modulo}'
    rutas = []
    for nombre, contenido in _PROMPTS + [('leeme.md', _LEEME)]:
        ruta = os.path.join(carpeta, nombre)
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido.replace('__MODULO__', mod))
        rutas.append(ruta)
    return rutas
