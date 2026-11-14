"""generar_ejemplo.py — genera el proyecto de ejemplo en una carpeta, sin BD.

    python scripts/generar_ejemplo.py [destino] [--extras]

Crea un proyecto nuevo en `destino` (por defecto: .tmp/ejemplo), copia el
mockup de ejemplos/biblioteca y ejecuta `davgen generar --local`: todo el
código queda generado sin base de datos, sin FTP y sin instalar Laravel/React.
Es lo mismo que hacen las pruebas de extremo a extremo (tests/test_e2e_local.py).

Con SOURCE_DATE_EPOCH definido la salida es reproducible byte a byte.
"""
import contextlib
import io
import os
import shutil
import sys

RAIZ_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ_REPO, 'src'))

from davgen import cli  # noqa: E402
from davgen.nucleo import boveda, configuracion, plantillas  # noqa: E402

EXTRAS = ('form_requests', 'tests', 'componentes_react', 'ci', 'openapi', 'export')


def preparar(destino: str, extras: bool = False, mockup: str = '',
             nombre: str = 'Biblioteca', modulo: str = 'bib',
             admin_password: str = '') -> str:
    """Deja en `destino` un proyecto listo para `generar` (estructura +
    _configtotal.ini completo + mockup). Devuelve la ruta del proyecto."""
    destino = os.path.abspath(destino)
    if os.path.isdir(destino):
        shutil.rmtree(destino)
    os.makedirs(destino)
    en(destino, ['nuevo'])
    mockup = mockup or os.path.join(RAIZ_REPO, 'ejemplos', 'biblioteca', 'index.html')
    shutil.copy2(mockup, os.path.join(destino, '01-Mockups', 'index.html'))
    ruta = os.path.join(destino, '_configtotal.ini')
    with open(ruta, encoding='utf-8') as f:
        lineas = f.read().splitlines()
    valores = {('proyecto', 'nombre'): nombre, ('proyecto', 'modulo'): modulo,
               ('entrada', 'mockup'): '01-Mockups/index.html'}
    # davgen no trae contraseña de administrador: el ejemplo usa una al azar
    # (los accesos van en el archivo del entorno, no en _configtotal.ini)
    configuracion.fijar_valor(destino, 'seguridad', 'admin_password',
                              admin_password or configuracion.generar_password(),
                              archivo='_acceso.desarrollo.ini')
    if extras:
        valores.update({('generar', e): 'si' for e in EXTRAS})
    seccion, salida = '', []
    for linea in lineas:
        limpia = linea.strip()
        if limpia.startswith('['):
            seccion = limpia.strip('[]').lower()
        elif limpia and limpia[0] != ';' and '=' in limpia:
            clave = limpia.split('=', 1)[0].strip().lower()
            if (seccion, clave) in valores:
                linea = f"{clave} = {valores[(seccion, clave)]}"
        salida.append(linea)
    with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(salida) + '\n')
    return destino


def en(carpeta: str, argumentos, silencioso: bool = False):
    """Ejecuta `davgen <argumentos>` con `carpeta` como directorio actual.
    Devuelve (código de salida, texto de consola)."""
    previo = os.getcwd()
    os.environ.setdefault('DAVGEN_NO_ABRIR', '1')
    buf = io.StringIO()
    try:
        os.chdir(carpeta)
        if silencioso:
            with contextlib.redirect_stdout(buf):
                codigo = cli.main(list(argumentos))
        else:
            codigo = cli.main(list(argumentos))
    finally:
        os.chdir(previo)
        plantillas.usar_proyecto(None)
        os.environ.pop('DAVGEN_ENTORNO', None)   # --entorno no debe quedar pegado
        boveda.olvidar()                         # ni un token en memoria
    return codigo, buf.getvalue()


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    destino = args[0] if args else os.path.join(RAIZ_REPO, '.tmp', 'ejemplo')
    proyecto = preparar(destino, extras='--extras' in sys.argv)
    codigo, _ = en(proyecto, ['generar', '--local'])
    print(f"\n  Proyecto de ejemplo en: {proyecto}")
    return codigo


if __name__ == '__main__':
    sys.exit(main())
