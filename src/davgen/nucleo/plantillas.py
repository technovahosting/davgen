"""plantillas.py — las plantillas son DATOS, no código.

Hasta la v4 casi la mitad del generador eran PHP, JSX, SQL y Markdown escritos
dentro de literales de Python. Cambiar el aspecto de una página generada
obligaba a editar el código fuente del generador. Desde la v5 cada plantilla es
un archivo bajo `davgen/plantillas/<grupo>/<nombre>.<ext>` y se resuelve con
una cadena de dos eslabones:

    1. {raíz del proyecto}/_plantillas/<grupo>/<nombre>.<ext>   ← gana
    2. la plantilla que trae el paquete                          ← por defecto

Para personalizar una plantilla no se toca davgen: se copia al proyecto
(`davgen plantillas copiar <grupo>/<nombre>.<ext>`), se edita y se regenera.

El motor de sustitución NO cambia: cada módulo sigue reemplazando sus
marcadores (`__TOKEN__`, o `{campo}` con `str.format`) exactamente como antes,
así que la salida es idéntica byte a byte mientras no haya plantillas propias.

Uso en un módulo generador:

    from .plantillas import cargar as _plantilla
    _AUTH = _plantilla('backend/auth_controller.php', __name__, '_AUTH')

`cargar` registra (módulo, nombre) para que `usar_proyecto` pueda recargar el
módulo cuando el proyecto trae una versión propia de esa plantilla.
"""
import importlib
import os
import shutil
import sys
from typing import Dict, List, Optional, Tuple

DIR_PAQUETE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           'plantillas')
CARPETA_PROYECTO = '_plantillas'

_dir_proyecto: Optional[str] = None
# ruta relativa ('backend/x.php') -> lista de (módulo, nombre de la constante)
_registro: Dict[str, List[Tuple[str, str]]] = {}


def _ruta_paquete(ruta: str) -> str:
    return os.path.join(DIR_PAQUETE, *ruta.split('/'))


def _ruta_proyecto(ruta: str) -> Optional[str]:
    if not _dir_proyecto:
        return None
    return os.path.join(_dir_proyecto, *ruta.split('/'))


def _leer(archivo: str) -> str:
    # newline='' conservaría los \r\n; aquí se quiere lo contrario: que una
    # plantilla guardada con CRLF por un editor de Windows genere lo mismo.
    with open(archivo, encoding='utf-8-sig') as f:
        return f.read()


def origen(ruta: str) -> str:
    """'proyecto' si el proyecto trae su propia versión, si no 'paquete'."""
    propia = _ruta_proyecto(ruta)
    return 'proyecto' if propia and os.path.isfile(propia) else 'paquete'


def cargar(ruta: str, modulo: Optional[str] = None,
           nombre: Optional[str] = None) -> str:
    """Texto de la plantilla `ruta` (relativa, con '/'). Gana la del proyecto."""
    if modulo and nombre:
        usos = _registro.setdefault(ruta, [])
        if (modulo, nombre) not in usos:
            usos.append((modulo, nombre))
    propia = _ruta_proyecto(ruta)
    if propia and os.path.isfile(propia):
        return _leer(propia)
    archivo = _ruta_paquete(ruta)
    if not os.path.isfile(archivo):
        raise FileNotFoundError(
            f"Falta la plantilla «{ruta}» del paquete davgen ({archivo}). "
            "La instalación está incompleta: reinstalar con `pip install davgen`.")
    return _leer(archivo)


def listar() -> List[str]:
    """Todas las plantillas del paquete, como rutas relativas ordenadas."""
    rutas = []
    for base, _dirs, archivos in os.walk(DIR_PAQUETE):
        for a in archivos:
            rel = os.path.relpath(os.path.join(base, a), DIR_PAQUETE)
            rutas.append(rel.replace(os.sep, '/'))
    return sorted(rutas)


def propias(raiz_proyecto: str) -> List[str]:
    """Plantillas que el proyecto sobrescribe (existen en su _plantillas/)."""
    carpeta = os.path.join(raiz_proyecto, CARPETA_PROYECTO)
    if not os.path.isdir(carpeta):
        return []
    conocidas = set(listar())
    encontradas = []
    for base, _dirs, archivos in os.walk(carpeta):
        for a in archivos:
            rel = os.path.relpath(os.path.join(base, a), carpeta).replace(os.sep, '/')
            if rel in conocidas:
                encontradas.append(rel)
    return sorted(encontradas)


def desconocidas(raiz_proyecto: str) -> List[str]:
    """Archivos en _plantillas/ que NO corresponden a ninguna plantilla del
    paquete (nombre mal escrito o plantilla de otra versión): se ignorarían en
    silencio, así que el CLI los avisa."""
    carpeta = os.path.join(raiz_proyecto, CARPETA_PROYECTO)
    if not os.path.isdir(carpeta):
        return []
    conocidas = set(listar())
    extra = []
    for base, _dirs, archivos in os.walk(carpeta):
        for a in archivos:
            rel = os.path.relpath(os.path.join(base, a), carpeta).replace(os.sep, '/')
            if rel not in conocidas and not a.lower().startswith(('leeme', 'readme')):
                extra.append(rel)
    return sorted(extra)


def usar_proyecto(raiz_proyecto: Optional[str]) -> List[str]:
    """Activa (o desactiva con None) las plantillas propias de un proyecto.

    Las constantes de los módulos generadores se evalúan al importarlos, así
    que se RECARGAN los módulos afectados: recargar vuelve a ejecutar el módulo
    sobre el mismo diccionario de globales, con lo que también se actualiza
    todo lo que derive de una plantilla. Devuelve las plantillas propias.
    """
    global _dir_proyecto
    anteriores = set(propias(os.path.dirname(_dir_proyecto))) if _dir_proyecto else set()
    nuevas: List[str] = []
    if raiz_proyecto:
        carpeta = os.path.join(raiz_proyecto, CARPETA_PROYECTO)
        _dir_proyecto = carpeta if os.path.isdir(carpeta) else None
        nuevas = propias(raiz_proyecto) if _dir_proyecto else []
    else:
        _dir_proyecto = None
    modulos = []
    for ruta in sorted(anteriores | set(nuevas)):
        for modulo, _nombre in _registro.get(ruta, []):
            if modulo not in modulos:
                modulos.append(modulo)
    for modulo in modulos:
        if modulo in sys.modules:
            importlib.reload(sys.modules[modulo])
    return nuevas


def copiar_al_proyecto(ruta: str, raiz_proyecto: str,
                       sobrescribir: bool = False) -> str:
    """Copia la plantilla del paquete a {raíz}/_plantillas/ para editarla.
    Devuelve la ruta destino. Lanza FileExistsError si ya existe."""
    archivo = _ruta_paquete(ruta)
    if not os.path.isfile(archivo):
        raise FileNotFoundError(ruta)
    destino = os.path.join(raiz_proyecto, CARPETA_PROYECTO, *ruta.split('/'))
    if os.path.exists(destino) and not sobrescribir:
        raise FileExistsError(destino)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    shutil.copyfile(archivo, destino)
    return destino


def usos(ruta: str) -> List[Tuple[str, str]]:
    """(módulo, constante) que consumen la plantilla — para documentación."""
    return list(_registro.get(ruta, []))
