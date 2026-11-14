"""consola.py — salida con colores ANSI (sin dependencias)."""
import os
import sys

# Habilitar ANSI en consolas Windows antiguas
if os.name == 'nt':
    os.system('')


class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    DIM    = "\033[2m"


def ok(msg):    print(f"  {C.GREEN}✓{C.RESET} {msg}")
def warn(msg):  print(f"  {C.YELLOW}⚠{C.RESET} {msg}")
def error(msg): print(f"  {C.RED}✗{C.RESET} {msg}")
def info(msg):  print(f"  {C.CYAN}→{C.RESET} {msg}")
def dim(msg):   print(f"  {C.DIM}{msg}{C.RESET}")


def titulo(msg):
    print(f"\n{C.BOLD}{C.WHITE}{'─' * 58}")
    print(f"  {msg}")
    print(f"{'─' * 58}{C.RESET}\n")


def banner(texto):
    print(f"\n{C.BOLD}{C.WHITE}╔{'═' * 52}╗")
    print(f"║  {texto:<50}║")
    print(f"╚{'═' * 52}╝{C.RESET}")


def confirmar(pregunta: str, no_interactivo: bool = False,
              defecto: bool = True) -> bool:
    if no_interactivo:
        return defecto
    resp = input(f"  {C.YELLOW}{pregunta} (s/n): {C.RESET}").strip().lower()
    return resp in ('s', 'si', 'sí', 'y', 'yes')


def es_interactiva() -> bool:
    """True solo si hay una persona delante: la entrada es una CONSOLA real.

    `sys.stdin.isatty()` no alcanza en Windows: el dispositivo nulo (`NUL`, lo
    que recibe un proceso lanzado con la entrada cerrada) también dice ser una
    terminal, y un `input()`/`getpass()` ahí queda esperando para siempre o
    falla. Se confirma preguntándole al sistema si ese descriptor es de consola.
    """
    try:
        if sys.stdin is None or not sys.stdin.isatty():
            return False
    except (AttributeError, ValueError, OSError):
        return False
    if os.name != 'nt':
        return True
    try:
        import ctypes
        import msvcrt
        modo = ctypes.c_uint32()
        manija = msvcrt.get_osfhandle(sys.stdin.fileno())
        return bool(ctypes.windll.kernel32.GetConsoleMode(ctypes.c_void_p(manija),
                                                          ctypes.byref(modo)))
    except (OSError, ValueError, AttributeError, ImportError):
        return False


def asegurar_utf8():
    # utf-8-sig en stdin tolera el BOM que PowerShell antepone al hacer pipe
    try:
        sys.stdin.reconfigure(encoding='utf-8-sig', errors='replace')
    except (AttributeError, OSError):
        pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, OSError):
            pass
