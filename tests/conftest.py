"""Configuración común de las pruebas del generador.

Las pruebas NO necesitan MySQL, PHP, composer, node ni red: todo corre con
`davgen generar --local` sobre un mockup de ejemplo, en carpetas temporales.
Las que pueden aprovechar una herramienta opcional (php, para validar la
sintaxis de lo generado) se saltan solas si no está instalada.
"""
import os
import shutil
import sys

import pytest

RAIZ_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ_REPO, 'src'))
sys.path.insert(0, os.path.join(RAIZ_REPO, 'scripts'))

# Fecha fija (2026-01-01 00:00 UTC): la salida es reproducible byte a byte.
os.environ['SOURCE_DATE_EPOCH'] = '1767225600'
os.environ['DAVGEN_NO_ABRIR'] = '1'

import generar_ejemplo  # noqa: E402  (scripts/generar_ejemplo.py)

CLAVE_PRUEBA = 'ClaveDePrueba2026'


@pytest.fixture(autouse=True)
def _plantillas_limpias():
    """Ninguna prueba deja activas las plantillas propias de un proyecto."""
    from davgen.nucleo import bd, boveda, plantillas
    # scrypt con el costo mínimo: las pruebas cifran decenas de veces
    costo, boveda.N = boveda.N, 2 ** 10
    yield
    boveda.N = costo
    boveda.olvidar()
    plantillas.usar_proyecto(None)
    bd.usar_fabrica(None)


@pytest.fixture
def davgen():
    """Ejecuta `davgen <args>` en una carpeta: davgen(carpeta, [...]) →
    (código de salida, texto de consola)."""
    def _correr(carpeta, argumentos):
        return generar_ejemplo.en(str(carpeta), argumentos, silencioso=True)
    return _correr


@pytest.fixture
def proyecto_nuevo(tmp_path):
    """Proyecto recién creado y configurado (sin generar todavía)."""
    return generar_ejemplo.preparar(str(tmp_path / 'proyecto'),
                                    admin_password=CLAVE_PRUEBA)


@pytest.fixture(scope='session')
def proyecto_generado(tmp_path_factory):
    """Proyecto de ejemplo generado UNA vez con todos los extras (solo lectura:
    las pruebas que modifican archivos usan `copia_generado`)."""
    destino = str(tmp_path_factory.mktemp('generado') / 'proyecto')
    generar_ejemplo.preparar(destino, extras=True, admin_password=CLAVE_PRUEBA)
    codigo, salida = generar_ejemplo.en(destino, ['generar', '--local'],
                                        silencioso=True)
    assert codigo == 0, salida
    return destino


@pytest.fixture
def copia_generado(proyecto_generado, tmp_path):
    destino = str(tmp_path / 'copia')
    shutil.copytree(proyecto_generado, destino)
    return destino


def leer(*partes) -> str:
    with open(os.path.join(*partes), encoding='utf-8-sig') as f:
        return f.read()


def archivos(carpeta: str):
    """Rutas relativas (con /) de todos los archivos bajo `carpeta`."""
    salida = []
    for base, _dirs, nombres in os.walk(carpeta):
        for n in nombres:
            salida.append(os.path.relpath(os.path.join(base, n), carpeta)
                          .replace(os.sep, '/'))
    return sorted(salida)
