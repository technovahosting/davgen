"""Empaqueta la skill «crear-sistema» en un .zip que funciona sola.

    python scripts/empaquetar_skill.py            → dist/crear-sistema.zip

El .zip lleva la carpeta de la skill y, dentro de ella, `fuente/` con el código
de davgen: quien lo descarga no necesita clonar el repositorio ni que davgen
esté publicado en ningún índice. Sirve para:

  · copiarlo descomprimido a ~/.claude/skills/        (Claude Code)
  · subirlo tal cual en la aplicación de Claude       (Configuración → Skills)

El .zip NO se versiona: se adjunta al Release de GitHub (docs/publicar.md).
"""
import os
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMBRE = 'crear-sistema'
SKILL = os.path.join(RAIZ, 'skills', NOMBRE)
# lo mínimo para que `pip install fuente/` funcione (pyproject los nombra)
FUENTE = ('pyproject.toml', 'README.md', 'LICENSE', 'AVISOS-TERCEROS.md')
OMITIR_DIRS = {'__pycache__'}
OMITIR_EXT = ('.pyc', '.pyo')
FECHA = (2020, 1, 1, 0, 0, 0)            # fija: el .zip sale idéntico cada vez


def _archivos(carpeta):
    for base, dirs, nombres in os.walk(carpeta):
        dirs[:] = sorted(d for d in dirs if d not in OMITIR_DIRS
                         and not d.endswith('.egg-info'))
        for n in sorted(nombres):
            if not n.endswith(OMITIR_EXT):
                yield os.path.join(base, n)


def contenido():
    """Pares (ruta en disco, ruta dentro del .zip), en orden estable."""
    pares = [(r, f'{NOMBRE}/' + os.path.relpath(r, SKILL).replace(os.sep, '/'))
             for r in _archivos(SKILL)]
    pares += [(os.path.join(RAIZ, n), f'{NOMBRE}/fuente/{n}') for n in FUENTE]
    src = os.path.join(RAIZ, 'src')
    pares += [(r, f'{NOMBRE}/fuente/src/' + os.path.relpath(r, src).replace(os.sep, '/'))
              for r in _archivos(os.path.join(src, 'davgen'))]
    return pares


def empaquetar(destino=None):
    destino = destino or os.path.join(RAIZ, 'dist', f'{NOMBRE}.zip')
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as z:
        for ruta, nombre in contenido():
            info = zipfile.ZipInfo(nombre, FECHA)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(ruta, 'rb') as f:
                z.writestr(info, f.read())
    return destino


if __name__ == '__main__':
    ruta = empaquetar(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f'{ruta}  ({os.path.getsize(ruta) // 1024} KB, {len(contenido())} archivos)')
