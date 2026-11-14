"""bd.py — ÚNICO punto de conexión a MySQL/MariaDB del generador.

Antes cada módulo importaba `mysql.connector` por su cuenta (7 sitios). Aquí se
centraliza para:
  · poder elegir el controlador: PyMySQL (licencia MIT, el predeterminado) o
    mysql-connector-python (GPLv2 con excepción FOSS) si es el que está
    instalado — davgen no obliga a ninguno de los dos;
  · que las pruebas puedan sustituir la conexión por un doble (`usar_fabrica`);
  · que una corrida completa use UNA conexión (`una_sola_conexion`): el
    hosting compartido cuenta las conexiones nuevas por hora;
  · dar un solo mensaje de error accionable cuando falta el controlador.

La API que usa el resto del código es la DB-API 2.0 común a ambos: `cursor()`,
`execute(sql, params)` con marcadores `%s`, `fetchall()`, `commit()`, `close()`.
"""
from contextlib import contextmanager
from typing import Callable, Dict, Optional, Tuple

_fabrica: Optional[Callable] = None     # doble de pruebas (ver usar_fabrica)

MENSAJE_SIN_CONTROLADOR = (
    "No hay controlador de MySQL instalado — instalar uno:  "
    "pip install pymysql   (o: pip install mysql-connector-python)")


class SinControlador(RuntimeError):
    """No está instalado ni PyMySQL ni mysql-connector-python."""


def usar_fabrica(fabrica: Optional[Callable]) -> None:
    """Sustituye la conexión real por `fabrica(bd, timeout)` (None = restaurar).
    Solo para pruebas: permite ejercitar el código de BD sin un servidor."""
    global _fabrica
    _fabrica = fabrica


def controlador() -> str:
    """Nombre del controlador disponible: 'pymysql', 'mysql.connector' o ''."""
    try:
        import pymysql  # noqa: F401
        return 'pymysql'
    except ImportError:
        pass
    try:
        import mysql.connector  # noqa: F401
        return 'mysql.connector'
    except ImportError:
        return ''


# ── Una sola conexión por corrida ───────────────────────────────────────────
# El hosting compartido limita las conexiones NUEVAS por hora de cada usuario
# de MySQL (error 1226). Una corrida de `generar` conectaba una vez por paso
# (validar, leer el esquema, comparar y aplicar procedimientos, seeds…) y cada
# una descontaba del mismo cupo que usa el sitio publicado. Dentro de
# `una_sola_conexion()` todos esos pasos comparten la misma.
_compartidas: Optional[Dict] = None     # None = cada conectar() abre la suya
_abiertas = 0                           # conexiones reales abiertas (contador)

ERROR_LIMITE_POR_HORA = 1226            # max_connections_per_hour (y similares)
ERROR_LIMITE_SIMULTANEAS = 1203         # max_user_connections


class _Compartida:
    """Conexión que varios pasos reutilizan: `close()` no la cierra (solo
    descarta lo que no se confirmó); se cierra al salir de `una_sola_conexion`."""

    def __init__(self, real):
        self._davgen_real = real

    def __getattr__(self, nombre):
        return getattr(self._davgen_real, nombre)

    def close(self):
        try:
            self._davgen_real.rollback()
        except Exception:                           # noqa: BLE001
            pass


def real(conn):
    """La conexión del controlador que hay detrás de una compartida."""
    return getattr(conn, '_davgen_real', conn)


def _viva(conn) -> bool:
    """True si la conexión sigue abierta (el hosting corta las inactivas, y
    entre dos pasos puede haber minutos de composer o npm)."""
    ping = getattr(conn, 'ping', None)
    if ping is None:
        return True
    try:
        ping(reconnect=False)
        return True
    except Exception:                               # noqa: BLE001
        return False


@contextmanager
def una_sola_conexion():
    """Mientras dura el bloque, `conectar()` devuelve siempre la misma conexión
    para las mismas credenciales. Se cierra al salir. Anidar no abre otra."""
    global _compartidas
    if _compartidas is not None:
        yield
        return
    _compartidas = {}
    try:
        yield
    finally:
        abiertas, _compartidas = _compartidas, None
        for conn in abiertas.values():
            try:
                real(conn).close()
            except Exception:                       # noqa: BLE001
                pass


