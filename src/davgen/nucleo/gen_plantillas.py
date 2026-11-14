"""
gen_plantillas.py — documentos ESTÁNDAR mínimos del proyecto + leeme.html.

Para cualquier proyecto en blanco se copian 4 plantillas (UNA por fase que
el usuario completa: requisitos, mockups, base de datos, pruebas) — solo
si no existen, porque el usuario las llena — y un `leeme.html` interactivo
(guía navegable: qué configurar en _configtotal.ini, el proceso, las reglas
y los prompts), que sí se regenera en cada corrida.
"""
import os
from typing import List

from .version import AUTOR, VERSION
from .plantillas import cargar as _plantilla

_PIE = f"\n---\n_Plantilla davgen v{VERSION} · Autor: {AUTOR}_\n"

_REQUISITOS = _plantilla('documentos/requisitos.md', __name__, '_REQUISITOS')

_MOCKUPS = _plantilla('documentos/mockups.md', __name__, '_MOCKUPS')

_BASE_DATOS = _plantilla('documentos/base_datos.md', __name__, '_BASE_DATOS')

_PLAN_PRUEBAS = _plantilla('documentos/plan_pruebas.md', __name__, '_PLAN_PRUEBAS')

# (carpeta destino que empieza con…, nombre del archivo, contenido)
_PLANTILLAS = [
    ('00-requisitos',    'requisitos.md',      _REQUISITOS),
    ('01-mockups',       'mockups.md',         _MOCKUPS),
    ('02-base',          'base-de-datos.md',   _BASE_DATOS),
    ('05-test',          'plan-de-pruebas.md', _PLAN_PRUEBAS),
]


def generar_plantillas(raiz: str) -> List[str]:
    """Copia las plantillas estándar a las carpetas del proyecto — SOLO si
    no existen (el usuario las completa: nunca se sobrescriben)."""
    try:
        carpetas = {d.lower(): os.path.join(raiz, d) for d in os.listdir(raiz)
                    if os.path.isdir(os.path.join(raiz, d))}
    except OSError:
        return []
    creadas = []
    for prefijo, nombre, contenido in _PLANTILLAS:
        destino_dir = next((ruta for nom, ruta in sorted(carpetas.items())
                            if nom.startswith(prefijo)), None)
        if not destino_dir:
            continue
        ruta = os.path.join(destino_dir, nombre)
        if os.path.isfile(ruta):
            continue                      # el usuario ya la está llenando
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido + _PIE)
        creadas.append(ruta)
    return creadas


# ═════════════════════════════════════════════
#  leeme.html — guía interactiva del proyecto
# ═════════════════════════════════════════════
_LEEME_HTML = _plantilla('documentos/leeme.html', __name__, '_LEEME_HTML')


def generar_leeme_html(raiz: str) -> str:
    """Escribe (o regenera) la guía interactiva leeme.html en la raíz."""
    ruta = os.path.join(raiz, 'leeme.html')
    contenido = (_LEEME_HTML.replace('__VERSION__', VERSION)
                            .replace('__AUTOR__', AUTOR))
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(contenido)
    return ruta


_LEEME_MD = _plantilla('documentos/davgen_leeme.md', __name__, '_LEEME_MD')


def generar_leeme_md(raiz: str) -> str:
    """Escribe (o regenera) la guía rápida _davgen.leeme.md en la raíz."""
    ruta = os.path.join(raiz, '_davgen.leeme.md')
    contenido = (_LEEME_MD.replace('__VERSION__', VERSION)
                          .replace('__AUTOR__', AUTOR))
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(contenido)
    return ruta


# ═════════════════════════════════════════════
#  CONFIGURAR-GOOGLE-AUTH.md — acción OPCIONAL por proyecto
# ═════════════════════════════════════════════
_GUIA_GOOGLE = _plantilla('documentos/configurar_google_auth.md', __name__, '_GUIA_GOOGLE')


def generar_guia_google(raiz: str) -> str:
    """Escribe (o regenera) CONFIGURAR-GOOGLE-AUTH.md en la raíz del proyecto:
    guía paso a paso para habilitar el login con Google (acción OPCIONAL)."""
    ruta = os.path.join(raiz, 'CONFIGURAR-GOOGLE-AUTH.md')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(_GUIA_GOOGLE + _PIE)
    return ruta
