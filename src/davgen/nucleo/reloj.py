"""reloj.py — fecha/hora del generador, reproducible.

Todo sello de fecha que el generador escribe en un archivo pasa por aquí. Si
está definida la variable de entorno estándar SOURCE_DATE_EPOCH (segundos Unix,
https://reproducible-builds.org/specs/source-date-epoch/) se usa esa fecha en
vez del reloj: dos corridas sobre la misma entrada producen la misma salida
byte a byte. Es lo que permite las pruebas de snapshot del generador.
"""
import os
from datetime import datetime, timezone


def ahora() -> datetime:
    epoch = os.environ.get('SOURCE_DATE_EPOCH', '').strip()
    if epoch:
        try:
            return datetime.fromtimestamp(int(epoch), tz=timezone.utc).replace(tzinfo=None)
        except (ValueError, OverflowError, OSError):
            pass
    return datetime.now()


def sello() -> str:
    """Fecha en el formato que usan las cabeceras generadas: 2026-01-31 14:05."""
    return ahora().strftime('%Y-%m-%d %H:%M')