def conexiones_abiertas() -> int:
    """Cuántas conexiones reales abrió el proceso hasta ahora."""
    return _abiertas


def codigo_error(exc: Exception) -> int:
    """Código de error de MySQL de una excepción de cualquiera de los dos
    controladores (0 si no lo trae)."""
    codigo = getattr(exc, 'errno', None)
    if not isinstance(codigo, int) and getattr(exc, 'args', None):
        codigo = exc.args[0]
    return codigo if isinstance(codigo, int) else 0


def explicar_limite(exc: Exception) -> Optional[Tuple[str, str]]:
    """(causa, qué hacer) si el error es un límite de conexiones del hosting;
    None si es otra cosa. Reintentar enseguida no sirve: gasta más cupo."""
    codigo = codigo_error(exc)
    if codigo == ERROR_LIMITE_POR_HORA:
        return ('el hosting bloqueó las conexiones a la base por una hora '
                '(límite de conexiones por hora del usuario de MySQL, error 1226)',
                'esperar a que pase la hora y reintentar UNA vez; mientras tanto el '
                'sitio publicado también falla. No repetir corridas contra producción: '
                'desarrollar contra _acceso.desarrollo.ini')
    if codigo == ERROR_LIMITE_SIMULTANEAS:
        return ('el usuario de MySQL ya tiene abiertas todas las conexiones simultáneas '
                'que permite el hosting (error 1203)',
                'reintentar en unos minutos; si se repite con el sitio en uso, poner '
                '[opciones] conexiones_persistentes = no y volver a generar')
    return None


def mensaje_error(exc: Exception) -> str:
    """Texto de una línea para mostrar un error de conexión o de consulta."""
    limite = explicar_limite(exc)
    return f'{limite[0]} — {limite[1]}' if limite else str(exc)


def conectar(bd: Dict, timeout: int = 20):
    """Abre una conexión con las credenciales de la sección [bd] (o devuelve
    la compartida de la corrida, ver `una_sola_conexion`)."""
    if _compartidas is None:
        return _abrir(bd, timeout)
    clave = (bd.get('host'), str(bd.get('puerto') or 3306), bd.get('usuario'),
             bd.get('database'))
    conn = _compartidas.get(clave)
    if conn is not None and _viva(real(conn)):
        return conn
    conn = _compartidas[clave] = _Compartida(_abrir(bd, timeout))
    return conn


def _abrir(bd: Dict, timeout: int):
    global _abiertas
    conn = _abrir_real(bd, timeout)
    _abiertas += 1
    return conn


def _abrir_real(bd: Dict, timeout: int):
    if _fabrica is not None:
        return _fabrica(bd, timeout)
    nombre = controlador()
    if nombre == 'pymysql':
        import pymysql
        return pymysql.connect(
            host=bd['host'], port=int(bd.get('puerto') or 3306),
            user=bd['usuario'], password=bd.get('password', ''),
            database=bd['database'], connect_timeout=timeout,
            charset='utf8mb4')
    if nombre == 'mysql.connector':
        import mysql.connector
        # use_pure: la extensión C falla dentro de un ejecutable congelado
        return mysql.connector.connect(
            host=bd['host'], port=int(bd.get('puerto') or 3306),
            user=bd['usuario'], password=bd.get('password', ''),
            database=bd['database'], connection_timeout=timeout,
            use_pure=True)
    raise SinControlador(MENSAJE_SIN_CONTROLADOR)


def cursor_dict(conn):
    """Cursor que devuelve cada fila como dict {columna: valor}."""
    conn = real(conn)
    if type(conn).__module__.startswith('pymysql'):
        import pymysql.cursors
        return conn.cursor(pymysql.cursors.DictCursor)
    try:
        return conn.cursor(dictionary=True)
    except TypeError:
        return conn.cursor()        # doble de pruebas que ya entrega dicts


def texto(valor) -> str:
    """Los dos controladores no coinciden en el tipo de algunas columnas de
    INFORMATION_SCHEMA (str vs bytes/bytearray): se normaliza a str."""
    if isinstance(valor, (bytes, bytearray)):
        return bytes(valor).decode('utf-8', errors='replace')
    return '' if valor is None else str(valor)
