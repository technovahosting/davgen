"""
gen_google.py — piezas de FRONTEND para el login con Google y la cola de
aprobación de accesos. SIEMPRE se regeneran (no son "solo si faltan").

Por qué existe este módulo aparte de gen_servicios:
  `authService.js` y `App.jsx` se escriben SOLO SI NO EXISTEN (son
  personalizables). Cuando v4.34 agregó `loginConGoogle`, `getConfigPublica` y
  `accesos*` a la plantilla de `authService.js`, los proyectos que ya tenían ese
  archivo NUNCA los recibieron: había que copiarlos a mano o borrar y regenerar
  (documentado como pendiente en CLAUDE.md). Lo mismo con el botón en App.jsx.
  Resultado: Google venía "activado de fábrica" en la BD (google_auth_activo=1 +
  google_client_id sembrados) pero el frontend no tenía con qué usarlo.

La solución es que Google NO viva en archivos personalizables. Estos archivos
son aditivos y autosuficientes (no dependen de authService.js):

  {src}/services/googleAuthService.js            — /auth/google, /config-publica, /accesos/*
  {src}/components/generados/BotonGoogle.jsx     — botón oficial de Google (GIS)
  {src}/components/generados/PanelAccesosPendientes.jsx — cola de aprobación (admin)
  {src}/components/generados/LEEME-GOOGLE.md     — cómo montarlos (2 líneas)

Se generan SIEMPRE (no dependen del flag opcional `componentes_react`): Google
está activo por defecto en la BD, así que el frontend tiene que poder usarlo.
El Client ID se lee en RUNTIME desde POST /config-publica (única fuente = la
BD), así que activar/cambiar Google NO exige recompilar el frontend.
"""
import os
from typing import Dict, List
from .plantillas import cargar as _plantilla

_NOTA = ("// GENERADO por davgen — NO editar (se regenera).\n"
         "// El Client ID se lee en runtime desde POST /config-publica\n"
         "// (tbl_seg_parametro): activar/cambiar Google NO exige recompilar.\n")


# ═════════════════════════════════════════════
#  services/googleAuthService.js
# ═════════════════════════════════════════════
# Autosuficiente a propósito: usa post()/sesion de ./api (que sí es generado y
# estable) y NO importa authService.js, que en muchos proyectos está escrito a
# mano y puede no tener estos métodos.
_GOOGLE_SERVICE = _NOTA + _plantilla('google/google_auth_service.js', __name__, '_GOOGLE_SERVICE')


# ═════════════════════════════════════════════
#  components/generados/BotonGoogle.jsx
# ═════════════════════════════════════════════
# OJO: string normal de Python, NO f-string — el JSX usa ${...} literal.
_BOTON_GOOGLE = _NOTA + _plantilla('google/boton_google.jsx', __name__, '_BOTON_GOOGLE')


# ═════════════════════════════════════════════
#  components/generados/PanelAccesosPendientes.jsx
# ═════════════════════════════════════════════
_PANEL_ACCESOS = _NOTA + _plantilla('google/panel_accesos_pendientes.jsx', __name__, '_PANEL_ACCESOS')


# ═════════════════════════════════════════════
#  LEEME-GOOGLE.md
# ═════════════════════════════════════════════
_LEEME = _plantilla('google/leeme.md', __name__, '_LEEME')


def generar_google(cfg: Dict, carpeta_src: str) -> List[str]:
    """Escribe el service y los componentes de Google en {carpeta_src}.
    SIEMPRE sobreescribe (son generados). Devuelve las rutas escritas."""
    servicios = os.path.join(carpeta_src, 'services')
    comps = os.path.join(carpeta_src, 'components', 'generados')
    os.makedirs(servicios, exist_ok=True)
    os.makedirs(comps, exist_ok=True)

    archivos = {
        os.path.join(servicios, 'googleAuthService.js'): _GOOGLE_SERVICE,
        os.path.join(comps, 'BotonGoogle.jsx'): _BOTON_GOOGLE,
        os.path.join(comps, 'PanelAccesosPendientes.jsx'): _PANEL_ACCESOS,
        os.path.join(comps, 'LEEME-GOOGLE.md'): _LEEME,
    }
    rutas = []
    for ruta, contenido in archivos.items():
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido)
        rutas.append(ruta)
    return rutas
