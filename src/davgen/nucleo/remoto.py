"""remoto.py — bajar el backend PUBLICADO y compararlo en local.

Antes de desplegar conviene saber qué hay de verdad en el servidor: alguien
pudo subir un archivo a mano, un despliegue pudo quedar a medias, o el
manifiesto local pudo quedar viejo. En vez de ir archivo por archivo contra el
FTP en cada corrida, se baja UNA vez el PHP publicado (`app/**`, `routes/**`,
`bootstrap/app.php`, `bootstrap/providers.php`) a
`_backendGenerado/_remoto/` y todo lo demás se hace en local: comparar, ver
diferencias y validar la sintaxis de lo que se va a subir.

Solo lee del servidor: no sube, no borra y no modifica nada remoto.
"""
import ftplib
import os
import shutil
import subprocess
from typing import Callable, Dict, List, Optional, Tuple

from . import resumen

CARPETA = '_remoto'
_RAICES = ('app', 'routes')
_SUELTOS = ('bootstrap/app.php', 'bootstrap/providers.php')

_fabrica_ftp: Optional[Callable] = None


def usar_fabrica_ftp(fabrica: Optional[Callable]) -> None:
    """Sustituye la conexión FTP real por `fabrica(cfg_ftp)` (solo pruebas)."""
    global _fabrica_ftp
    _fabrica_ftp = fabrica


def _abrir(cfg_ftp: Dict):
    if _fabrica_ftp is not None:
        return _fabrica_ftp(cfg_ftp)
    ftp = ftplib.FTP()
    ftp.connect(resumen._host_ftp(cfg_ftp['host']), 21, timeout=60)
    ftp.login(cfg_ftp['usuario'], cfg_ftp['password'])
    ftp.set_pasv(True)
    return ftp


def _listar(ftp, ruta: str) -> List[Tuple[str, bool]]:
    """[(nombre, es_carpeta)] de una carpeta remota; [] si no existe."""
    try:
        return [(n, datos.get('type') == 'dir') for n, datos in ftp.mlsd(ruta)
                if n not in ('.', '..') and datos.get('type') in ('dir', 'file')]
    except ftplib.error_perm as e:
        if str(e)[:3] not in ('500', '501', '502', '504'):   # no es «MLSD no soportado»
            return []
    except (AttributeError, ftplib.all_errors):
        pass
    try:
        nombres = [os.path.basename(n.rstrip('/')) for n in ftp.nlst(ruta)]
    except ftplib.all_errors:
        return []
    salida = []
    for n in sorted(set(x for x in nombres if x and x not in ('.', '..'))):
        salida.append((n, '.' not in n))     # sin MLSD: carpeta = nombre sin extensión
    return salida


def descargar_backend(cfg_ftp: Dict, destino: str) -> Dict:
    """Baja el PHP publicado a `destino` (se vacía antes: es una copia de
    trabajo de davgen). Devuelve {existe, descargados, errores}."""
    remota = cfg_ftp['ruta_remota'].rstrip('/')
    reporte = {'existe': False, 'descargados': 0, 'errores': []}
    try:
        ftp = _abrir(cfg_ftp)
    except (ftplib.all_errors, OSError) as e:
        reporte['errores'].append(f'FTP no conecta: {e}')
        return reporte
    if os.path.isdir(destino):
        shutil.rmtree(destino)
    os.makedirs(destino)

    def bajar(rel: str) -> None:
        local = os.path.join(destino, *rel.split('/'))
        os.makedirs(os.path.dirname(local), exist_ok=True)
        try:
            with open(local, 'wb') as f:
                ftp.retrbinary(f'RETR {remota}/{rel}', f.write)
            reporte['descargados'] += 1
        except ftplib.all_errors as e:
            os.remove(local)
            if not str(e).startswith('550'):          # 550 = no existe: no es un error
                reporte['errores'].append(f'{rel}: {e}')

    def recorrer(rel: str) -> None:
        for nombre, es_carpeta in _listar(ftp, f'{remota}/{rel}'):
            hijo = f'{rel}/{nombre}'
            if es_carpeta:
                recorrer(hijo)
            elif nombre.endswith('.php'):
                bajar(hijo)

    try:
        for raiz in _RAICES:
            recorrer(raiz)
        for suelto in _SUELTOS:
            bajar(suelto)
    finally:
        try:
            ftp.quit()
        except ftplib.all_errors:
            pass
    reporte['existe'] = reporte['descargados'] > 0
    return reporte


def comparar(carpeta_espejo: str, ruta_laravel: str, carpeta_remota: str) -> Dict:
    """Compara lo que se desplegaría (espejo generado + código propio del
    Laravel real) contra la copia bajada del servidor, ignorando la línea
    `@generated` (fecha y versión). Devuelve listas de rutas relativas:
      iguales · distintos · solo_local (falta subir) · solo_remoto (sobra allá)
    y `origenes` {rel: ruta local} para poder mostrar el diff."""
    locales, origenes = resumen._hashes_control(carpeta_espejo, ruta_laravel)
    locales = {r: h.replace(resumen._MARCA_PROPIO, '', 1) for r, h in locales.items()}
    remotos = {}
    for base, _dirs, archivos in os.walk(carpeta_remota):
        for a in archivos:
            ruta = os.path.join(base, a)
            rel = os.path.relpath(ruta, carpeta_remota).replace(os.sep, '/')
            remotos[rel] = resumen._sha256_generado(ruta)
    return {
        'iguales': sorted(r for r in locales if remotos.get(r) == locales[r]),
        'distintos': sorted(r for r in locales if r in remotos and remotos[r] != locales[r]),
        'solo_local': sorted(r for r in locales if r not in remotos),
        'solo_remoto': sorted(r for r in remotos if r not in locales),
        'origenes': origenes,
    }


def buscar_php() -> str:
    """Un ejecutable de PHP para validar sintaxis, o ''."""
    candidatos = [os.environ.get('DAVGEN_PHP', ''), shutil.which('php') or '']
    return next((c for c in candidatos if c and os.path.isfile(c)), '')


def validar_sintaxis(origenes: Dict[str, str], php: str) -> List[str]:
    """`php -l` sobre cada archivo que se subiría. Devuelve los que fallan."""
    fallas = []
    for rel, local in sorted(origenes.items()):
        try:
            r = subprocess.run([php, '-l', local], capture_output=True, text=True,
                               timeout=60, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError) as e:
            fallas.append(f'{rel}: no se pudo validar ({e})')
            continue
        if r.returncode != 0:
            detalle = ' '.join((r.stdout or r.stderr).split())[:160]
            fallas.append(f'{rel}: {detalle}')
    return fallas
