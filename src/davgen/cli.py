"""
cli.py — davgen · generador dirigido por _configtotal.ini (raíz del proyecto).

El programa se ejecuta en la raíz del proyecto destino. Busca carpetas
03-Backend* (si hay varias, el usuario elige una), valida el entorno y genera
TODO dentro de {03-Backend*}/_backendGenerado:

    {raiz}/
    ├── _configtotal.ini          ← único archivo a completar
    ├── _plantillas/              ← (opcional) plantillas propias que
    │                               reemplazan a las del paquete
    ├── 03-Backend*/
    │   ├── servicio/ (o backend/)  ← proyecto Laravel
    │   └── _backendGenerado/       ← TODO lo generado (espejo)
    └── 04-Front*/frontend/         ← proyecto React

Comandos:  nuevo · generar · sincronizar · verificar · comparar ·
           plantillas · doctor · actualizar · seguridad   (`davgen --help`)
"""
import argparse
import configparser
import os
import shutil
import subprocess
import sys
from datetime import datetime  # noqa: F401

from .nucleo import bd as _bd
from .nucleo import (boveda, configuracion, diagnostico, entrada, esquema, gen_backend,
                     gen_componentes, gen_devops, gen_google, gen_plantillas,
                     gen_legal, gen_tema,
                     gen_prompts, gen_pruebas, gen_servicios, gen_sql,
                     gen_testing, plantillas, remoto)
from .nucleo.consola import (C, asegurar_utf8, banner, confirmar, dim, error,
                             es_interactiva, info, ok, titulo, warn)
from .nucleo.reloj import ahora as _ahora
from .nucleo import resumen as resumen_mod
from .nucleo.resumen import (Registro, avisar_version_proyecto,
                             comparar_diferencias, decidir_frontend,
                             decidir_produccion, delta_esquema,
                             escribir_manifiesto, escribir_manifiesto_integridad,
                             escribir_snapshot_esquema, imprimir_verificacion,
                             leer_snapshot_esquema, resumen_final,
                             snapshot_esquema, verificar_integridad,
                             verificar_manifiesto)
from .nucleo.version import VERSION
from .nucleo.plantillas import cargar as _plantilla

# Carpetas donde se busca una plantilla Laravel/React EMPAQUETADA POR EL PROPIO
# USUARIO (_laravel.zip / _react.zip — ver scripts/empaquetar-plantillas.ps1).
# davgen NO distribuye esos zips: traen vendor/ y node_modules/ de terceros.
# Sin zip, el proyecto se crea con composer / npm, que es el camino normal.
_DIR_CACHE = os.path.join(os.path.expanduser('~'), '.davgen')
_BASE = (os.path.dirname(os.path.abspath(sys.executable))
         if getattr(sys, 'frozen', False) else _DIR_CACHE)

# ─────────────────────────────────────────────
#  Proyecto nuevo: estructura inicial + guía del proceso
# ─────────────────────────────────────────────
CARPETAS_PROYECTO = ['00-Requisitos', '01-Mockups', '02-Base-de-datos',
                     '03-Backend', '04-Frontend', '05-Testing']

_LEEME_PROCESO = _plantilla('proyecto/leeme_proceso.md', __name__, '_LEEME_PROCESO')

# .gitignore para el PROYECTO DESTINO (no el repo del generador).
# Decisión del proyecto: _configtotal.ini y 03-Backend/_backendGenerado/ SÍ se
# versionan a propósito, así que NO se ignoran aquí.
_GITIGNORE = _plantilla('proyecto/gitignore.txt', __name__, '_GITIGNORE')


def inicializar_proyecto(raiz: str) -> None:
    """No hay carpetas del proyecto: crea la estructura inicial completa,
    la guía del proceso (leeme_proceso.md) y el _configtotal.ini a llenar."""
    titulo("PROYECTO NUEVO — creando la estructura inicial")
    for nombre in CARPETAS_PROYECTO:
        os.makedirs(os.path.join(raiz, nombre), exist_ok=True)
        ok(f"Carpeta {nombre}\\ creada")

    # 00-seguridad.sql SIEMPRE existe desde el inicio (tbl_seg_* con defaults):
    # el usuario debe ejecutarlo en su BD ANTES de generar (sin esas tablas la
    # generación se detiene). Al generar, davgen lo reescribe con los seeds.
    carpeta_02 = os.path.join(raiz, '02-Base-de-datos')
    # Accesos por entorno (_acceso.desarrollo.ini / _acceso.produccion.ini). La
    # contraseña inicial del administrador nace vacía: la escribe el usuario.
    # Hasta entonces el script de seguridad lleva un hash con el que nadie entra.
    ruta_cfg = os.path.join(raiz, '_configtotal.ini')
    es_nuevo = not os.path.isfile(ruta_cfg)
    accesos_creados = (configuracion.crear_accesos(raiz)
                       if es_nuevo or configuracion.hay_entornos(raiz) else [])
    try:
        clave_admin = configuracion.leer_ini(raiz).get(
            'seguridad', 'admin_password', fallback='')
    except Exception:                                   # noqa: BLE001
        clave_admin = ''
    gen_sql.generar_seguridad_inicial(carpeta_02, admin_password=clave_admin)
    gen_sql.generar_readme_cero(carpeta_02)
    ok("00-seguridad.sql + readme_cero.md creados en 02-Base-de-datos\\ — "
       "`davgen seguridad` lo completa con tu contraseña de administrador y "
       "lo aplica en la base UNA SOLA VEZ (crea tbl_seg_*)")

    with open(os.path.join(raiz, 'leeme_proceso.md'), 'w', encoding='utf-8') as f:
        f.write(_LEEME_PROCESO)
    ok("leeme_proceso.md creado — guía del proceso de desarrollo (fases 0→6)")

    # prompts de IA para las fases manuales (mockup, tablas, SPs, custom);
    # aún no hay _configtotal.ini: el módulo queda como placeholder {modulo}
    gen_prompts.generar_prompts(raiz)
    ok("_prompts\\ creados — prompts de IA por fase (mockup, tablas, SPs, "
       "personalización)")

    # documentos estándar mínimos (uno por fase a completar) + guía interactiva
    plantillas = gen_plantillas.generar_plantillas(raiz)
    for pl in plantillas:
        dim(f"· {os.path.relpath(pl, raiz)}  (plantilla a COMPLETAR)")
    ok(f"{len(plantillas)} plantilla(s) de documentos copiadas — "
       "revisarlas y completarlas")
    gen_plantillas.generar_leeme_html(raiz)
    ok("leeme.html creado — GUÍA INTERACTIVA del proyecto (abrir con doble "
       "clic): qué configurar (BD, nombre), proceso, reglas y prompts")
    ruta_md = gen_plantillas.generar_leeme_md(raiz)
    ok("_davgen.leeme.md creado — guía rápida en markdown")
    _abrir_archivo(ruta_md)

    gen_plantillas.generar_guia_google(raiz)
    ok("CONFIGURAR-GOOGLE-AUTH.md creado — acción OPCIONAL por proyecto: "
       "habilitar inicio de sesión con Google (Client ID + tbl_seg_parametro)")

    if not os.path.isfile(ruta_cfg):
        with open(ruta_cfg, 'w', encoding='utf-8') as f:
            f.write(configuracion.nueva_plantilla())
        ok("_configtotal.ini creado — configuración del proyecto (sin contraseñas)")
    else:
        dim("· _configtotal.ini ya existía — no se toca")
    for creado in accesos_creados:
        ok(f"{os.path.basename(creado)} creado — usuarios y contraseñas de ese "
           "entorno (NO se versiona)")

    ruta_gitignore = os.path.join(raiz, '.gitignore')
    if not os.path.isfile(ruta_gitignore):
        with open(ruta_gitignore, 'w', encoding='utf-8') as f:
            f.write(_GITIGNORE)
        ok(".gitignore creado (ignora los _acceso.*.ini —contraseñas—, node_modules, "
           "vendor, dist, .env y logs; _configtotal.ini y _backendGenerado/ se versionan)")
    else:
        dim("· .gitignore ya existía — no se toca")

    if configuracion.escribir_ejemplo(raiz):
        ok("_acceso.*.ejemplo.ini creados — copias SIN contraseñas, para versionar")

    print(f"\n  {C.BOLD}Qué necesitas tener a mano:{C.RESET}")
    info("El MOCKUP del sistema en HTML → copiarlo a 01-Mockups/index.html "
         "(o las tablas ya creadas en la base, con [entrada] tipo = bd)")
    info("Acceso a una BASE DE DATOS MySQL/MariaDB de desarrollo → "
         "_acceso.desarrollo.ini  [bd]")
    info("Para publicar: la base y el FTP del hosting → _acceso.produccion.ini "
         " [bd] y [ftp]")
    info("PHP 8.2+, Composer y Node.js para crear y ejecutar el sistema "
         "(`davgen doctor` dice qué falta)")
    dim(diagnostico.INTERFAZ)
    print(f"\n  {C.BOLD}Para continuar:{C.RESET}")
    info("1. Completar _configtotal.ini  ([proyecto] nombre y módulo, [entrada])")
    info("2. Completar _acceso.desarrollo.ini  ([bd] y TU contraseña de "
         "administrador en [seguridad] admin_password: davgen no trae ninguna)")
    info("3. davgen doctor --conexiones   (comprueba que todo responde)")
    info("4. davgen seguridad   y luego   davgen generar")
    info("5. Para publicar:  davgen generar --entorno produccion")


# ─────────────────────────────────────────────
#  Paso 1 · Validación del entorno (raíz)
# ─────────────────────────────────────────────
def buscar_carpetas_backend():
    """
    Busca carpetas cuyo nombre empiece con '03-Backend' (ej: 03-Backend,
    03-Backend-Zapatos) y devuelve la lista de rutas absolutas encontradas.
    Orden de búsqueda:
      1. el directorio actual (donde se ejecuta el programa) y sus padres
      2. las subcarpetas inmediatas del directorio actual
      3. la carpeta del script y sus padres
    """
    inicios = [os.getcwd()]
    candidatos = []
    for inicio in inicios:
        actual = os.path.abspath(inicio)
        while True:
            candidatos.append(actual)
            padre = os.path.dirname(actual)
            if padre == actual:
                break
            actual = padre
    # subcarpetas inmediatas del directorio actual (después de cwd, antes del script)
    try:
        candidatos[1:1] = [os.path.join(os.getcwd(), d)
                           for d in sorted(os.listdir(os.getcwd()))
                           if os.path.isdir(os.path.join(os.getcwd(), d))]
    except OSError:
        pass

    encontradas, vistos = [], set()
    for c in candidatos:
        clave = os.path.normcase(c)
        if clave in vistos:
            continue
        vistos.add(clave)
        try:
            nombres = sorted(os.listdir(c))
        except OSError:
            continue
        for nombre in nombres:
            ruta = os.path.join(c, nombre)
            if (nombre.lower().startswith('03-backend')
                    and os.path.isdir(ruta)
                    and os.path.normcase(ruta) not in
                    {os.path.normcase(e) for e in encontradas}):
                encontradas.append(ruta)
    return encontradas


def _localizar_backend_generado():
    """Ruta de {03-Backend*}\\_backendGenerado SIN validar Laravel ni BD (para
    `verificar`). Prefiere una carpeta que ya tenga _backendGenerado generado;
    devuelve None si no hay ninguna 03-Backend*."""
    carpetas = buscar_carpetas_backend()
    if not carpetas:
        return None
    con_generado = [c for c in carpetas
                    if os.path.isdir(os.path.join(c, '_backendGenerado'))]
    elegida = _seleccionar_carpeta(con_generado or carpetas, no_interactivo=True)
    return os.path.join(elegida, '_backendGenerado')


def _seleccionar_carpeta(carpetas, no_interactivo: bool):
    """Si hay varias carpetas 03-Backend*, muestra un menú para elegir una."""
    if len(carpetas) == 1:
        return carpetas[0]
    print(f"  {C.BOLD}Se encontraron {len(carpetas)} carpetas de backend — "
          f"seleccionar una:{C.RESET}\n")
    for i, ruta in enumerate(carpetas, 1):
        print(f"    {C.CYAN}[{i}]{C.RESET} {C.BOLD}{os.path.basename(ruta)}{C.RESET}"
              f"  {C.DIM}{ruta}{C.RESET}")
    print()
    if no_interactivo:
        info(f"Modo no interactivo: se usa [1] {os.path.basename(carpetas[0])}")
        return carpetas[0]
    while True:
        resp = input(f"  {C.YELLOW}Seleccionar carpeta [1-{len(carpetas)}]: "
                     f"{C.RESET}")
        resp = ''.join(c for c in resp if c.isdigit())
        if resp and 1 <= int(resp) <= len(carpetas):
            return carpetas[int(resp) - 1]
        warn(f"Opción inválida — escribir un número entre 1 y {len(carpetas)}")


def _leer_credenciales_configtotal(ruta_configtotal):
    """Lee la sección [bd] de _configtotal.ini (raíz). Devuelve (bd, errores)."""
    if not os.path.isfile(ruta_configtotal):
        return {}, [f"No existe _configtotal.ini en la raíz ({os.path.dirname(ruta_configtotal)})"]
    try:
        # _configtotal.ini + el archivo de acceso del entorno elegido
        ini = configuracion.leer_ini(os.path.dirname(ruta_configtotal))
    except configparser.Error as e:
        return {}, [f"_configtotal.ini ilegible: {e}"]

    bd = {clave: ini.get('bd', clave, fallback='').strip()
          for clave in ('host', 'puerto', 'usuario', 'password', 'database')}
    errores = [f"[bd] {clave} — requerido en _configtotal.ini"
               for clave in ('host', 'usuario', 'database') if not bd[clave]]
    bd['puerto'] = bd['puerto'] or '3306'
    if not bd['puerto'].isdigit():
        errores.append("[bd] puerto — debe ser numérico (default 3306)")
    return bd, errores


def _probar_conexion_bd(bd) -> None:
    """Abre y cierra una conexión MySQL con las credenciales dadas."""
    _bd.conectar(bd, timeout=10).close()


def _decidir_aplicar_sps(cfg, ruta_sps: str, no_interactivo: bool) -> None:
    """Compara los SPs pcru* del 03_procedimientos.sql contra la BD y, según
    [generar] aplicar_sps / confirmación interactiva, los ejecuta (DROP+CREATE).
    Siempre informa el resultado. No detiene la generación si algo falla."""
    import os
    nombre_sql = os.path.basename(ruta_sps)   # '03_procedimientos.sql'
    bd_nombre  = cfg['bd']['database']
    aplicar_flag = cfg['generar'].get('aplicar_sps')

    # 1) Comparar (sin aplicar) para mostrar el estado actual de la BD
    info(f"Comparando «{nombre_sql}» con los procedimientos en «{bd_nombre}»…")
    rep = gen_sql.aplicar_procedimientos(cfg['bd'], ruta_sps, aplicar=False)
    if 'error' in rep:
        warn(f"No se pudo conectar a la BD para comparar los SPs: {rep['error']}")
        warn(f"Ejecuta manualmente «{nombre_sql}» en la BD antes de continuar.")
        return

    nuevos      = rep['nuevos']
    actualizados = rep['actualizados']
    iguales     = rep['iguales']
    distintos   = nuevos + actualizados

    # Mostrar estado por SP
    for n in iguales:
        dim(f"· SIN CAMBIO  {n}")
    for n in nuevos:
        dim(f"· NUEVO       {n}  ← se creará en la BD")
    for n in actualizados:
        dim(f"· ACTUALIZAR  {n}  ← ya existe, se reemplazará")

    if not distintos:
        ok(f"Los {len(iguales)} procedimiento(s) de «{nombre_sql}» ya están "
           f"actualizados en «{bd_nombre}» — nada que aplicar.")
        return

    # 2) Informar intención antes de preguntar/actuar
    n_nuevos = len(nuevos)
    n_act    = len(actualizados)
    partes   = []
    if n_nuevos:
        partes.append(f"{n_nuevos} nuevo(s)")
    if n_act:
        partes.append(f"{n_act} a actualizar")
    info(f"«{nombre_sql}» tiene {', '.join(partes)} en «{bd_nombre}».")

    if n_act and not nuevos:
        info("Los procedimientos ya existen en la BD y serán actualizados "
             "(DROP + CREATE idempotente).")
    elif n_nuevos and not actualizados:
        info("Los procedimientos NO existen en la BD y serán creados.")
    else:
        info("Se crearán los nuevos y se actualizarán los distintos.")

    # 3) Decidir si ejecutar
    aplicar = aplicar_flag
    if not aplicar and not no_interactivo:
        aplicar = confirmar(
            f"¿Aplicar {len(distintos)} procedimiento(s) en «{bd_nombre}» ahora?")
    if not aplicar:
        warn(f"{len(distintos)} procedimiento(s) NO aplicados. "
             f"Ejecuta «{nombre_sql}» en la BD manualmente, "
             "o activa [generar] aplicar_sps=si.")
        return

    # 4) Ejecutar
    info(f"Ejecutando procedimientos de «{nombre_sql}» en «{bd_nombre}»…")
    rep2 = gen_sql.aplicar_procedimientos(cfg['bd'], ruta_sps, aplicar=True)
    if 'error' in rep2:
        warn(f"Error al aplicar los procedimientos: {rep2['error']}")
        return
    aplicados = len(rep2['nuevos']) + len(rep2['actualizados'])
    ok(f"{aplicados} procedimiento(s) aplicados en «{bd_nombre}» "
       f"({len(rep2['nuevos'])} creados, {len(rep2['actualizados'])} actualizados)")
    if rep2['errores']:
        for e in rep2['errores']:
            warn(f"· {e}")


def _decidir_aplicar_seguridad(cfg, carpeta_db: str, no_interactivo: bool) -> None:
    """Aplica en la BD los SEEDS de 01_seguridad.sql (idempotentes: reconcilian
    admin/owner y agregan módulos/permisos/parámetros nuevos SIN pisar lo
    administrado en la BD) y crea las vistas vis_* que FALTEN. Una vista
    EXISTENTE nunca se toca (puede estar personalizada). Mismo interruptor que
    los SPs: [generar] aplicar_sps. Sin esto, generar anunciaba credenciales
    (admin_email) y vistas que solo existían en los .sql — el login daba 401 y
    los `sel` fallaban hasta ejecutar los scripts a mano."""
    import os
    ruta_seg = os.path.join(carpeta_db, '01_seguridad.sql')
    if not os.path.isfile(ruta_seg):
        return
    bd_nombre = cfg['bd']['database']
    aplicar = cfg['generar'].get('aplicar_sps')
    if not aplicar and not no_interactivo:
        aplicar = confirmar(
            f"¿Aplicar seeds de seguridad y vistas faltantes en «{bd_nombre}» ahora?")
    if not aplicar:
        info("Seeds de seguridad y vistas NO aplicados — ejecutar "
             "01_seguridad.sql (y 02_negocio.sql) en la BD manualmente, "
             "o activar [generar] aplicar_sps=si.")
        return

    info(f"Aplicando seeds de seguridad y vistas faltantes en «{bd_nombre}»…")
    ruta_neg = os.path.join(carpeta_db, '02_negocio.sql')
    rep = gen_sql.aplicar_seguridad(
        cfg['bd'], ruta_seg,
        rutas_vistas=[ruta_neg] if os.path.isfile(ruta_neg) else [])
    if 'error' in rep:
        warn(f"No se pudo conectar a la BD para aplicar seeds/vistas: {rep['error']}")
        warn("Ejecuta manualmente 01_seguridad.sql en la BD.")
        return
    ok(f"Seeds de seguridad aplicados ({rep['seeds']} sentencia(s)): admin "
       f"{cfg['admin_email']} reconciliado; roles/módulos/permisos/parámetros "
       "nuevos sembrados — lo ya administrado en la BD NO se pisa.")
    if rep['vistas_creadas']:
        ok(f"{len(rep['vistas_creadas'])} vista(s) creadas (faltaban): "
           + ', '.join(rep['vistas_creadas']))
    if rep['vistas_respetadas']:
        dim(f"· {len(rep['vistas_respetadas'])} vista(s) ya existían y se "
            "RESPETAN (pueden estar personalizadas) — no se reemplazan")
    for e in rep['seeds_err'] + rep['vistas_err']:
        warn(f"· {e}")


def _inventario_bd(bd):
    """(conjunto de SPs, conjunto de vistas) que existen en la BD `bd['database']`.
    Devuelve None si no se puede conectar (verificación de objetos omitida)."""
    try:
        conn = _bd.conectar(bd, timeout=10)
    except Exception:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES "
            "WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'PROCEDURE'",
            (bd['database'],))
        sps = {r[0] for r in cur.fetchall()}
        cur.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS "
            "WHERE TABLE_SCHEMA = %s", (bd['database'],))
        vistas = {r[0] for r in cur.fetchall()}
        cur.close()
        return sps, vistas
    except Exception:
        return None
    finally:
        conn.close()


# tablas de seguridad de NÚCLEO: sin ellas no hay login/permisos → no se genera
_TBL_SEG_NUCLEO = ('tbl_seg_usuario', 'tbl_seg_rol', 'tbl_seg_modulo',
                   'tbl_seg_permiso', 'tbl_seg_parametro')


def _tablas_seg_existentes(bd):
    """Conjunto de tablas tbl_seg_* presentes en la BD, o None si no se pudo
    conectar."""
    try:
        conn = _bd.conectar(bd, timeout=10)
    except Exception:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = %s", (bd['database'],))
        tablas = {r[0].lower() for r in cur.fetchall()
                  if r[0].lower().startswith('tbl_seg_')}
        cur.close()
        return tablas
    except Exception:
        return None
    finally:
        conn.close()


def _exigir_tablas_seguridad(cfg) -> bool:
    """Prerrequisito de la generación: las tablas tbl_seg_* deben existir en la
    BD. Devuelve True si se puede continuar; False si faltan o no se pudo
    verificar (la generación debe detenerse). Si no hay BD configurada, no se
    puede exigir: avisa y deja continuar."""
    bd = cfg['bd']
    if not bd.get('database'):
        warn("No hay BD en [bd]: no se puede verificar el backbone de seguridad "
             "(tbl_seg_*). Se crea con `davgen seguridad`.")
        return True
    presentes = _tablas_seg_existentes(bd)
    if presentes is None:
        error(f"No se pudo conectar a la BD «{bd['database']}» para verificar "
              "las tablas de seguridad (tbl_seg_*).")
        info("Revisa la sección [bd] de _configtotal.ini y que la BD esté accesible.")
        return False
    faltan = [t for t in _TBL_SEG_NUCLEO if t not in presentes]
    if faltan:
        error(f"Faltan tablas de seguridad en la BD «{bd['database']}»: "
              f"{', '.join(faltan)}")
        info("Ejecuta PRIMERO (una sola vez) `davgen seguridad` "
             "(crea tbl_seg_*: login, 2FA, roles, permisos, parámetros).")
        error("Sin esas tablas NO se continúa con la generación.")
        return False
    ok(f"Backbone de seguridad presente en «{bd['database']}» "
       f"({len(_TBL_SEG_NUCLEO)} tablas tbl_seg_* de núcleo verificadas).")
    return True


def env_valor(valor: str) -> str:
    """Valor listo para un archivo .env: entre comillas si lleva espacios o
    caracteres que dotenv interpreta (#, comillas, $, barra invertida). Ahí se
    cortaban en silencio las contraseñas con símbolos."""
    valor = valor or ''
    if any(c in valor for c in (' ', '#', '"', "'", '$', chr(92))):
        escapado = (valor.replace(chr(92), chr(92) * 2)
                    .replace('"', chr(92) + '"').replace('$', chr(92) + '$'))
        return f'"{escapado}"'
    return valor


def _configurar_env_laravel(destino: str, bd) -> None:
    """Escribe las credenciales [bd] de _configtotal.ini en el .env del proyecto."""
    ruta = os.path.join(destino, '.env')
    if not os.path.isfile(ruta):
        plantilla = os.path.join(destino, '.env.example')
        if not os.path.isfile(plantilla):
            return
        shutil.copy2(plantilla, ruta)
    # SESSION/CACHE/QUEUE: Laravel trae `database` por defecto, que exige tablas
    # propias de Laravel (sessions, cache, jobs) que davgen no crea: sin esto
    # el proyecto recién creado daba 500 en local.
    valores = {'SESSION_DRIVER': 'file', 'CACHE_STORE': 'file',
               'QUEUE_CONNECTION': 'sync'}
    if bd and bd.get('database'):
        valores.update({
            'DB_CONNECTION': 'mysql', 'DB_HOST': bd['host'],
            'DB_PORT': bd['puerto'], 'DB_DATABASE': bd['database'],
            'DB_USERNAME': bd['usuario'],
            'DB_PASSWORD': env_valor(bd['password'])})
    with open(ruta, encoding='utf-8-sig') as f:
        lineas = f.read().splitlines()
    vistos, salida = set(), []
    for linea in lineas:
        clave = linea.lstrip('#').strip().split('=')[0]
        if clave in valores and clave not in vistos:
            salida.append(f"{clave}={valores[clave]}")
            vistos.add(clave)
        elif linea.startswith('APP_KEY=') and linea.strip() == 'APP_KEY=':
            # plantilla del zip: la clave se genera aquí, sin necesitar PHP
            salida.append(f"APP_KEY={_generar_app_key()}")
        else:
            salida.append(linea)
    salida += [f"{k}={v}" for k, v in valores.items() if k not in vistos]
    salida = resumen_mod.con_interruptor_persistentes(salida)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('\n'.join(salida) + '\n')
    ok(".env del proyecto Laravel configurado"
       + (" con la BD de _configtotal.ini" if bd and bd.get('database') else "")
       + " (sesión y caché en archivos)")


def _buscar_zip_plantilla(nombres, raiz: str):
    """Busca un zip de plantilla (acepta varios nombres candidatos) junto al
    exe (_BASE) o en la raíz del proyecto. Devuelve la ruta o None."""
    if isinstance(nombres, str):
        nombres = [nombres]
    for base in (raiz, _BASE, _DIR_CACHE):
        for nombre in nombres:
            ruta = os.path.join(base, nombre)
            if os.path.isfile(ruta):
                return ruta
    return None


def _extraer_zip(ruta_zip: str, destino: str) -> None:
    import zipfile
    os.makedirs(destino, exist_ok=True)
    with zipfile.ZipFile(ruta_zip) as z:
        z.extractall(destino)


def _obtener_zip_plantilla(nombres_sueltos, raiz: str):
    """Ruta a un zip de plantilla (Laravel/React) empaquetado por el usuario,
    o None. Se busca en la raíz del proyecto, junto al ejecutable y en
    ~/.davgen/. Es solo un atajo para no depender de la red."""
    return _buscar_zip_plantilla(nombres_sueltos, raiz)


def _generar_app_key() -> str:
    """APP_KEY de Laravel sin necesitar PHP: base64 de 32 bytes aleatorios."""
    import base64
    import secrets
    return 'base64:' + base64.b64encode(secrets.token_bytes(32)).decode()


def _es_laravel_valido(ruta: str) -> bool:
    """Proyecto Laravel USABLE: artisan + dependencias instaladas (vendor).
    Un create-project fallido deja el esqueleto sin vendor\\ — no sirve."""
    return (os.path.isfile(os.path.join(ruta, 'artisan'))
            and os.path.isfile(os.path.join(ruta, 'vendor', 'autoload.php')))


def _es_laravel_existente(ruta: str) -> bool:
    """Laravel ya instalado (aunque sin vendor): basta artisan + composer.json.
    Usado en modo --listar para no crear ni limpiar nada."""
    return (os.path.isfile(os.path.join(ruta, 'artisan'))
            and os.path.isfile(os.path.join(ruta, 'composer.json')))


def _version_php(php: str):
    """(mayor, menor) del ejecutable PHP dado, o None si no responde."""
    import re
    try:
        r = subprocess.run(f'"{php}" -v', shell=True, capture_output=True,
                           text=True, timeout=30)
        m = re.search(r'PHP (\d+)\.(\d+)', r.stdout or '')
        return (int(m.group(1)), int(m.group(2))) if m else None
    except Exception:
        return None


def _entorno_con_php_adecuado():
    """
    Laravel actual requiere PHP >= 8.2. Si el `php` del PATH es viejo,
    busca uno adecuado (ej. Laragon: C:\\laragon\\bin\\php\\*) y devuelve
    (env con ese PHP al frente del PATH, descripción). Si no hay ninguno,
    devuelve (None, descripción del problema).
    """
    v = _version_php('php')
    if v and v >= (8, 2):
        return os.environ.copy(), f"PHP {v[0]}.{v[1]} (PATH)"

    candidatos = []
    base_laragon = r'C:\laragon\bin\php'
    if os.path.isdir(base_laragon):
        for d in sorted(os.listdir(base_laragon)):
            exe = os.path.join(base_laragon, d, 'php.exe')
            if os.path.isfile(exe):
                vv = _version_php(exe)
                if vv and vv >= (8, 2):
                    candidatos.append((vv, os.path.dirname(exe)))
    if candidatos:
        vv, carpeta_php = max(candidatos)
        env = os.environ.copy()
        env['PATH'] = carpeta_php + os.pathsep + env.get('PATH', '')
        return env, f"PHP {vv[0]}.{vv[1]} ({carpeta_php})"

    detalle = f"PHP {v[0]}.{v[1]} del PATH es insuficiente" if v \
        else "no se encontró PHP"
    return None, detalle


def _instalar_dependencias_laravel(ruta: str, bd):
    """Laravel existente sin vendor/: `composer install`. No toca el código ni
    un .env que ya exista. Devuelve la ruta o None si no se pudo instalar."""
    nombre = os.path.basename(ruta)
    info(f"El proyecto Laravel de {nombre}/ no tiene vendor/ (¿recién "
         "clonado?) — se instalan sus dependencias, sin tocar el código.")
    if not shutil.which('composer'):
        error(f"composer no está instalado: ejecutar `composer install` en "
              f"{ruta} y volver a intentar (o usar `davgen generar --local`).")
        return None
    env, descripcion_php = _entorno_con_php_adecuado()
    if env is None:
        error(f"Se requiere PHP >= 8.2 para instalar Laravel — {descripcion_php}.")
        return None
    r = subprocess.run('composer install --no-interaction --quiet', cwd=ruta,
                       shell=True, env=env, capture_output=True, text=True,
                       timeout=1800)
    if r.returncode != 0 or not _es_laravel_valido(ruta):
        error("composer install falló:")
        dim((r.stderr or r.stdout or '')[-800:])
        return None
    ok(f"Dependencias instaladas en {nombre}/vendor ({descripcion_php})")
    if not os.path.isfile(os.path.join(ruta, '.env')):
        _configurar_env_laravel(ruta, bd)
    return ruta


def _crear_proyecto_laravel(carpeta_backend: str, bd):
    """
    Crea el proyecto Laravel en {03-Backend*}\\backend y configura su .env.
    Preferencia: extraer laravel.zip (plantilla empaquetada junto al exe —
    rápido y sin red); respaldo: composer create-project + install:api.
    Devuelve la ruta del proyecto o None.
    """
    # Un Laravel que YA existe pero no tiene vendor/ no son «restos»: es lo
    # normal tras un `git clone` (vendor no se versiona). Se REPARA con
    # `composer install` y jamás se borra: ahí vive el código propio del
    # proyecto. (Hasta la v4 se eliminaba la carpeta entera y se recreaba,
    # llevándose Custom/, las rutas propias y el bloque then: de bootstrap.)
    for sub in ('servicio', 'backend'):
        existente = os.path.join(carpeta_backend, sub)
        if _es_laravel_existente(existente):
            return _instalar_dependencias_laravel(existente, bd)

    destino = os.path.join(carpeta_backend, 'backend')
    # Hay archivos que no forman un proyecto Laravel: se APARTAN, no se borran.
    if os.path.isdir(destino) and os.listdir(destino):
        apartado = f"{destino}._incompleto-{_ahora():%Y%m%d-%H%M%S}"
        os.replace(destino, apartado)
        warn("backend/ tenía archivos que no forman un proyecto Laravel — se "
             f"movieron a {os.path.basename(apartado)}/ (no se borra nada).")

    # ── Camino 1: plantilla empaquetada (bundle _davgen-*.zip o suelta) ─
    zip_laravel = _obtener_zip_plantilla(['_laravel.zip', 'laravel.zip'],
                                         os.path.dirname(carpeta_backend))
    if zip_laravel:
        info(f"Extrayendo la plantilla Laravel empaquetada: {zip_laravel}…")
        try:
            _extraer_zip(zip_laravel, destino)
        except Exception as e:
            warn(f"No se pudo extraer laravel.zip ({e}) — se usará composer")
            shutil.rmtree(destino, ignore_errors=True)
        else:
            if _es_laravel_valido(destino):
                ok("Proyecto Laravel extraído de laravel.zip (con Sanctum)")
                _configurar_env_laravel(destino, bd)
                return destino
            warn("laravel.zip no contiene un proyecto Laravel válido "
                 "(falta artisan o vendor) — se usará composer")
            shutil.rmtree(destino, ignore_errors=True)

    # ── Camino 2 (respaldo): composer create-project ───────────────────
    if not shutil.which('composer'):
        error("composer no está instalado — no se puede crear el proyecto Laravel.")
        info("Opciones: instalar composer (https://getcomposer.org), crear el "
             "proyecto a mano en backend/, o generar sin entorno con "
             "`davgen generar --local`. Diagnóstico: `davgen doctor`.")
        return None

    # Laravel requiere PHP >= 8.2: buscar uno adecuado (PATH o Laragon)
    env, descripcion_php = _entorno_con_php_adecuado()
    if env is None:
        error(f"Se requiere PHP >= 8.2 para crear el proyecto Laravel — "
              f"{descripcion_php}.")
        info("Instalar PHP 8.2+ (o Laragon) o agregarlo al PATH y volver "
             "a ejecutar.")
        return None
    info(f"Usando {descripcion_php}")

    info("Creando el proyecto Laravel en backend\\ "
         "(composer create-project — puede tardar varios minutos)…")
    r = subprocess.run('composer create-project laravel/laravel backend '
                       '--no-interaction --quiet',
                       cwd=carpeta_backend, shell=True, env=env,
                       capture_output=True, text=True, timeout=1800)
    if r.returncode != 0 or not _es_laravel_valido(destino):
        error("composer create-project falló:")
        dim((r.stderr or r.stdout or '')[-800:])
        # no dejar un proyecto a medias (rompería la siguiente corrida)
        if os.path.isdir(destino):
            shutil.rmtree(destino, ignore_errors=True)
            info("Se limpió backend\\ parcial — corregir la causa y reintentar")
        return None
    ok("Proyecto Laravel creado en backend\\")

    # Laravel 11+ no trae routes/api.php ni Sanctum: instalarlos
    if not os.path.isfile(os.path.join(destino, 'routes', 'api.php')):
        info("Instalando la API (Sanctum): php artisan install:api…")
        r = subprocess.run('php artisan install:api --no-interaction',
                           cwd=destino, shell=True, env=env,
                           capture_output=True, text=True, timeout=900)
        # la migración puede fallar si la BD ya tiene personal_access_tokens
        # (BD compartida): basta con que Sanctum y routes/api.php queden listos
        sanctum_ok = (os.path.isfile(os.path.join(destino, 'routes', 'api.php'))
                      and os.path.isdir(os.path.join(destino, 'vendor',
                                                     'laravel', 'sanctum')))
        if sanctum_ok:
            ok("API + Sanctum instalados"
               + (" (migración omitida: tablas ya existen)"
                  if r.returncode != 0 else ""))
        else:
            warn("php artisan install:api falló — instalar Sanctum a mano")
            dim((r.stderr or r.stdout or '')[-400:])

    _configurar_env_laravel(destino, bd)
    return destino


# ─────────────────────────────────────────────
#  Menú interactivo de opciones [generar]
# ─────────────────────────────────────────────
#  El menú va agrupado por RIESGO, no por orden histórico (v4.36.0).
#  Los 3 primeros flags no son "opciones de generación": escriben FUERA del
#  proyecto (uno en la BD, dos en el FTP de un sitio en vivo) y venían mezclados
#  en la misma lista plana que «generar openapi.json». Con `produccion` marcado
#  por defecto, un ENTER de más desplegaba a producción.
_FLAGS_ACCIONES = [
    ('aplicar_sps',       'Aplicar en la BD: SPs pcru*, seeds y vistas faltantes'),
    ('produccion',        'Subir el BACKEND a la nube por FTP al terminar'),
    ('front',             'Subir el FRONTEND React a la nube por FTP al terminar'),
]
_FLAGS_EXTRAS = [
    ('form_requests',     'FormRequest por tabla — validación 422 + type-hint en controllers'),
    ('tests',             'Suite PHPUnit — AuthTest / RutasTest / RateLimitTest'),
    ('componentes_react', 'Hooks useCrud/useAuth + DataTable / CampoFormulario / SelectRelacion'),
    ('ci',                'GitHub Actions CI/CD — php artisan test + davgen verificar'),
    ('openapi',           'OpenAPI 3 + Swagger UI — documentación generada de la API'),
    ('export',            'Endpoint CSV — POST /{tabla}/export'),
]
_FLAGS_GENERAR_MENU = _FLAGS_ACCIONES + _FLAGS_EXTRAS


def _actualizar_flags_ini(ruta: str, cambios: dict) -> None:
    """Reescribe solo las líneas de flag de [generar] que cambiaron,
    preservando todos los comentarios y el resto del archivo."""
    with open(ruta, encoding='utf-8-sig') as f:
        lineas = f.read().splitlines()
    en_generar = False
    salida = []
    for linea in lineas:
        stripped = linea.strip()
        if stripped.startswith('['):
            en_generar = (stripped.lower() == '[generar]')
            salida.append(linea)
            continue
        if en_generar and not stripped.startswith(';') and '=' in stripped:
            clave = stripped.split('=')[0].strip().lower()
            if clave in cambios:
                salida.append(f"{clave} = {'si' if cambios[clave] else 'no'}")
                continue
        salida.append(linea)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('\n'.join(salida) + '\n')


def _destino_accion(flag: str, cfg: dict) -> str:
    """Adónde escribe realmente una acción, para mostrarlo EN el menú.
    Un menú que dice «subir a la nube» sin decir a qué host obliga a salir a
    revisar el .ini para saber si se está por publicar en el sitio del cliente."""
    bd = cfg.get('bd') or {}
    ftp = cfg.get('ftp') or {}
    if flag == 'aplicar_sps':
        if not bd.get('database'):
            return 'sin [bd] configurada — se omite'
        return f"→ BD «{bd['database']}» en {bd.get('host', '?')}"
    if not cfg.get('ftp_listo'):
        return 'sin [ftp] completo — se omite'
    destino = (ftp.get('url') or ftp.get('host') or '?').rstrip('/')
    if flag == 'produccion':
        return f"→ {destino}{ftp.get('ruta_remota', '/servicio')}"
    if flag == 'front':
        return f"→ {destino}/  (raíz del sitio)"
    return ''


def _confirmar_acciones_externas(cfg: dict, generar: dict) -> bool:
    """Resumen final ANTES de arrancar, con lo que sale del proyecto.

    v4.36.0 — Antes no existía: tras el menú el flujo corría los pasos 0..8 y
    desplegaba por FTP sin una pantalla que dijera «esto es lo que va a pasar».
    Devuelve False si el usuario NO quiere las acciones externas (se genera
    igual, pero solo en local)."""
    externas = [(f, d) for f, d in _FLAGS_ACCIONES if generar.get(f)]
    if not externas:
        return True

    titulo("ANTES DE EMPEZAR — esto sale del proyecto")
    for flag, desc in externas:
        print(f"  {C.YELLOW}·{C.RESET} {C.BOLD}{flag}{C.RESET}  {desc}")
        print(f"      {C.DIM}{_destino_accion(flag, cfg)}{C.RESET}")
    print()
    # OJO: `confirmar` en interactivo solo acepta s/si/sí — ENTER cuenta como NO.
    # Se dice en el texto para que nadie pierda un despliegue por costumbre.
    return confirmar(
        "¿Continuar con estas acciones?  s = sí  ·  ENTER o n = generar solo "
        "en local (sin tocar la BD ni el FTP)")


def _menu_generar_opciones(cfg: dict, ruta_config: str) -> None:
    """Menú de toggle de las opciones [generar], agrupado por riesgo.

    Acepta varios números de una (`2,4,6`), `t` = todos, `n` = ninguno y ENTER
    para continuar. Los cambios se guardan en _configtotal.ini y persisten.
    Antes de arrancar confirma las acciones que escriben fuera del proyecto.
    """
    generar = cfg['generar']
    original = dict(generar)

    titulo("OPCIONES DE GENERACIÓN — ¿qué se hace en esta corrida?")

    def _bloque(titulo_bloque: str, nota: str, flags, desde: int) -> None:
        print(f"  {C.BOLD}{titulo_bloque}{C.RESET}  {C.DIM}{nota}{C.RESET}")
        for i, (flag, desc) in enumerate(flags, desde):
            activo = generar.get(flag, False)
            marca = f"{C.GREEN}[✓]{C.RESET}" if activo else f"{C.DIM}[ ]{C.RESET}"
            print(f"    {marca} {C.BOLD}{i}.{C.RESET} {flag:<18} {C.DIM}{desc}{C.RESET}")
            if activo and flag in dict(_FLAGS_ACCIONES):
                print(f"           {C.DIM}{_destino_accion(flag, cfg)}{C.RESET}")
        print()

    total = len(_FLAGS_GENERAR_MENU)
    while True:
        _bloque('ACCIONES', '— escriben FUERA del proyecto (BD y FTP)',
                _FLAGS_ACCIONES, 1)
        _bloque('EXTRAS DE CÓDIGO', '— solo generan archivos en el proyecto',
                _FLAGS_EXTRAS, len(_FLAGS_ACCIONES) + 1)
        print(f"  {C.DIM}Números para activar/desactivar (se puede «2,4,6») · "
              f"t = todos · n = ninguno · ENTER = continuar{C.RESET}")
        try:
            entrada = input(f"  Opción (1-{total}): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not entrada:
            break
        print()
        if entrada in ('t', 'todos'):
            for flag, _ in _FLAGS_GENERAR_MENU:
                generar[flag] = True
            dim('· todas activadas')
            print()
            continue
        if entrada in ('n', 'ninguno', 'ninguna'):
            for flag, _ in _FLAGS_GENERAR_MENU:
                generar[flag] = False
            dim('· todas desactivadas')
            print()
            continue
        # varios números de una: «2,4,6» o «2 4 6»
        tokens = [t for t in entrada.replace(',', ' ').split() if t]
        validos = 0
        for t in tokens:
            if not t.isdigit() or not 1 <= int(t) <= total:
                dim(f"· «{t}» no es una opción — escribe 1-{total}, t, n o ENTER")
                continue
            flag = _FLAGS_GENERAR_MENU[int(t) - 1][0]
            generar[flag] = not generar[flag]
            estado = f"{C.GREEN}activado{C.RESET}" if generar[flag] \
                else f"{C.DIM}desactivado{C.RESET}"
            dim(f"· {flag} {estado}")
            validos += 1
        if not validos and not tokens:
            dim(f"· escribe 1-{total}, t, n o ENTER para continuar")
        print()

    cambios = {f: v for f, v in generar.items() if v != original.get(f)}
    if cambios and os.path.isfile(ruta_config):
        _actualizar_flags_ini(ruta_config, cambios)
        ok(f"{len(cambios)} opción(es) guardada(s) en _configtotal.ini "
           "— activas también en la próxima ejecución")
    else:
        dim("· opciones sin cambios")

    # Confirmación de lo que sale del proyecto (BD / FTP)
    if not _confirmar_acciones_externas(cfg, generar):
        for flag, _ in _FLAGS_ACCIONES:
            generar[flag] = False
        warn("Acciones externas CANCELADAS solo para esta corrida — se genera "
             "en local, sin tocar la BD ni el FTP. Lo elegido en el menú sigue "
             "guardado en _configtotal.ini para la próxima vez.")


def validar_entorno_backend(no_interactivo: bool = False,
                             solo_listar: bool = False,
                             local: bool = False):
    """
    Paso 1 — el programa busca la carpeta 03-Backend* y antes de continuar valida:
      1. que exista una carpeta 03-Backend* (ej: 03-Backend, 03-Backend-Zapatos);
         si hay varias, el usuario elige una en un menú
      2. que exista el proyecto Laravel en {03-Backend*}\\backend\\
      3. las credenciales [bd] de _configtotal.ini (acceso real a la BD)
    Si todo está bien, crea {03-Backend*}\\_backendGenerado\\ y devuelve su ruta
    (TODO el código se genera AHÍ). Devuelve None si algo falla.
    Con solo_listar=True no crea ni modifica nada (read-only).
    """
    # v4.36.0 — se llamaba «PASO 1» pero corre ANTES del paso «0 · CONFIGURACIÓN»:
    # dos numeraciones distintas conviviendo, con el 1 antes del 0. Ahora es un
    # paso PREVIO, sin número, y la secuencia numerada es una sola: 0..8.
    titulo("PASO PREVIO · VALIDACIÓN DEL ENTORNO — 03-Backend* + _configtotal.ini")

    carpetas = buscar_carpetas_backend()
    if not carpetas:
        error("No se encontró ninguna carpeta 03-Backend* "
              "(ej: 03-Backend, 03-Backend-Zapatos) — el programa no puede continuar.")
        info(f"Se buscó desde: {os.getcwd()} (y sus padres/subcarpetas)")
        return None
    carpeta_backend = _seleccionar_carpeta(carpetas, no_interactivo)
    nombre_carpeta = os.path.basename(carpeta_backend)
    ok(f"Carpeta de backend seleccionada: {carpeta_backend}")
    raiz = os.path.dirname(carpeta_backend)

    # Credenciales primero: se validan y sirven para el .env del Laravel nuevo
    ruta_configtotal = os.path.join(raiz, '_configtotal.ini')
    bd, errores = _leer_credenciales_configtotal(ruta_configtotal)
    # [bd] es opcional salvo con [entrada] tipo = bd: con un mockup se puede
    # generar todo el código sin base de datos (los .sql se ejecutan después).
    sin_bd = not any(bd.get(k) for k in ('host', 'usuario', 'database'))
    if sin_bd and os.path.isfile(ruta_configtotal):
        errores = [e for e in errores if not e.startswith('[bd] ')
                   or 'puerto' in e]
    if local or sin_bd:
        if errores:
            error(f"_configtotal.ini tiene {len(errores)} problema(s):")
            for e in errores:
                print(f"    {C.RED}·{C.RESET} {e}")
            return None
        if local:
            info("Modo --local: solo se generan archivos — no se escribe en la "
                 "BD, no se usa FTP y no se crea Laravel/React.")
        else:
            warn("Sin [bd] en _configtotal.ini: se genera el código, pero no se "
                 "verifica ni se aplica nada en una base de datos.")
        ruta_laravel = next(
            (os.path.join(carpeta_backend, s) for s in ('servicio', 'backend')
             if _es_laravel_existente(os.path.join(carpeta_backend, s))), None)
        if not ruta_laravel and not local and not solo_listar:
            warn(f"No hay proyecto Laravel en {nombre_carpeta} — se creará.")
            ruta_laravel = _crear_proyecto_laravel(carpeta_backend, bd)
            if not ruta_laravel:
                return None
        ruta_generado = os.path.join(carpeta_backend, '_backendGenerado')
        if not solo_listar:
            os.makedirs(ruta_generado, exist_ok=True)
        return ruta_generado
    if errores:
        error(f"_configtotal.ini tiene {len(errores)} problema(s) — "
              "corregir y volver a ejecutar:")
        for e in errores:
            print(f"    {C.RED}·{C.RESET} {e}")
        print(f"\n  Archivo: {C.BOLD}{ruta_configtotal}{C.RESET}\n")
        return None

    try:
        _probar_conexion_bd(bd)
    except Exception as e:
        causa, hacer = diagnostico.explicar_error_bd(e, bd)
        error(f"Sin acceso a la base de datos «{bd['database']}» en {bd['host']} "
              f"(entorno {configuracion.entorno_actual()}): {causa}")
        info(f"Qué hacer: {hacer}")
        info("Sin base de datos igual se puede generar el código: "
             "`davgen generar --local`.")
        return None
    ok(f"Acceso verificado a la base de datos «{bd['database']}» "
       f"({bd['usuario']}@{bd['host']}:{bd['puerto']})")

    # El proyecto Laravel vive en servicio\ (o backend\); si no existe, SE CREA
    # En modo solo_listar se acepta un Laravel sin vendor (no se crea ni modifica).
    _check_laravel = _es_laravel_existente if solo_listar else _es_laravel_valido
    ruta_laravel = None
    for subcarpeta in ('servicio', 'backend'):
        candidata = os.path.join(carpeta_backend, subcarpeta)
        if _check_laravel(candidata):
            ruta_laravel = candidata
            break
    if not ruta_laravel:
        if solo_listar:
            warn(f"No se encontró proyecto Laravel en {nombre_carpeta}\\servicio\\ "
                 f"ni en {nombre_carpeta}\\backend\\ (se continúa en modo listar).")
        else:
            warn(f"No hay proyecto Laravel en {nombre_carpeta}\\servicio\\ ni en "
                 f"{nombre_carpeta}\\backend\\ — se creará automáticamente.")
            ruta_laravel = _crear_proyecto_laravel(carpeta_backend, bd)
            if not ruta_laravel:
                return None
    if ruta_laravel:
        ok(f"Proyecto Laravel listo en {nombre_carpeta}\\"
           f"{os.path.basename(ruta_laravel)}\\")
    else:
        # solo_listar sin Laravel: no hay ruta que mostrar, pero NO se aborta
        dim("(modo listar: sin proyecto Laravel; se omite su validación)")

    ruta_generado = os.path.join(carpeta_backend, '_backendGenerado')
    os.makedirs(ruta_generado, exist_ok=True)
    ok(f"Carpeta {nombre_carpeta}\\_backendGenerado\\ lista")
    return ruta_generado


# ─────────────────────────────────────────────
#  Comandos
# ─────────────────────────────────────────────
def _copiar_a_servicio(ruta_backend: str, carpeta_03backend: str):
    """
    Copia (reemplazando si existen) TODO el backend generado al proyecto
    Laravel real: app\\ completo (Services, Controllers, Middleware, Models,
    Utils) y routes\\api.php. La carpeta servicio se crea si no existe.
    Devuelve (lista de etiquetas copiadas, ruta destino).
    """
    # destino = el proyecto Laravel real: servicio\ o backend\ (el que exista)
    servicio = None
    for subcarpeta in ('servicio', 'backend'):
        candidata = os.path.join(carpeta_03backend, subcarpeta)
        if os.path.isfile(os.path.join(candidata, 'artisan')):
            servicio = candidata
            break
    if servicio is None:
        servicio = os.path.join(carpeta_03backend, 'servicio')
        info(f"La carpeta servicio\\ no existía — se crea en {carpeta_03backend}")
    copiados = []

    def _copiar(origen, destino, etiqueta):
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        reemplazo = os.path.isfile(destino)
        shutil.copy2(origen, destino)
        copiados.append(etiqueta)
        dim(f"· {etiqueta}" + ('  (reemplazado)' if reemplazo else '  (nuevo)'))

    # app\ completo (Services, Controllers, Middleware, Models, Utils)
    origen_app = os.path.join(ruta_backend, 'app')
    for base, _dirs, archivos in os.walk(origen_app):
        for nombre in sorted(archivos):
            if not nombre.endswith('.php'):
                continue
            origen = os.path.join(base, nombre)
            rel = os.path.relpath(origen, ruta_backend)
            _copiar(origen, os.path.join(servicio, rel), rel)

    # Rutas: api.php + web.php + {mod}_api.php (v4.32.0: todos los .php de routes\)
    rutas_origen = os.path.join(ruta_backend, 'routes')
    if os.path.isdir(rutas_origen):
        for nombre_ruta in sorted(os.listdir(rutas_origen)):
            if not nombre_ruta.endswith('.php'):
                continue
            origen = os.path.join(rutas_origen, nombre_ruta)
            _copiar(origen, os.path.join(servicio, 'routes', nombre_ruta),
                    f'routes\\{nombre_ruta}')
    else:
        warn("No se encontró la carpeta routes\\ en el backend generado")

    # bootstrap/app.php (v4.32.0: carga los {mod}_api.php vía then:)
    bootstrap_origen = os.path.join(ruta_backend, 'bootstrap', 'app.php')
    if os.path.isfile(bootstrap_origen):
        _copiar(bootstrap_origen, os.path.join(servicio, 'bootstrap', 'app.php'),
                'bootstrap\\app.php')

    # README de seguridad → raíz del proyecto Laravel: avisa que el código
    # genérico no se modifica y que las tablas de auth son obligatorias
    readme = os.path.join(os.path.dirname(ruta_backend), 'database',
                          'README-SEGURIDAD.md')
    if os.path.isfile(readme):
        _copiar(readme, os.path.join(servicio, 'README-SEGURIDAD.md'),
                'README-SEGURIDAD.md')

    # Tests generados (opcional, [generar] tests=si): copiar las carpetas
    # generadas SIN tocar las pruebas escritas a mano (van en otras carpetas)
    for sub in (os.path.join('tests', 'Feature', 'Generados'),
                os.path.join('tests', 'Datos')):
        origen_dir = os.path.join(ruta_backend, sub)
        if not os.path.isdir(origen_dir):
            continue
        for base, _dirs, archivos in os.walk(origen_dir):
            for nombre in sorted(archivos):
                origen = os.path.join(base, nombre)
                rel = os.path.relpath(origen, ruta_backend)
                _copiar(origen, os.path.join(servicio, rel), rel)
    return copiados, servicio


def _buscar_carpeta_servicios(raiz: str):
    """
    Busca el proyecto React dentro de {raiz}\\04-Front* y devuelve la ruta
    de su carpeta src\\services (ej: 04-Frontend\\frontend\\src\\services).
    Devuelve None si no hay carpeta 04-Front* con un proyecto React.
    """
    try:
        nombres = sorted(os.listdir(raiz))
    except OSError:
        return None
    for nombre in nombres:
        base = os.path.join(raiz, nombre)
        if not (nombre.lower().startswith('04-front') and os.path.isdir(base)):
            continue
        for src in (os.path.join(base, 'frontend', 'src'),
                    os.path.join(base, 'src')):
            if os.path.isdir(src):
                return os.path.join(src, 'services')
    return None


def _crear_proyecto_react(carpeta_04: str) -> bool:
    """Crea el proyecto React con Vite en {04-Front*}/frontend (npm, con red).
    Devuelve True si quedó un proyecto con src/ y package.json."""
    destino = os.path.join(carpeta_04, 'frontend')
    if not shutil.which('npm'):
        return False
    if os.path.isdir(destino) and os.listdir(destino):
        return False        # hay algo que no es un proyecto: no se pisa
    info("Creando el proyecto React en frontend/ (npm create vite — puede "
         "tardar unos minutos)…")
    # `npm create vite` a veces ignora --template: se invoca create-vite directo
    pasos = ('npx -y create-vite@latest frontend --template react',
             'npm install --no-audit --no-fund')
    for n, cmd in enumerate(pasos):
        r = subprocess.run(cmd, cwd=carpeta_04 if n == 0 else destino,
                           shell=True, capture_output=True, text=True,
                           timeout=1800, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            warn(f"Falló `{cmd}`:")
            dim((r.stderr or r.stdout or '')[-600:])
            return False
    return (os.path.isdir(os.path.join(destino, 'src'))
            and os.path.isfile(os.path.join(destino, 'package.json')))


def _asegurar_proyecto_react(raiz: str, local: bool = False):
    """
    Devuelve (carpeta_services, es_nuevo).
    es_nuevo=True cuando el proyecto React se creó en esta ejecución (desde un
    _react.zip propio del usuario o, si no hay, con npm). En modo local no se
    crea nada. Devuelve (None, False) si no hay dónde generar.
    """
    carpeta = _buscar_carpeta_servicios(raiz)
    if carpeta:
        return (carpeta, False)   # proyecto ya existía
    if local:
        return (None, False)
    try:
        carpeta_04 = next(
            (os.path.join(raiz, d) for d in sorted(os.listdir(raiz))
             if d.lower().startswith('04-front')
             and os.path.isdir(os.path.join(raiz, d))), None)
    except OSError:
        return (None, False)
    if not carpeta_04:
        return (None, False)
    destino = os.path.join(carpeta_04, 'frontend')
    creado = False
    zip_react = _obtener_zip_plantilla(['_react.zip', 'react.zip'], raiz)
    if zip_react:
        info(f"Extrayendo la plantilla React empaquetada: {zip_react}…")
        try:
            _extraer_zip(zip_react, destino)
            creado = os.path.isdir(os.path.join(destino, 'src'))
        except Exception as e:
            warn(f"No se pudo extraer _react.zip ({e})")
        if creado:
            ok("Proyecto React extraído de _react.zip")
        else:
            warn("_react.zip no contiene un proyecto React válido (falta src/)")
    if not creado:
        creado = _crear_proyecto_react(carpeta_04)
        if creado:
            ok("Proyecto React creado en frontend/ (Vite)")
    if not creado:
        return (None, False)
    # La plantilla de Vite trae su App.jsx de muestra: se borra para que
    # generar_app_jsx() cree la pantalla de login en su lugar.
    app_jsx = os.path.join(destino, 'src', 'App.jsx')
    if os.path.isfile(app_jsx):
        os.remove(app_jsx)
    return (os.path.join(destino, 'src', 'services'), True)


def _mostrar_tablas(tablas) -> None:
    print(f"  {C.GREEN}Entidades/tablas: {len(tablas)}{C.RESET}\n")
    for i, t in enumerate(tablas, 1):
        print(f"  {C.DIM}[{i}]{C.RESET} {C.BOLD}{t['tabla']}{C.RESET} "
              f"({len(t['columnas'])} col)  {C.DIM}{t['origen']}{C.RESET}")
    print()


def _mostrar_requisitos(cfg: dict, puntos=None) -> int:
    """Lista lo que el proyecto necesita (mockup, base de datos, FTP…) con su
    estado y qué hacer con lo que falta. Devuelve cuántos puntos faltan."""
    entorno = cfg.get('entorno', 'desarrollo').upper()
    origen = cfg.get('archivo_acceso') or '_configtotal.ini'
    print(f"\n  {C.BOLD}REQUISITOS{C.RESET}  {C.DIM}entorno {entorno} · accesos "
          f"en {origen}{C.RESET}")
    faltan = 0
    for estado, nombre, detalle, hacer in (puntos or diagnostico.requisitos(cfg)):
        marca = {'ok': f"{C.GREEN}✓{C.RESET}", 'aviso': f"{C.YELLOW}⚠{C.RESET}",
                 'falta': f"{C.RED}✗{C.RESET}"}[estado]
        print(f"  {marca} {C.BOLD}{nombre}:{C.RESET} {detalle}")
        if hacer:
            print(f"      {C.DIM}→ {hacer}{C.RESET}")
        faltan += estado == 'falta'
    print(f"  {C.DIM}· {diagnostico.INTERFAZ}{C.RESET}\n")
    return faltan


def cmd_generar(solo_listar: bool, no_interactivo: bool,
                produccion: str, ruta_backend_generado: str,
                front: str = 'preguntar', solo_si_cambio: bool = False,
                local: bool = False) -> int:
    # raíz = carpeta que contiene 03-Backend (ahí vive _configtotal.ini)
    raiz = os.path.dirname(os.path.dirname(ruta_backend_generado))

    # ── Configuración: si tiene errores, pedir al usuario que la complete ──
    titulo("0 · CONFIGURACIÓN — _configtotal.ini")
    cfg, errores = configuracion.cargar(raiz, archivo='_configtotal.ini')
    if errores:
        error(f"_configtotal.ini tiene {len(errores)} problema(s) — corregir y volver a ejecutar:")
        print()
        for e in errores:
            print(f"    {C.RED}·{C.RESET} {e}")
        print(f"\n  Archivo: {C.BOLD}{cfg.get('ruta_config', os.path.join(raiz, '_configtotal.ini'))}{C.RESET}\n")
        return 1
    # TODO lo generado va dentro de 03-Backend\_backendGenerado
    cfg['salida'] = ruta_backend_generado
    ok(f"_configtotal.ini válido — proyecto «{cfg['nombre']}» · módulo {cfg['modulo']} "
       f"· entrada: {cfg['tipo']}")
    for aviso in cfg.get('avisos', []):
        warn(aviso)
    if not solo_listar and not _exigir_clave_admin(raiz, cfg, no_interactivo or local):
        return 1
    _mostrar_requisitos(cfg)
    if local:
        # --local: nada sale del proyecto en esta corrida (el .ini no se toca)
        cfg['generar'].update(aplicar_sps=False, produccion=False, front=False)
        produccion = front = 'no'
    solo_desarrollo = cfg['con_entornos'] and cfg['entorno'] != 'produccion'
    if solo_desarrollo:
        # Con archivos de acceso por entorno, publicar es SIEMPRE una decisión
        # explícita: en desarrollo no se sube nada, diga lo que diga el .ini.
        if (cfg['generar'].get('produccion') or cfg['generar'].get('front')
                or 'si' in (produccion, front)) and not local:
            info("Entorno de DESARROLLO: no se publica nada por FTP. Para "
                 "publicar:  davgen generar --entorno produccion")
        cfg['generar'].update(produccion=False, front=False)
        produccion = front = 'no'

    # Con qué versión se generó antes este proyecto (y si el .exe actual difiere)
    avisar_version_proyecto(cfg['salida'])

    # ── Menú de opciones [generar] — solo en modo interactivo ──────────
    if not no_interactivo and not solo_listar:
        _menu_generar_opciones(cfg, cfg['ruta_config'])
    # Aplicar flags del INI a produccion/front (menú o --si): si el usuario
    # no pasó --produccion/--front por CLI, se respeta lo guardado en el INI.
    if solo_desarrollo:
        cfg['generar'].update(produccion=False, front=False)
    if produccion == 'preguntar':
        produccion = 'si' if cfg['generar'].get('produccion', False) else 'no'
    if front == 'preguntar':
        front = 'si' if cfg['generar'].get('front', False) else 'no'

    # ── 1 · ENTRADA ────────────────────────────────────────────────────
    titulo("1 · ENTRADA — " + ('mockup' if cfg['tipo'] == 'mockup' else 'base de datos'))
    sin_mockup = False   # True cuando la carpeta no tiene index.html (continúa sin CRUD)
    if cfg['tipo'] == 'mockup':
        ruta_mockup = cfg['ruta_mockup']
        if os.path.isdir(ruta_mockup):
            idx_html = os.path.join(ruta_mockup, 'index.html')
            if os.path.isfile(idx_html):
                ruta_mockup = idx_html
                cfg['ruta_mockup'] = idx_html
            else:
                warn(f"No se encontró index.html en la carpeta «{cfg['mockup']}»")
                info("Guardar el diseño como index.html en esa carpeta y volver a ejecutar.")
                info("Se continúa con las otras etapas (seguridad + backend sin CRUD de negocio).")
                sin_mockup = True
        if not sin_mockup:
            with open(ruta_mockup, encoding='utf-8', errors='replace') as _f:
                _txt = _f.read()
            _tipo = ('bundle Design Canvas / Bolt.new'
                     if '__bundler/manifest' in _txt and '__bundler/template' in _txt
                     else 'HTML estático')
            dim(f"Tipo de mockup detectado: {_tipo}")
            entidades = entrada.analizar_mockup(ruta_mockup)
        else:
            entidades = []
        tablas = esquema.construir_tablas(entidades, cfg['modulo'])
        cfg['origen_entrada'] = (f"mockup `{cfg['mockup']}`" if not sin_mockup
                                 else f"sin mockup (falta index.html en «{cfg['mockup']}»)")
    else:
        try:
            tablas = entrada.leer_bd(cfg['bd'])
        except Exception as e:
            error(f"No se pudo leer la base de datos: {_bd.mensaje_error(e)}")
            info("Revisar la sección [bd] de config.ini")
            return 1
        cfg['origen_entrada'] = f"base de datos `{cfg['bd']['database']}`"

    tablas = [t for t in tablas
              if t['entidad'] not in cfg['excluir'] and t['tabla'] not in cfg['excluir']]
    if not tablas:
        if cfg['tipo'] == 'bd':
            # BD con solo tablas de seguridad: se genera el backbone de
            # autenticación (login + 2FA + admin), sin CRUD de negocio.
            warn("La BD no tiene tablas de negocio — se generará solo el "
                 "backbone de autenticación (login, 2FA, administración).")
            info("Para el CRUD de negocio: crear las tablas tbl_{modulo}_* "
                 "en la BD y volver a ejecutar.")
        elif sin_mockup:
            # Carpeta de mockup sin index.html: se genera solo el backbone.
            warn("Sin entidades de negocio — se genera solo el backbone de autenticación.")
        else:
            error("No se detectaron entidades. Revisar el mockup o [opciones] excluir.")
            return 1
    else:
        _mostrar_tablas(tablas)

    # ── sincronizar: regenerar SOLO si el esquema cambió ────────────────
    if solo_si_cambio:
        previo = leer_snapshot_esquema(ruta_backend_generado)
        if previo is None:
            info("Sin snapshot previo del esquema — primera corrida: "
                 "se genera todo.")
        else:
            cambios = delta_esquema(previo, snapshot_esquema(tablas))
            if not cambios:
                ok("La BD no cambió desde la última generación — nada que "
                   "regenerar ni subir.")
                return 0
            warn(f"El esquema cambió ({len(cambios)} diferencia(s)) — se "
                 f"regenera y despliega:")
            for c in cambios[:15]:
                dim(f"· {c}")
            if len(cambios) > 15:
                dim(f"· … y {len(cambios) - 15} más")

    if solo_listar:
        info("Modo --listar: análisis terminado, no se generó nada.")
        return 0

    # ── Prerrequisito: el backbone de seguridad (tbl_seg_*) debe existir en la
    #    BD; si falta, se detiene (ejecutar 00-seguridad.sql primero). ───────
    if not local and not _exigir_tablas_seguridad(cfg):
        return 1

    if not no_interactivo and not confirmar(
            f"¿Generar el proyecto con estas {len(tablas)} tabla(s)?"):
        warn("Cancelado. Ajustar [opciones] excluir en config.ini si hay ruido.")
        return 0

    cfg['tablas'] = tablas
    salida = cfg['salida']

    # ── Integridad: respaldar y avisar si lo generado fue editado a mano ──
    editados = verificar_manifiesto(salida)
    if editados:
        warn(f"{len(editados)} archivo(s) generados fueron editados a mano "
             f"y serán SOBRESCRITOS:")
        for r in editados[:10]:
            dim(f"· {r}")
        if len(editados) > 10:
            dim(f"· … y {len(editados) - 10} más")
        # respaldo: las ediciones no se conservan en el código, pero tampoco
        # se pierden — copia previa a la regeneración
        respaldo = os.path.join(salida, '_respaldo-ediciones',
                                _ahora().strftime('%Y-%m-%d_%H%M'))
        for rel in editados:
            origen = os.path.join(salida, rel)
            destino = os.path.join(respaldo, rel.replace('../', ''))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copy2(origen, destino)
        info(f"Respaldo de las ediciones en {respaldo}")
        info("El código generado no se edita: personalizar extendiendo "
             "(ver _prompts\\prompt-4-personalizacion.md) o en la BD (tbl_seg_*).")
        if not no_interactivo and not confirmar(
                "¿Continuar y sobrescribir los archivos editados "
                "(quedan respaldados)?"):
            warn("Cancelado: mover la personalización fuera del código "
                 "generado y volver a ejecutar.")
            return 0

    reg = Registro(salida)

    # ── 2 · ESTRUCTURA (todo dentro de 03-Backend\_backendGenerado) ────
    titulo("2 · ESTRUCTURA — 03-Backend\\_backendGenerado\\")
    rutas = {clave: os.path.join(salida, clave)
             for clave in ('mockup', 'database', 'backend', 'documentacion')}
    cfg['ruta_backend'] = rutas['backend']
    for r in rutas.values():
        os.makedirs(r, exist_ok=True)
    if cfg['tipo'] == 'mockup' and os.path.isfile(cfg['ruta_mockup']):
        destino = os.path.join(rutas['mockup'], os.path.basename(cfg['ruta_mockup']))
        shutil.copy2(cfg['ruta_mockup'], destino)
        reg.add('mockup', destino)
    else:
        nota = os.path.join(rutas['mockup'], 'origen.txt')
        with open(nota, 'w', encoding='utf-8') as f:
            f.write(f"Entrada: {cfg['origen_entrada']}\n"
                    f"Generado: {_ahora():%Y-%m-%d %H:%M}\n")
        reg.add('mockup', nota)
    ok(f"Estructura creada en {salida}")

    # ── 3 · BASE DE DATOS ───────────────────────────────────────────────
    titulo("3 · BASE DE DATOS — seguridad+acceso+2FA+archivos → negocio → SPs")
    reg.add('database', gen_sql.generar_seguridad(rutas['database'], '',
                                                  tablas, cfg))
    ok(f"01_seguridad.sql (admin {cfg['admin_email']}, roles admin/usuario/cliente, "
       "2FA, archivos, permisos, parámetros, cola de accesos — administrar en la BD)")
    reg.add('database', gen_sql.generar_readme_seguridad(rutas['database'],
                                                         cfg['admin_email']))
    ok("README-SEGURIDAD.md (tablas OBLIGATORIAS de autenticación + "
       "código genérico que NO se modifica)")

    # carpeta 02-* del proyecto: 00-seguridad.sql + readme_cero.md
    # Acepta cualquier nombre que empiece con '02-' (ej: 02-Base-de-datos,
    # 02-Base de datos, 02-BD) o el prefijo '02 ' con espacio.
    def _es_carpeta_02(nombre: str) -> bool:
        n = nombre.lower()
        return (n.startswith('02-') or n.startswith('02 ')) and \
               os.path.isdir(os.path.join(raiz, nombre))

    carpeta_02 = next(
        (os.path.join(raiz, d) for d in sorted(os.listdir(raiz))
         if _es_carpeta_02(d)), None)
    if carpeta_02:
        shutil.copy2(os.path.join(rutas['database'], '01_seguridad.sql'),
                     os.path.join(carpeta_02, '00-seguridad.sql'))
        reg.add('database', gen_sql.generar_readme_cero(carpeta_02))
        ok(f"00-seguridad.sql + readme_cero.md → {carpeta_02}")
    else:
        dim(f"(sin carpeta 02-* en {raiz} — 00-seguridad.sql no se copia ahí)")
    if tablas:
        reg.add('database', gen_sql.generar_negocio(tablas, rutas['database'], cfg['nombre']))
        if cfg['tipo'] == 'mockup':
            ok(f"02_negocio.sql ({len(tablas)} tablas + vistas, orden FK)")
        else:
            # tipo=bd: volcar el DDL leído de la BD para que el bundle sea
            # autosuficiente (reproducible en una BD nueva). G-4.
            ok(f"02_negocio.sql ({len(tablas)} tablas + vistas reconstruidas "
               "de la BD, orden FK) — bundle autosuficiente")
    else:
        dim("(sin tablas de negocio: 02_negocio.sql no se genera)")

    # SPs para TODAS las tablas: las del mockup/bd + las adicionales de la BD
    # (tipo=mockup con credenciales BD → lee la BD y agrega tablas sin SP)
    tablas_para_sps = list(tablas)
    if cfg['tipo'] == 'mockup' and cfg['bd'].get('database') and not local:
        try:
            tablas_bd = entrada.leer_bd(cfg['bd'], incluir_seg=True)
            nombres_ya = {t['tabla'] for t in tablas_para_sps}
            tablas_extra = [
                t for t in tablas_bd
                if t['tabla'] not in nombres_ya
                and t['entidad'] not in cfg['excluir']
                and t['tabla'] not in cfg['excluir']
            ]
            if tablas_extra:
                info(f"BD: {len(tablas_extra)} tabla(s) adicional(es) incluidas "
                     f"en 03_procedimientos.sql:")
                for t in tablas_extra:
                    dim(f"· {t['tabla']} ({len(t['columnas'])} col)")
                tablas_para_sps.extend(tablas_extra)
        except Exception as e:
            warn(f"No se pudieron leer tablas adicionales de la BD: {_bd.mensaje_error(e)}")

    ruta_sps = gen_sql.generar_procedimientos(tablas_para_sps, rutas['database'], cfg['nombre'])
    reg.add('database', ruta_sps)
    ok(f"03_procedimientos.sql ({len(tablas_para_sps)} SPs, DELETE lógico funcional)")

    # copiar TODOS los scripts SQL a 02-Base* (no solo 00-seguridad.sql):
    # 02_negocio.sql (si existe) y 03_procedimientos.sql con su nombre real
    if carpeta_02:
        copiados_sql = []
        for nombre in ('02_negocio.sql', '03_procedimientos.sql'):
            origen = os.path.join(rutas['database'], nombre)
            if os.path.isfile(origen):
                shutil.copy2(origen, os.path.join(carpeta_02, nombre))
                copiados_sql.append(nombre)
        if copiados_sql:
            ok(f"{', '.join(copiados_sql)} → {carpeta_02}")

    # ejecutar/comparar los SPs pcru* en la BD (si hay credenciales [bd])
    if tablas and cfg['bd'].get('host') and not local:
        _decidir_aplicar_sps(cfg, ruta_sps, no_interactivo)

    # aplicar seeds de seguridad + vistas vis_* FALTANTES (mismo flag
    # aplicar_sps; una vista existente NUNCA se reemplaza — puede estar
    # personalizada). Así las credenciales anunciadas al final y los `sel`
    # funcionan sin ejecutar los .sql a mano.
    if cfg['bd'].get('host') and not local:
        _decidir_aplicar_seguridad(cfg, rutas['database'], no_interactivo)

    # ── 4 · BACKEND ─────────────────────────────────────────────────────
    titulo("4 · BACKEND — Laravel: servicios (auth+2FA) → controllers → API")
    reg.add('backend', gen_backend.generar_backend(tablas, cfg, rutas['backend']))
    ok(f"Servicios: BaseService (valida auth normal + 2FA en cada operación) "
       f"+ {len(tablas)} service(s) de tabla")
    ok(f"Controllers delgados (delegan en los servicios): base, Auth 2FA + menú, "
       f"VerificarPermiso, Archivo, /seguridad/*, {len(tablas)} controller(s)")
    ok("API completa en routes/api.php")
    info(f"Backend generado en: {rutas['backend']}")
    if cfg['generar'].get('form_requests'):
        ok("FormRequests por tabla (validación 422 desde el esquema) — extra activo")
    if cfg['generar'].get('export'):
        ok("Endpoint /export CSV por tabla — extra activo")

    # ── 4b · TESTING PHP opcional (PHPUnit) → tests\ del mirror ──────────
    if cfg['generar'].get('tests'):
        pruebas_php = gen_pruebas.generar_pruebas(tablas, cfg, rutas['backend'])
        reg.add('testing', pruebas_php)
        ok(f"{len(pruebas_php)} archivo(s) de pruebas PHPUnit (auth, rutas, "
           "rate-limit, datos) — extra activo")

    # ── 5 · SERVICIO — Controllers + routes\api.php → proyecto Laravel ──
    carpeta_03backend = os.path.dirname(salida)
    titulo("5 · SERVICIO — Controllers + routes\\api.php → proyecto Laravel")
    hay_laravel = any(
        os.path.isfile(os.path.join(carpeta_03backend, s, 'artisan'))
        for s in ('servicio', 'backend'))
    if local and not hay_laravel:
        # sin proyecto Laravel no hay dónde copiar: el espejo es el resultado
        copiados, destino_servicio = [], rutas['backend']
        dim("· (modo --local sin proyecto Laravel: el código queda solo en el "
            "espejo _backendGenerado/backend)")
    else:
        copiados, destino_servicio = _copiar_a_servicio(rutas['backend'],
                                                        carpeta_03backend)
        ok(f"{len(copiados)} archivo(s) copiados/reemplazados en {destino_servicio}")
        gen_prompts.escribir_avisos_no_modificar([
            os.path.join(destino_servicio, 'app', 'Http', 'Controllers'),
            os.path.join(destino_servicio, 'app', 'Services'),
            os.path.join(destino_servicio, 'app', 'Http', 'Middleware'),
            os.path.join(destino_servicio, 'app', 'Utils'),
        ])
        dim("· _NO-MODIFICAR.md en las carpetas generadas del Laravel")
    # proyecto Laravel COMPLETO y funcional (con vendor) — lo que se despliega
    cfg['ruta_laravel'] = destino_servicio

    # ── 6 · FRONTEND — base + servicios + páginas CRUD → 04-Front*\..\src ──
    titulo("6 · FRONTEND — base (api/auth) + servicios JS + páginas CRUD")
    # ubicación final del frontend generado (para el manifiesto de integridad)
    front_raiz, front_archivos = None, []
    carpeta_services, es_nuevo_front = _asegurar_proyecto_react(raiz, local)
    front_espejo = False
    if not carpeta_services and local:
        # sin proyecto React: el frontend se genera en el espejo
        carpeta_services = os.path.join(salida, 'frontend', 'src', 'services')
        os.makedirs(carpeta_services, exist_ok=True)
        front_espejo = True
        dim("· (modo --local sin proyecto React: el frontend queda en el espejo "
            "_backendGenerado/frontend/src)")
    if carpeta_services:
        base_front = gen_servicios.generar_base_frontend(carpeta_services)
        if base_front:
            reg.add('frontend', base_front)
            for b in base_front:
                dim(f"· services\\{os.path.basename(b)}  (base creada: no existía)")
        else:
            dim("· api.js / authService.js ya existen — no se tocan")

        # proyecto React (con package.json) = ...\frontend (padre de src)
        cfg['ruta_front'] = os.path.dirname(os.path.dirname(carpeta_services))

        app_jsx = gen_servicios.generar_app_jsx(os.path.dirname(carpeta_services),
                                                cfg['nombre'])
        if gen_servicios.ajustar_index_html(cfg['ruta_front'], cfg['nombre']):
            ok("index.html: idioma de la página (es) y título con el nombre del sistema")
        if app_jsx:
            ok(f"App.jsx creado con pantalla de login (solo si no existía)")
        else:
            dim("· App.jsx ya existe — no se toca")

        generados = gen_servicios.generar_servicios(tablas, cfg, carpeta_services)
        reg.add('frontend', generados)
        for g in generados:
            dim(f"· services\\{os.path.basename(g)}")
        ok(f"{len(generados)} servicio(s) JS generados en {carpeta_services}")

        carpeta_paginas = os.path.join(os.path.dirname(carpeta_services),
                                       'pages', 'generados')
        paginas = gen_servicios.generar_paginas(tablas, cfg, carpeta_paginas)
        reg.add('frontend', paginas)
        for pg in paginas:
            dim(f"· pages\\generados\\{os.path.basename(pg)}")
        ok(f"{len(paginas) - 1} página(s) CRUD + rutas.jsx generadas en {carpeta_paginas}")
        info("rutas.jsx es OPCIONAL: ver su cabecera para sumarlas a App.jsx")
        gen_prompts.escribir_avisos_no_modificar([carpeta_services, carpeta_paginas])
        dim("· _NO-MODIFICAR.md en services\\ y pages\\generados\\")
        # raíz = carpeta src\ (padre de services\); archivos = todo lo generado
        front_raiz = os.path.dirname(carpeta_services)
        front_archivos = list(base_front or []) + list(generados) + list(paginas)

        # ── Tailwind + DaisyUI + Capacitor ──────────────────────────────
        import json as _json
        front_dir = os.path.dirname(front_raiz)   # …/frontend (tiene package.json)
        nombre_proyecto = cfg['nombre'] or 'App'

        # Detectar qué falta
        try:
            with open(os.path.join(front_dir, 'package.json'),
                      encoding='utf-8') as _f:
                _pkg = _json.load(_f)
            _deps = {**_pkg.get('dependencies', {}),
                     **_pkg.get('devDependencies', {})}
        except Exception:
            _deps = {}
        tw_falta = 'tailwindcss' not in _deps
        cap_falta = not os.path.isfile(
            os.path.join(front_dir, 'capacitor.config.json'))

        if local:
            dim("· (modo --local: no se instala Tailwind/DaisyUI/Capacitor)")
        elif es_nuevo_front:
            # Proyecto recién creado: instalar/configurar siempre
            if gen_servicios.configurar_tailwind_daisyui(front_dir):
                ok("Tailwind CSS + DaisyUI instalados en el nuevo proyecto")
            else:
                dim("· Tailwind + DaisyUI ya incluidos en el zip")
            if gen_servicios.configurar_capacitor(front_dir, nombre_proyecto):
                ok("capacitor.config.json creado")
            else:
                dim("· capacitor.config.json ya incluido en el zip")
        else:
            # Proyecto existente: solo tocar si falta algo Y el usuario lo confirma
            pendientes = []
            if tw_falta:
                pendientes.append("Tailwind CSS + DaisyUI")
            if cap_falta:
                pendientes.append("Capacitor (APK)")
            if pendientes:
                lista = ', '.join(pendientes)
                if confirmar(
                    f"¿Actualizar el frontend existente con {lista}?",
                    no_interactivo, defecto=False
                ):
                    if tw_falta:
                        gen_servicios.configurar_tailwind_daisyui(front_dir)
                        ok("Tailwind CSS + DaisyUI instalados")
                    if cap_falta:
                        gen_servicios.configurar_capacitor(
                            front_dir, nombre_proyecto)
                        ok("capacitor.config.json creado")
                        info("  npm install @capacitor/core @capacitor/cli"
                             " @capacitor/android")
                        info("  npx cap add android   (una sola vez)")
                        info("  npx cap sync          (tras cada build)")
                        info("  Android Studio → Build → Generate Signed APK")
                else:
                    dim(f"· Frontend existente sin cambios ({lista} omitido)")
            else:
                dim("· Tailwind + DaisyUI + Capacitor ya configurados")

        # ── Google: service + botón + cola de aprobación ────────────────
        # SIEMPRE (no es un extra opcional): Google viene activado de fábrica
        # en la BD (google_auth_activo=1 + google_client_id sembrados), así que
        # el frontend tiene que traer con qué usarlo. Son archivos NUEVOS y
        # aditivos: no pisan authService.js ni App.jsx (personalizables), que
        # era el motivo de que Google nunca llegara a los proyectos ya creados.
        google_front = gen_google.generar_google(cfg, front_raiz)
        reg.add('frontend', google_front)
        front_archivos += list(google_front)
        for gf in google_front:
            dim(f"· {os.path.relpath(gf, front_raiz)}")
        ok("Login con Google listo para montar — botón + cola de aprobación "
           "(ver components\\generados\\LEEME-GOOGLE.md)")

        # ── Tema claro / oscuro / del sistema — SIEMPRE, y aditivo ───────
        tema_front = gen_tema.generar_tema(cfg, front_raiz)
        reg.add('frontend', tema_front)
        front_archivos += list(tema_front)
        ok("Tema claro, oscuro o del sistema + selector "
           "(ver components\\generados\\LEEME-TEMA.md)")

        # ── Privacidad y términos de uso — SIEMPRE, y aditivo ────────────
        legal_front = gen_legal.generar_legal(cfg, front_raiz)
        reg.add('frontend', legal_front)
        front_archivos += list(legal_front)
        ok("Privacidad y términos de uso"
           + ("" if cfg['legal']['responsable'] else
              " — falta [legal] responsable y contacto en _configtotal.ini")
           + " (ver components\\generados\\LEEME-LEGAL.md)")

        # hooks y componentes React reutilizables (opcional)
        if cfg['generar'].get('componentes_react'):
            componentes = gen_componentes.generar_componentes(cfg, front_raiz)
            reg.add('frontend', componentes)
            front_archivos += list(componentes)
            for cmp in componentes:
                dim(f"· {os.path.relpath(cmp, front_raiz)}")
            ok(f"{len(componentes)} hook(s)/componente(s) React reutilizables — "
               "extra activo")
    else:
        warn("No hay proyecto React en 04-Front* y no se pudo crear (hace falta "
             "npm) — se omite la generación de servicios y páginas JS")

    # ── 7 · TESTING — pruebas de API + checklist + configuración de uso ──
    titulo("7 · TESTING — api.http + checklist + configuración de uso")
    carpeta_testing = os.path.join(salida, 'testing')
    pruebas = gen_testing.generar_testing(tablas, cfg, carpeta_testing)
    reg.add('testing', pruebas)
    for pr in pruebas:
        dim(f"· testing\\{os.path.basename(pr)}")
    ok(f"{len(pruebas)} archivo(s) de pruebas/uso generados en {carpeta_testing}")
    # misma lógica que 03/04: si existe la carpeta 05-Test*, copiarlos ahí
    carpeta_05 = next(
        (os.path.join(raiz, d) for d in sorted(os.listdir(raiz))
         if d.lower().startswith('05-test')
         and os.path.isdir(os.path.join(raiz, d))), None)
    if carpeta_05:
        destino_05 = os.path.join(carpeta_05, 'generados')
        os.makedirs(destino_05, exist_ok=True)
        for pr in pruebas:
            shutil.copy2(pr, os.path.join(destino_05, os.path.basename(pr)))
        ok(f"Pruebas copiadas también a {destino_05} (sin tocar las manuales)")
    info("Leer testing\\COMO-USAR.md: pasos de BD, backend, front y pruebas")

    # ── 8 · DOCUMENTACIÓN ───────────────────────────────────────────────
    titulo("8 · DOCUMENTACIÓN")
    reg.add('documentacion', _generar_docs(cfg, rutas['documentacion']))
    ok("guia.md (BD + API + frontend + 2FA + archivos)")

    # prompts de IA por fase, con el módulo del proyecto ya resuelto
    prompts = gen_prompts.generar_prompts(raiz, cfg['modulo'])
    reg.add('_prompts', prompts)
    ok(f"{len(prompts)} prompt(s) de IA en {os.path.join(raiz, '_prompts')} "
       f"(mockup, tablas, SPs de dominio, personalización)")

    # plantillas de documentos (solo las que falten: nunca pisa las llenadas)
    plantillas = gen_plantillas.generar_plantillas(raiz)
    if plantillas:
        reg.add('documentacion', plantillas)
        ok(f"{len(plantillas)} plantilla(s) de documentos repuesta(s) — "
           "COMPLETARLAS (requisitos, mockups, BD, plan de pruebas)")
    reg.add('documentacion', gen_plantillas.generar_leeme_html(raiz))
    ok("leeme.html actualizado — guía interactiva del proyecto (raíz)")
    ruta_md = gen_plantillas.generar_leeme_md(raiz)
    reg.add('documentacion', ruta_md)
    ok("_davgen.leeme.md actualizado — guía rápida en markdown")
    _abrir_archivo(ruta_md)

    reg.add('documentacion', gen_plantillas.generar_guia_google(raiz))
    ok("CONFIGURAR-GOOGLE-AUTH.md — acción OPCIONAL: habilitar login con Google")

    # GU-5 · mostrar las credenciales sembradas (mismo correo que el seed/docs)
    titulo("ACCESO INICIAL — credenciales sembradas en tbl_seg_usuario")
    warn(f"Admin: {cfg['admin_email']}  ·  contraseña: la que escribiste en "
         f"{configuracion.archivo_de_secretos(raiz)} ([seguridad] admin_password). "
         "Cambiarla desde la aplicación al primer ingreso.")
    if cfg.get('owner_email'):
        info(f"Owner Google: {cfg['owner_email']} — entra con Google desde el inicio "
             "y aprueba/deniega el acceso de otros correos.")
    else:
        dim("Sin owner_email configurado: el login con Google solo servirá para "
            "usuarios ya cargados (ver CONFIGURAR-GOOGLE-AUTH.md).")

    # ── 8b · DEVOPS opcional: OpenAPI/Swagger y CI (GitHub Actions) ──────
    if cfg['generar'].get('openapi'):
        openapi = gen_devops.generar_openapi(tablas, cfg, rutas['documentacion'])
        reg.add('documentacion', openapi)
        ok("openapi.json + swagger.html (especificación OpenAPI 3) — extra activo")
    if cfg['generar'].get('ci'):
        laravel_rel = os.path.relpath(destino_servicio, raiz).replace('\\', '/')
        front_rel = (os.path.relpath(cfg['ruta_front'], raiz).replace('\\', '/')
                     if cfg.get('ruta_front') else None)
        ci = gen_devops.generar_ci(raiz, laravel_rel, front_rel, cfg['autor'])
        reg.add('documentacion', ci)
        ok(".github/workflows/ci.yml (tests + davgen verificar) — extra activo")

    if configuracion.escribir_ejemplo(raiz):
        dim("· _configtotal.ejemplo.ini actualizado (copia sin secretos, para git)")

    # ── 9 · RESUMEN + 10 · PRODUCCIÓN (backend + frontend) ─────────────
    resumen_final(cfg, reg)
    decidir_produccion(cfg, cfg, no_interactivo, produccion)
    if produccion == 'si' and cfg.get('ftp_listo') and not local:
        # recién publicado: comprobar DESDE AFUERA que no se bajan .env ni logs
        _avisar_exposicion(cfg)
    decidir_frontend(cfg, no_interactivo, front)
    escribir_manifiesto(salida, reg)
    # huella del esquema para `sincronizar`: regenerar solo si la BD cambia
    escribir_snapshot_esquema(salida, tablas)
    # manifiesto de INTEGRIDAD: hashes del código en su ubicación FINAL
    # (Laravel real, frontend, SQL) + SPs/vistas esperados → `davgen verificar`
    laravel_archivos = [os.path.join(destino_servicio, rel) for rel in copiados]
    if front_espejo:
        cfg.pop('ruta_front', None)
    sql_archivos = [os.path.join(rutas['database'], f)
                    for f in sorted(os.listdir(rutas['database']))
                    if f.lower().endswith('.sql')]
    escribir_manifiesto_integridad(
        salida, raiz, tablas,
        laravel_raiz=destino_servicio, laravel_archivos=laravel_archivos,
        front_raiz=front_raiz, front_archivos=front_archivos,
        database_raiz=rutas['database'], database_archivos=sql_archivos)
    dim("· .davgen-integridad.json escrito (base para `davgen verificar`)")
    return 0


def cmd_verificar(ruta_backend_generado: str) -> int:
    """Comando `verificar`: compara el código generado en su ubicación final
    (Laravel, frontend, SQL) y los SPs/vistas de la BD contra el manifiesto de
    integridad escrito en la última generación. Avisa de cualquier edición
    manual. Código de salida: 0 = todo intacto, 1 = hay modificaciones/faltantes."""
    raiz = os.path.dirname(os.path.dirname(ruta_backend_generado))
    salida = ruta_backend_generado

    # SPs/vistas en la BD: best-effort (si [bd] está bien y conecta)
    sps_bd = vistas_bd = None
    cfg, errores = configuracion.cargar(raiz, archivo='_configtotal.ini')
    if errores:
        warn("_configtotal.ini tiene problemas — se verifican solo los archivos, "
             "no los objetos de la BD.")
    else:
        inventario = _inventario_bd(cfg['bd'])
        if inventario is None:
            warn("No se pudo conectar a la BD — se verifican solo los archivos.")
        else:
            sps_bd, vistas_bd = inventario

    resultado = verificar_integridad(salida, raiz, sps_bd, vistas_bd)
    if resultado is None:
        error("No hay manifiesto de integridad (.davgen-integridad.json).")
        info("Ejecutar primero `davgen generar` para crear la línea base.")
        return 1

    incidencias = imprimir_verificacion(resultado)
    return 0 if incidencias == 0 else 1


def cmd_comparar(ruta_backend_generado: str) -> int:
    """Comando `comparar`: muestra el diff unificado entre el código generado
    (copia en _backendGenerado/backend/ o /database/) y su ubicación final
    (servicio/, 02-Base*/). Útil para auditar qué editó el usuario antes de
    regenerar. Código de salida: 0 = sin diferencias, 1 = hay archivos editados."""
    raiz = os.path.dirname(os.path.dirname(ruta_backend_generado))
    incidencias = comparar_diferencias(ruta_backend_generado, raiz)
    return 0 if incidencias == 0 else 1


def _generar_docs(cfg, carpeta: str) -> str:
    from .nucleo.esquema import a_clase
    tablas = cfg['tablas']
    secciones = []
    for t in tablas:
        filas = '\n'.join(
            f"| `{c['COLUMN_NAME']}` | `{c['SQL_FULL']}` | "
            f"{'PK' if c['COLUMN_KEY'] == 'PRI' else ('FK → ' + c['FK'] if c['FK'] else '')} |"
            for c in t['columnas'])
        secciones.append(
            f"### `{t['tabla']}`\n\nVista `{t['vista']}` · SP `pcru{a_clase(t['tabla'])}` "
            f"· {t['origen']}\n\n| Columna | Tipo | Clave |\n|---|---|---|\n{filas}\n")
    def _fila_endpoint(t):
        mod, rec = gen_backend._modulo_recurso(t['tabla'])
        return (f"| `POST /api/{mod}/{gen_backend._recurso_uri(rec)}/` `listar` "
                f"`obtener` `guardar` `actualizar` `eliminar` | "
                f"`{mod.title()}{a_clase(rec)}Controller` |")
    endpoints = '\n'.join(_fila_endpoint(t) for t in tablas)
    contenido = f"""\
# {cfg['nombre']} — Guía del proyecto generado

> davgen v{VERSION} — {_ahora():%Y-%m-%d %H:%M} · entrada: {cfg['origen_entrada']}

> **Principio del proyecto:** el código generado NO se edita. Toda la
> administración y configuración (roles, permisos, menú, parámetros) se
> realiza **en la base de datos** (tablas `tbl_seg_*`) o desde el módulo
> Administración del portal. Al agregar tablas, regenerar y volver a
> ejecutar `01_seguridad.sql` y `03_procedimientos.sql` (idempotentes):
> los seeds nunca pisan lo ajustado en la BD.

## Configuración de acceso (administrar en la BD)

| Tabla | Qué se administra |
|---|---|
| `tbl_seg_rol` | Roles; `es_admin=1` da acceso total (ignora permisos) |
| `tbl_seg_modulo` | Módulos del menú: título, orden, visibilidad, activo |
| `tbl_seg_permiso` | Permisos rol × módulo × operación (`sel/get/add/upd/del`) |
| `tbl_seg_parametro` | Parámetros runtime: 2FA obligatorio, tamaño de archivos… |
| `tbl_seg_bitacora` | Auditoría de logins y escrituras (solo lectura) |

El middleware `VerificarPermiso` valida cada ruta CRUD contra
`tbl_seg_permiso`; el menú del frontend se carga de `POST /api/auth/menu`.

## Autenticación (2FA por correo o app)

| Endpoint | Auth | Descripción |
|---|---|---|
| `POST /api/auth/login` | pública | Paso 1 — sin 2FA devuelve token; con 2FA `{{requiere_2fa, metodo}}` |
| `POST /api/auth/verificar` | pública | Paso 2 — credenciales + código → token |
| `POST /api/auth/me` `logout` | token | Sesión |
| `POST /api/auth/menu` | token | Módulos y permisos del rol (desde la BD) |
| `POST /api/auth/2fa/activar` `confirmar` `desactivar` | token | Gestión 2FA |

Métodos: **app** (TOTP RFC 6238, `app/Utils/Totp.php`) y **correo**
(código 6 dígitos, vigencia `codigo_2fa_minutos`, requiere `MAIL_*` en `.env`).
Con el parámetro `2fa_obligatorio=1` todo login exige código por correo
aunque el usuario no haya enrolado un método.

## Administración (`/api/seguridad/*` — requiere permiso `administracion`)

| Endpoint | Descripción |
|---|---|
| `usuarios/sel` `add` `upd` `reset` | CRUD de usuarios, rol, activar/desactivar, reset de contraseña |
| `roles/sel` `add` `upd` | Roles (el nombre no se renombra) |
| `permisos/matriz` `guardar` | Matriz rol × módulo × operación |
| `parametros/sel` `upd` | Parámetros runtime |
| `bitacora/sel` | Auditoría (solo lectura) |

## Archivos por usuario

| Endpoint | Descripción |
|---|---|
| `POST /api/archivos/subir` | multipart `archivo` + `descripcion` — ext: {', '.join(cfg['extensiones_archivo'])} · máx {cfg['max_archivo_mb']}MB |
| `POST /api/archivos/sel` | listado paginado (cada usuario ve los suyos; admin todos) |
| `POST /api/archivos/descargar` | `{{pid}}` → descarga (valida dueño/admin) |
| `POST /api/archivos/del` | `{{pid}}` → borrado lógico |

Los archivos se guardan en `storage/app/archivos/{{usuario_id}}/`.

## Envelope de la API

Respuesta: `{{ "mensaje": "...", "info": {{ "item": [...], "pagination": {{...}} }} }}`
(v4 corrige el campo `mensaje`; las versiones anteriores usaban `mesaje`).
Error: `{{ "error": {{ "text": "..." }} }}` · paginación 15/100.

## Endpoints por tabla

| Endpoints | Controlador |
|---|---|
{endpoints}

## Tablas

{chr(10).join(secciones)}
"""
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, 'guia.md')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(contenido)
    return ruta


# ─────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────
_NO_ABRIR = False   # lo activa --si / --local


def _abrir_archivo(ruta: str) -> None:
    """Abre un archivo con la aplicación predeterminada del sistema. Solo en
    una sesión interactiva: nunca en CI, con tubería, con --si ni en pruebas
    (DAVGEN_NO_ABRIR=1 lo apaga del todo)."""
    if (_NO_ABRIR or os.environ.get('DAVGEN_NO_ABRIR')
            or not es_interactiva() or not sys.stdout.isatty()):
        return
    try:
        if sys.platform == 'win32':
            os.startfile(ruta)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', ruta])
        else:
            subprocess.Popen(['xdg-open', ruta])
    except Exception:
        pass


def _raiz_proyecto(desde: str) -> str:
    """Sube desde `desde` buscando _configtotal.ini o carpeta 03-Backend*.
    Devuelve la primera coincidencia o `desde` si no encuentra nada."""
    actual = os.path.abspath(desde)
    while True:
        if os.path.isfile(os.path.join(actual, '_configtotal.ini')):
            return actual
        try:
            if any(n.lower().startswith('03-backend')
                   and os.path.isdir(os.path.join(actual, n))
                   for n in os.listdir(actual)):
                return actual
        except OSError:
            pass
        padre = os.path.dirname(actual)
        if padre == actual:
            return desde
        actual = padre


def cmd_nuevo(carpeta: str) -> int:
    """Comando `nuevo`: crea la estructura inicial del proyecto en `carpeta`."""
    raiz = os.path.abspath(carpeta or os.getcwd())
    if any(n.lower().startswith('03-backend') for n in
           (os.listdir(raiz) if os.path.isdir(raiz) else [])):
        error(f"Ya hay un proyecto en {raiz} (existe 03-Backend*).")
        return 1
    os.makedirs(raiz, exist_ok=True)
    inicializar_proyecto(raiz)
    return 0


def cmd_actualizar(migrar_ini: bool) -> int:
    """Comando `actualizar`: pone al día los archivos de apoyo que davgen
    escribe en la raíz de un proyecto (guías, prompts, ejemplo del .ini) con la
    versión instalada. NO genera código, NO se conecta a la BD ni al FTP y NO
    toca los documentos que el usuario completa (requisitos, mockups, etc.).
    Es el primer paso para pasar un proyecto de davgen 4.x a 5."""
    import glob
    raiz = _raiz_proyecto(os.getcwd())
    ruta_cfg = os.path.join(raiz, '_configtotal.ini')
    if not os.path.isfile(ruta_cfg) and not buscar_carpetas_backend():
        error("No hay un proyecto davgen aquí (falta _configtotal.ini y 03-Backend*).")
        return 1
    titulo(f"ACTUALIZAR — archivos de apoyo del proyecto a davgen v{VERSION}")

    if os.path.isfile(ruta_cfg):
        if migrar_ini:
            cambios = configuracion.migrar_ini(raiz)
            for c in cambios:
                ok(f"_configtotal.ini: {c}")
            if not cambios:
                dim("· _configtotal.ini ya estaba al día")
        for aviso in configuracion.claves_con_defecto_distinto(raiz):
            warn(aviso)
    cfg, errores = (configuracion.cargar(raiz) if os.path.isfile(ruta_cfg)
                    else ({}, ['sin _configtotal.ini']))
    for aviso in cfg.get('avisos', []) if not errores or cfg else []:
        if migrar_ini and 'validar_acceso' in aviso:
            continue
        warn(aviso)
    if not migrar_ini and any('validar_acceso' in a for a in cfg.get('avisos', [])):
        info("`davgen actualizar --ini` quita esa clave por ti (no cambia "
             "ningún otro valor).")
    modulo = cfg.get('modulo', '') if cfg and not any(
        'modulo' in e for e in errores) else ''

    prompts = gen_prompts.generar_prompts(raiz, modulo)
    ok(f"{len(prompts)} prompt(s) de IA actualizados en _prompts/")
    gen_plantillas.generar_leeme_html(raiz)
    gen_plantillas.generar_leeme_md(raiz)
    gen_plantillas.generar_guia_google(raiz)
    ok("leeme.html, _davgen.leeme.md y CONFIGURAR-GOOGLE-AUTH.md actualizados")
    repuestas = gen_plantillas.generar_plantillas(raiz)
    if repuestas:
        ok(f"{len(repuestas)} plantilla(s) de documentos que faltaban, repuestas")
    if configuracion.escribir_ejemplo(raiz):
        ok("_configtotal.ejemplo.ini actualizado (copia sin secretos, para git)")

    # Restos de la v4 que ya no se usan: se informan, no se borran.
    restos = sorted(glob.glob(os.path.join(raiz, '_davgen4-*.exe'))
                    + glob.glob(os.path.join(raiz, '_davgen4-*.zip')))
    for r in restos:
        info(f"{os.path.basename(r)} ya no se usa con davgen 5 — se puede borrar")
    try:
        with open(os.path.join(raiz, '.gitignore'), encoding='utf-8-sig') as f:
            ignora_ini = any(linea.strip() == '_configtotal.ini' for linea in f)
    except OSError:
        ignora_ini = False
    if not ignora_ini and os.path.isfile(ruta_cfg):
        warn("_configtotal.ini (con contraseñas) NO está en .gitignore — si el "
             "repositorio se comparte, agregarlo y versionar "
             "_configtotal.ejemplo.ini (ver docs/migrar-desde-v4.md).")
    print()
    info("No se generó código ni se tocó la BD/FTP. Para regenerar el sistema: "
         "`davgen generar --local` (en seco) y luego `davgen generar`.")
    return 0


def _carpeta_02(raiz: str):
    """Carpeta `02-*` del proyecto (scripts de base de datos), o None."""
    try:
        return next((os.path.join(raiz, d) for d in sorted(os.listdir(raiz))
                     if d.lower().startswith(('02-', '02 '))
                     and os.path.isdir(os.path.join(raiz, d))), None)
    except OSError:
        return None


def cmd_seguridad(no_interactivo: bool) -> int:
    """Comando `seguridad`: crea en la BD de [bd] las tablas de seguridad
    (`tbl_seg_*`), sus vistas y los datos iniciales, ejecutando
    `02-*/00-seguridad.sql`. Es el paso que `generar` exige y que antes había
    que hacer a mano con un cliente de MySQL.

    · El script se REESCRIBE antes con los valores de _configtotal.ini (admin,
      contraseña inicial, Google, dueño), para que base y configuración digan
      lo mismo.
    · Si falta admin_password se pide por teclado (o se detiene): davgen no
      inventa ni trae ninguna contraseña.
    · Si la base ya tiene `tbl_seg_usuario` no se toca nada.
    · Muestra el destino y pide confirmación (salvo --si)."""
    raiz = _raiz_proyecto(os.getcwd())
    titulo("SEGURIDAD — crear tbl_seg_* en la base de datos")
    if not os.path.isfile(os.path.join(raiz, '_configtotal.ini')):
        error("No hay _configtotal.ini aquí — `davgen nuevo` crea un proyecto.")
        return 1
    cfg, errores = configuracion.cargar(raiz)
    if errores:
        error(f"_configtotal.ini tiene {len(errores)} problema(s):")
        for e in errores:
            print(f"    {C.RED}·{C.RESET} {e}")
        return 1
    if not _exigir_clave_admin(raiz, cfg, no_interactivo):
        return 1
    datos = cfg['bd']
    if not (datos.get('host') and datos.get('usuario') and datos.get('database')):
        error("Falta la sección [bd] en _configtotal.ini (host, usuario, database).")
        return 1
    for aviso in cfg['avisos']:
        warn(aviso)

    carpeta = _carpeta_02(raiz) or os.path.join(raiz, '02-Base-de-datos')
    os.makedirs(carpeta, exist_ok=True)
    import tempfile
    with tempfile.TemporaryDirectory(prefix='davgen_seg_') as tmp:
        generado = gen_sql.generar_seguridad(tmp, '', [], cfg)
        ruta_sql = os.path.join(carpeta, '00-seguridad.sql')
        shutil.copyfile(generado, ruta_sql)
    ok(f"{os.path.relpath(ruta_sql, raiz)} reescrito con los valores de "
       "_configtotal.ini")

    print(f"\n  {C.BOLD}Destino ({cfg['entorno'].upper()}):{C.RESET} BD «{datos['database']}» en "
          f"{datos['host']}:{datos['puerto']} (usuario {datos['usuario']})")
    print(f"  {C.DIM}Admin inicial: {cfg['admin_email']} · Google: "
          f"{'activo' if cfg['google_auth_activo'] else 'apagado'} · dueño: "
          f"{cfg['owner_email'] or '(ninguno)'}{C.RESET}\n")
    if not no_interactivo and not confirmar(
            "¿Crear las tablas de seguridad en esa base?"):
        warn("Cancelado. El script quedó listo para ejecutarlo a mano.")
        return 0

    rep = gen_sql.crear_seguridad(datos, ruta_sql)
    if rep.get('error') and 'total' not in rep:
        error(f"No se pudo conectar a la base: {rep['error']}")
        return 1
    if rep['ya_existia']:
        info(f"La base ya tiene {len(rep['tablas'])} tabla(s) tbl_seg_* — no se "
             "tocó nada. Para sumar seeds nuevos: `davgen generar` "
             "([generar] aplicar_sps = si).")
        return 0
    if rep['error']:
        error(f"Se detuvo tras {rep['ejecutadas']} de {rep['total']} "
              f"sentencia(s): {rep['error']}")
        info(f"Tablas creadas hasta ahí: {', '.join(rep['tablas']) or '(ninguna)'}")
        return 1
    ok(f"{rep['ejecutadas']} sentencia(s) ejecutadas — {len(rep['tablas'])} "
       f"tabla(s) de seguridad creadas: {', '.join(rep['tablas'])}")
    if configuracion.escribir_ejemplo(raiz):
        dim("· _configtotal.ejemplo.ini actualizado (copia sin secretos)")
    warn(f"Admin: {cfg['admin_email']}  ·  contraseña: la que escribiste en "
         f"{configuracion.archivo_de_secretos(raiz)} ([seguridad] admin_password). "
         "Cambiarla desde la aplicación al primer ingreso.")
    return 0


def cmd_comparar_remoto(ruta_backend_generado: str, detalle: bool = False) -> int:
    """`comparar --remoto`: baja UNA vez el backend publicado y lo compara en
    local contra lo que se desplegaría. Solo lee del servidor.
    Salida 0 = el servidor ya tiene exactamente lo local; 1 = hay diferencias
    o algo que no dejaría desplegar bien."""
    import difflib
    raiz = os.path.dirname(os.path.dirname(ruta_backend_generado))
    entorno = ''
    if configuracion.hay_entornos(raiz) and not os.environ.get('DAVGEN_ENTORNO'):
        entorno = 'produccion'      # el FTP vive en el entorno de producción
    cfg, errores = configuracion.cargar(raiz, entorno=entorno)
    titulo("COMPARAR CON EL SERVIDOR — backend publicado vs. local")
    if errores:
        error("_configtotal.ini con problemas: " + '; '.join(errores))
        return 1
    if not cfg['ftp_listo']:
        error(f"Falta [ftp] completo en {cfg['archivo_acceso'] or '_configtotal.ini'}.")
        return 1
    ftp = cfg['ftp']
    espejo = os.path.join(ruta_backend_generado, 'backend')
    if not os.path.isdir(espejo):
        error("Todavía no se generó nada: ejecutar `davgen generar --local` primero.")
        return 1
    carpeta_03 = os.path.dirname(ruta_backend_generado)
    laravel = next((os.path.join(carpeta_03, d) for d in ('servicio', 'backend')
                    if os.path.isfile(os.path.join(carpeta_03, d, 'artisan'))), '')
    destino = os.path.join(ruta_backend_generado, remoto.CARPETA)
    info(f"Bajando el PHP publicado de {ftp['host']}{ftp['ruta_remota']} "
         f"(entorno {cfg['entorno']}) — solo lectura…")
    rep_ = remoto.descargar_backend(ftp, destino)
    for e in rep_['errores'][:5]:
        warn(e)
    if rep_['errores'] and not rep_['descargados']:
        causa, hacer = diagnostico.explicar_error_ftp(Exception(rep_['errores'][0]), ftp)
        info(f"Qué hacer: {hacer}")
        return 1
    if not rep_['existe']:
        info("El servidor todavía no tiene el backend: el primer despliegue "
             "sube el sistema completo (no hay nada que comparar).")
    else:
        ok(f"{rep_['descargados']} archivo(s) bajados a "
           f"{os.path.relpath(destino, raiz)}")

    c = remoto.comparar(espejo, laravel, destino)
    print()
    ok(f"{len(c['iguales'])} archivo(s) iguales en el servidor y en local")
    for clave, texto_, pintar in (
            ('distintos', 'DISTINTOS — el despliegue los reemplazaría', warn),
            ('solo_local', 'solo en LOCAL — falta subirlos', info),
            ('solo_remoto', 'solo en el SERVIDOR — no los genera davgen ni están '
                            'en tu Laravel local (¿subidos a mano?)', warn)):
        if c[clave]:
            pintar(f"{len(c[clave])} {texto_}:")
            for rel in c[clave][:40]:
                dim(f"    {rel}")
            if len(c[clave]) > 40:
                dim(f"    … y {len(c[clave]) - 40} más")
    if detalle:
        for rel in c['distintos'][:10]:
            with open(os.path.join(destino, *rel.split('/')), encoding='utf-8',
                      errors='replace') as f:
                viejo = [x for x in f.read().splitlines() if '@generated' not in x]
            with open(c['origenes'][rel], encoding='utf-8', errors='replace') as f:
                nuevo = [x for x in f.read().splitlines() if '@generated' not in x]
            print(f"\n  {C.BOLD}{rel}{C.RESET}  {C.DIM}(− servidor · + local){C.RESET}")
            for linea in list(difflib.unified_diff(viejo, nuevo, lineterm='', n=1))[2:60]:
                color = C.GREEN if linea.startswith('+') else C.RED if linea.startswith('-') else C.DIM
                print(f"    {color}{linea}{C.RESET}")
    elif c['distintos']:
        dim("· `davgen comparar --remoto --detalle` muestra las diferencias línea a línea")

    fallas = []
    php = remoto.buscar_php()
    if php:
        fallas = remoto.validar_sintaxis(c['origenes'], php)
        if fallas:
            error(f"{len(fallas)} archivo(s) con error de sintaxis PHP — NO desplegar:")
            for f_ in fallas[:10]:
                dim(f"    {f_}")
        else:
            ok(f"Sintaxis PHP correcta en los {len(c['origenes'])} archivo(s) a desplegar")
    else:
        dim("· sin PHP en el PATH: no se validó la sintaxis (variable DAVGEN_PHP)")
    print()
    pendientes = len(c['distintos']) + len(c['solo_local'])
    if fallas:
        return 1
    if not pendientes and not c['solo_remoto']:
        ok("El servidor tiene exactamente lo mismo que local: nada que desplegar.")
        return 0
    info(f"{pendientes} archivo(s) cambiarían al desplegar. Publicar con: "
         "davgen generar --entorno produccion --produccion si")
    return 1


def _avisar_exposicion(cfg: dict) -> int:
    """Pide por web los archivos internos del backend publicado y avisa, bien
    fuerte, si alguno se puede bajar. Devuelve cuántos están expuestos."""
    url = diagnostico.url_backend(cfg['ftp'])
    if not url.lower().startswith('http'):
        dim("· sin [ftp] url: no se pudo comprobar si la carpeta publicada está protegida")
        return 0
    expuestos = diagnostico.probar_exposicion(url)
    if not expuestos:
        ok(f"Carpeta publicada protegida: desde afuera no se pueden bajar el .env, "
           f"los logs ni las dependencias ({url})")
        return 0
    error(f"LA CARPETA PUBLICADA ESTÁ EXPUESTA — cualquiera puede bajar de {url}:")
    for ruta, que in expuestos:
        print(f"    {C.RED}·{C.RESET} /{ruta}  →  {que}")
    info("Arreglarlo YA:  davgen proteger --entorno produccion")
    info("Y después cambiar la contraseña de la base de datos y de los "
         "administradores: hay que darlas por conocidas.")
    return len(expuestos)


def cmd_proteger(si: bool) -> int:
    """Comando `proteger`: pone la protección de la carpeta publicada en un
    despliegue que YA existe (los hechos con versiones anteriores no la traen).
    Sube solo archivos .htaccess; no toca el código ni el .env del servidor."""
    raiz = _raiz_proyecto(os.getcwd())
    entorno = ''
    if configuracion.hay_entornos(raiz) and not os.environ.get('DAVGEN_ENTORNO'):
        entorno = 'produccion'
    cfg, errores = configuracion.cargar(raiz, entorno=entorno)
    titulo("PROTEGER — la carpeta publicada del backend")
    if errores:
        error("Configuración con problemas: " + '; '.join(errores))
        return 1
    if not cfg['ftp_listo']:
        error(f"Falta [ftp] completo en {cfg['archivo_acceso'] or '_configtotal.ini'}.")
        return 1
    ftp = cfg['ftp']
    antes = _avisar_exposicion(cfg)
    print(f"\n  {C.BOLD}Se subirán archivos .htaccess de protección a:{C.RESET} "
          f"{ftp['host']}{ftp['ruta_remota']}  (entorno {cfg['entorno']})")
    dim("  · en la raíz se conserva lo que ya haya; solo se antepone el bloque de davgen")
    if not si and not confirmar("¿Aplicar la protección ahora?"):
        warn("Cancelado: no se subió nada.")
        return 1 if antes else 0
    rep_ = resumen_mod.proteger_remoto(ftp)
    if rep_['error']:
        causa, hacer = diagnostico.explicar_error_ftp(Exception(rep_['error']), ftp)
        error(f"No se pudo aplicar: {rep_['error']}")
        info(f"Qué hacer: {hacer}")
        return 1
    ok(f"Raíz: protección {rep_['raiz']} · carpetas internas cerradas: "
       f"{', '.join(rep_['carpetas']) or '(ninguna encontrada: ¿hay un despliegue ahí?)'}")
    despues = _avisar_exposicion(cfg)
    if antes and not despues:
        warn("Esos archivos estuvieron expuestos hasta ahora: cambiar la contraseña "
             "de la base de datos (y actualizar el .env del servidor) y las de los "
             "administradores del sistema.")
    return 1 if despues else 0


def cmd_entornos(actual: str, no_interactivo: bool) -> int:
    """Comando `entornos`: crea los dos archivos de acceso
    (_acceso.desarrollo.ini y _acceso.produccion.ini). Si _configtotal.ini
    todavía tiene los accesos adentro (proyecto anterior), los MUEVE al archivo
    del entorno al que pertenecen (`--actual`) y los quita de _configtotal.ini,
    que queda sin contraseñas."""
    raiz = _raiz_proyecto(os.getcwd())
    ruta_cfg = os.path.join(raiz, '_configtotal.ini')
    titulo("ENTORNOS — accesos de desarrollo y de producción por separado")
    if not os.path.isfile(ruta_cfg):
        error("No hay _configtotal.ini aquí — `davgen nuevo` crea un proyecto.")
        return 1
    ini = configuracion.nuevo_parser()
    ini.read(ruta_cfg, encoding='utf-8-sig')
    a_mover = [(s_, c_, ini.get(s_, c_).strip())
               for s_, claves in (('bd', ('host', 'puerto', 'usuario', 'password', 'database')),
                                  ('ftp', ('host', 'usuario', 'password', 'ruta_remota', 'url')),
                                  ('seguridad', ('admin_password',)))
               for c_ in claves if ini.has_option(s_, c_) and ini.get(s_, c_).strip()]
    con_datos = any(c_ in ('host', 'usuario', 'password', 'database', 'admin_password')
                    for _s, c_, _v in a_mover)
    if con_datos and actual not in configuracion.ENTORNOS:
        if no_interactivo or not es_interactiva():
            error("_configtotal.ini tiene accesos cargados: indicar a qué entorno "
                  "pertenecen con  --actual desarrollo  o  --actual produccion")
            return 1
        resp = input(f"  {C.YELLOW}Los accesos que hoy están en _configtotal.ini, "
                     f"¿son de (d)esarrollo o de (p)roducción?: {C.RESET}").strip().lower()
        actual = {'d': 'desarrollo', 'p': 'produccion'}.get(resp[:1], '')
        if not actual:
            warn("Cancelado: no se cambió nada.")
            return 0
    for creado in configuracion.crear_accesos(raiz):
        ok(f"{os.path.basename(creado)} creado")
    if con_datos:
        destino = configuracion.nombre_acceso(actual)
        for seccion, clave, valor in a_mover:
            configuracion.fijar_valor(raiz, seccion, clave, valor, archivo=destino)
            configuracion.fijar_valor(raiz, seccion, clave, '')
        ok(f"{len(a_mover)} valor(es) de acceso movidos de _configtotal.ini a "
           f"{destino} — _configtotal.ini quedó sin contraseñas")
        otro = [e for e in configuracion.ENTORNOS if e != actual][0]
        info(f"Falta completar {configuracion.nombre_acceso(otro)} con los accesos "
             f"de {otro}.")
    ruta_git = os.path.join(raiz, '.gitignore')
    try:
        with open(ruta_git, encoding='utf-8-sig') as f:
            actual_git = f.read()
    except OSError:
        actual_git = ''
    if '_acceso.*.ini' not in actual_git:
        with open(ruta_git, 'a', encoding='utf-8', newline='\n') as f:
            f.write(('' if actual_git.endswith('\n') or not actual_git else '\n')
                    + "\n# Accesos por entorno (contraseñas): no se versionan; sí sus ejemplos\n"
                      "_acceso.*.ini\n!_acceso.*.ejemplo.ini\n")
        ok(".gitignore: se ignoran los _acceso.*.ini (sus .ejemplo.ini se versionan)")
    if configuracion.escribir_ejemplo(raiz):
        ok("Copias sin contraseñas (.ejemplo.ini) actualizadas")
    print()
    info("Uso:  davgen generar                      → desarrollo (nunca publica)")
    info("      davgen generar --entorno produccion → base y FTP de producción")
    return 0


def _exigir_clave_admin(raiz: str, cfg: dict, no_interactivo: bool) -> bool:
    """La contraseña inicial del administrador la pone el usuario: davgen no
    trae ninguna ni la inventa. Si falta, se toma de DAVGEN_ADMIN_PASSWORD
    (CI; no se guarda) o se pide por teclado (se guarda en el archivo de
    accesos). False = no hay contraseña válida y hay que detenerse."""
    if cfg.get('admin_password'):
        return True
    donde = f"{configuracion.archivo_de_secretos(raiz)} → [seguridad] admin_password"
    reglas = (f"mínimo {configuracion.ADMIN_PASSWORD_MINIMO} caracteres, con letras "
              "y números")
    valor = os.environ.get('DAVGEN_ADMIN_PASSWORD', '').strip()
    del_teclado = False
    if not valor and not no_interactivo and es_interactiva():
        info("Falta la contraseña inicial del administrador del sistema "
             f"({cfg['admin_email']}). La eliges tú ({reglas}).")
        valor = _pedir_secreto('DAVGEN_ADMIN_PASSWORD',
                               'Contraseña del administrador', repetir=True)
        del_teclado = True
    if not valor:
        error("Falta la contraseña inicial del administrador: davgen no trae "
              "ninguna por defecto.")
        info(f"Escríbela en {donde}  ({reglas}) y vuelve a ejecutar.")
        return False
    problema = configuracion.problema_admin_password(valor, cfg['admin_email'])
    if problema:
        error(f"Esa contraseña no sirve: {problema}.")
        return False
    if del_teclado:
        configuracion.guardar_secreto(raiz, 'seguridad', 'admin_password', valor)
        ok(f"Contraseña del administrador guardada en {donde}")
    cfg['admin_password'] = valor
    return True


def _pedir_secreto(variable: str, pregunta: str, repetir: bool = False) -> str:
    """Un secreto desde una variable de entorno o, en una terminal, por teclado
    sin eco (dos veces si `repetir`). '' si no hay de dónde sacarlo."""
    valor = os.environ.get(variable, '').strip()
    if valor:
        return valor
    if not es_interactiva():
        return ''
    import getpass
    valor = getpass.getpass(f"  {pregunta} (no se muestra): ").strip()
    if repetir and valor and getpass.getpass("  Repetir: ").strip() != valor:
        error("No coinciden.")
        return ''
    return valor


def cmd_acceso(accion: str, entorno: str, si: bool, sin_llave: bool,
               con_llave: bool) -> int:
    """Comando `acceso`: accesos CIFRADOS dentro del proyecto.

    estado         qué entornos están en claro y cuáles cifrados
    cifrar         _acceso.<entorno>.ini → .cifrado (y borra el .ini)
    ver            muestra el contenido (pide el token)
    descifrar      vuelve al .ini en claro, para editarlo
    cambiar-token  token nuevo; se autoriza con el actual o con la llave maestra
    reiniciar      se perdió el token y no hay llave: empezar de cero ese entorno
    """
    raiz = _raiz_proyecto(os.getcwd())
    entornos = [entorno] if entorno else list(configuracion.ENTORNOS)

    def rutas(e):
        return (os.path.join(raiz, configuracion.nombre_acceso(e)),
                os.path.join(raiz, configuracion.nombre_cifrado(e)))

    titulo(f"ACCESOS CIFRADOS — {accion}")
    if accion == 'estado':
        for e in configuracion.ENTORNOS:
            claro, cifrado = rutas(e)
            if os.path.isfile(cifrado):
                with open(cifrado, encoding='utf-8') as f:
                    maestra = boveda.tiene_llave_maestra(f.read())
                ok(f"{e}: CIFRADO ({os.path.basename(cifrado)}) · "
                   + ("con llave maestra" if maestra else "SIN llave maestra"))
                if os.path.isfile(claro):
                    warn(f"{e}: además existe {os.path.basename(claro)} en claro, y es el "
                         "que se está usando — volver a cifrar o borrarlo")
            elif os.path.isfile(claro):
                warn(f"{e}: en claro ({os.path.basename(claro)}) — `davgen acceso cifrar`")
            else:
                dim(f"· {e}: sin archivo de accesos (`davgen entornos` lo crea)")
        return 0

    if accion == 'cifrar':
        pendientes = [e for e in entornos if os.path.isfile(rutas(e)[0])]
        if not pendientes:
            info("No hay archivos _acceso.*.ini en claro para cifrar.")
            return 0
        ya = [e for e in configuracion.ENTORNOS if os.path.isfile(rutas(e)[1])
              and e not in pendientes]
        token = _pedir_secreto(boveda.VARIABLE_TOKEN,
                               "Token del proyecto" + (" (el mismo de siempre)" if ya else
                                                       f" — mínimo {boveda.LARGO_MINIMO_TOKEN} caracteres"),
                               repetir=not ya)
        if not token:
            error(f"Falta el token: ejecutar en una terminal o definir {boveda.VARIABLE_TOKEN}.")
            return 1
        motivo = boveda.validar_token(token)
        if motivo:
            error(motivo[0].upper() + motivo[1:] + '.')
            return 1
        for e in ya:      # un token por proyecto: debe abrir lo ya cifrado
            boveda.leer_archivo(rutas(e)[1], raiz, token)
        llave, llave_nueva = '', False
        if not sin_llave:
            llave = os.environ.get(boveda.VARIABLE_MAESTRA, '').strip()
            if not llave:
                llave, llave_nueva = boveda.nueva_llave_maestra(), True
        for e in pendientes:
            claro, cifrado = rutas(e)
            with open(claro, encoding='utf-8-sig') as f:
                contenido = f.read()
            sellado = boveda.cifrar(contenido, e, token, llave)
            if boveda.descifrar(sellado, token) != contenido:        # nunca borrar a ciegas
                error(f"{e}: la verificación del cifrado falló — no se tocó nada.")
                return 1
            configuracion._escribir_un_ejemplo(
                claro, os.path.join(raiz, f'_acceso.{e}.ejemplo.ini'), contenido)
            with open(cifrado, 'w', encoding='utf-8', newline='\n') as f:
                f.write(sellado)
            os.remove(claro)
            ok(f"{e}: cifrado en {os.path.basename(cifrado)} — se borró "
               f"{os.path.basename(claro)}")
        boveda.recordar_token(raiz, token)
        if llave_nueva:
            print(f"\n  {C.BOLD}{C.YELLOW}LLAVE MAESTRA de recuperación — se muestra "
                  f"SOLO ESTA VEZ:{C.RESET}\n\n      {C.BOLD}{llave}{C.RESET}\n")
            info("Guárdala FUERA de esta PC (papel, gestor de contraseñas). Sirve "
                 "para poner un token nuevo si el actual se pierde:")
            info("  davgen acceso cambiar-token --con-llave-maestra")
            info("davgen no la guarda en ningún lado y no puede volver a mostrarla.")
        elif sin_llave:
            warn("Sin llave maestra: si se pierde el token, la única salida es "
                 "`davgen acceso reiniciar` y volver a cargar los accesos.")
        info("El .cifrado se puede versionar. Para editar un acceso: "
             "`davgen acceso descifrar`, editar el .ini y volver a cifrar.")
        return 0

    cifrados = [e for e in entornos if os.path.isfile(rutas(e)[1])]
    if not cifrados:
        info("No hay archivos de accesos cifrados" + (f" para {entorno}." if entorno else "."))
        return 0

    if accion == 'ver':
        for e in cifrados:
            contenido = boveda.leer_archivo(rutas(e)[1], raiz)
            print(f"\n  {C.BOLD}── {configuracion.nombre_cifrado(e)} ──{C.RESET}")
            for linea in contenido.splitlines():
                if linea.strip() and not linea.lstrip().startswith(';'):
                    print(f"  {linea}")
        return 0

    if accion == 'descifrar':
        token = boveda.token_de(raiz)
        for e in cifrados:
            claro, cifrado = rutas(e)
            contenido = boveda.leer_archivo(cifrado, raiz, token)
            with open(claro, 'w', encoding='utf-8', newline='\n') as f:
                f.write(contenido)
            os.remove(cifrado)
            ok(f"{e}: {os.path.basename(claro)} en claro (no se versiona). Al "
               "terminar de editar: `davgen acceso cifrar`.")
        warn("Al volver a cifrar se genera una llave maestra NUEVA (la anterior deja "
             f"de servir), salvo que se pase la misma en {boveda.VARIABLE_MAESTRA}.")
        return 0

    if accion == 'cambiar-token':
        actual = llave = ''
        if con_llave:
            llave = _pedir_secreto(boveda.VARIABLE_MAESTRA, "Llave maestra")
            if not llave:
                error(f"Falta la llave maestra (terminal o variable {boveda.VARIABLE_MAESTRA}).")
                return 1
        else:
            actual = boveda.token_de(raiz)
        nuevo = _pedir_secreto('DAVGEN_TOKEN_NUEVO', "Token NUEVO", repetir=True)
        if not nuevo:
            error("Falta el token nuevo (terminal o variable DAVGEN_TOKEN_NUEVO).")
            return 1
        nuevos = {}
        for e in cifrados:            # primero todo en memoria: o cambian todos o ninguno
            with open(rutas(e)[1], encoding='utf-8') as f:
                nuevos[e] = boveda.cambiar_token(f.read(), nuevo, actual, llave)
        for e, texto_ in nuevos.items():
            with open(rutas(e)[1], 'w', encoding='utf-8', newline='\n') as f:
                f.write(texto_)
            ok(f"{e}: token cambiado")
        boveda.olvidar()
        info("Los accesos no cambiaron; solo el token que los abre. Si alguien "
             "más usa el proyecto, hay que pasarle el token nuevo.")
        return 0

    # reiniciar: sin token y sin llave maestra
    warn("Reiniciar DESCARTA los accesos cifrados de: " + ', '.join(cifrados) + ".")
    info("Es la salida cuando se perdió el token y no hay llave maestra: después "
         "hay que volver a cargar los datos de la base y del FTP desde el panel "
         "del hosting.")
    if not si and not confirmar("¿Descartar esos accesos y empezar de cero?"):
        warn("Cancelado: no se cambió nada.")
        return 0
    for e in cifrados:
        claro, cifrado = rutas(e)
        apartado = f"{cifrado}.perdido-{_ahora():%Y%m%d-%H%M%S}"
        os.replace(cifrado, apartado)
        with open(claro, 'w', encoding='utf-8', newline='\n') as f:
            f.write(configuracion.nueva_plantilla_acceso(e))
        ok(f"{e}: {os.path.basename(claro)} vacío, listo para completar "
           f"(el anterior quedó en {os.path.basename(apartado)}, por si aparece el token)")
    boveda.olvidar()
    info("La contraseña del admin de ese archivo es nueva y solo vale para una "
         "base sin sembrar: la del sistema ya publicado no cambió.")
    info("Completar los accesos y luego: davgen acceso cifrar")
    return 0


def cmd_plantillas(accion: str, ruta: str, forzar: bool) -> int:
    """Comando `plantillas`: listar las plantillas del generador o copiar una
    al proyecto (`_plantillas/`) para personalizarla sin tocar davgen."""
    raiz = _raiz_proyecto(os.getcwd())
    if accion == 'listar':
        propias = set(plantillas.propias(raiz))
        grupo = None
        for r in plantillas.listar():
            g = r.split('/', 1)[0]
            if g != grupo:
                grupo = g
                print(f"\n  {C.BOLD}{g}/{C.RESET}")
            marca = f"{C.GREEN}● propia{C.RESET}" if r in propias else ''
            print(f"    {r}  {marca}")
        print()
        info(f"{len(plantillas.listar())} plantillas · {len(propias)} "
             f"personalizada(s) en {os.path.join(raiz, plantillas.CARPETA_PROYECTO)}")
        info("Personalizar una:  davgen plantillas copiar <grupo/archivo>")
        return 0
    # copiar
    if not ruta:
        error("Indicar la plantilla:  davgen plantillas copiar <grupo/archivo>")
        return 1
    ruta = ruta.replace('\\', '/')
    try:
        destino = plantillas.copiar_al_proyecto(ruta, raiz, sobrescribir=forzar)
    except FileNotFoundError:
        error(f"No existe la plantilla «{ruta}» — ver `davgen plantillas listar`.")
        return 1
    except FileExistsError as e:
        error(f"Ya existe {e} — usar --forzar para reemplazarla.")
        return 1
    ok(f"Plantilla copiada a {destino}")
    info("Editarla y volver a ejecutar `davgen generar`: la del proyecto gana "
         "sobre la del paquete.")
    return 0


def cmd_doctor(conexiones: bool = False) -> int:
    """Comando `doctor`: diagnóstico del entorno. No modifica nada."""
    import platform
    import re
    titulo("DIAGNÓSTICO DEL ENTORNO")
    faltan = 0
    ok(f"davgen v{VERSION} · Python {platform.python_version()} · {platform.system()}")

    def _version(cmd: str):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               timeout=30)
            m = re.search(r'(\d+\.\d+(?:\.\d+)?)', (r.stdout or '') + (r.stderr or ''))
            return m.group(1) if r.returncode == 0 and m else None
        except Exception:
            return None

    ctrl = _bd.controlador()
    if ctrl:
        ok(f"Controlador MySQL: {ctrl}")
    else:
        warn(_bd.MENSAJE_SIN_CONTROLADOR + "  (solo hace falta si se usa [bd])")
    try:
        import bcrypt  # noqa: F401
        ok("bcrypt disponible (hash real de la contraseña del administrador)")
    except ImportError:
        warn("bcrypt no instalado — el seed del admin llevaría un hash de "
             "relleno: pip install bcrypt")
        faltan += 1

    env, desc = _entorno_con_php_adecuado()
    if env is not None:
        ok(f"{desc} — suficiente para Laravel (>= 8.2)")
    else:
        warn(f"PHP >= 8.2 no encontrado ({desc}) — necesario para crear/ejecutar "
             "el proyecto Laravel")
        faltan += 1
    for nombre, cmd, para in (
            ('composer', 'composer --version', 'crear el proyecto Laravel'),
            ('node', 'node --version', 'compilar el frontend React'),
            ('npm', 'npm --version', 'crear/compilar el frontend React')):
        v = _version(cmd)
        if v:
            ok(f"{nombre} {v}")
        else:
            warn(f"{nombre} no encontrado — necesario para {para}")
            faltan += 1

    raiz = _raiz_proyecto(os.getcwd())
    if os.path.isfile(os.path.join(raiz, '_configtotal.ini')):
        cfg, errores = configuracion.cargar(raiz, archivo='_configtotal.ini')
        if errores:
            warn(f"_configtotal.ini tiene {len(errores)} problema(s):")
            for e in errores:
                dim(f"· {e}")
            faltan += 1
        else:
            ok(f"_configtotal.ini válido — «{cfg['nombre']}» · módulo {cfg['modulo']}")
            for aviso in cfg.get('avisos', []):
                warn(aviso)
            puntos = diagnostico.requisitos(cfg)
            if conexiones:
                # se abre la conexión, se mira y se cierra: no escribe nada
                info("Probando las conexiones (solo lectura)…")
                reales = [diagnostico.probar_bd(cfg['bd'])]
                if not (cfg['con_entornos'] and cfg['entorno'] != 'produccion'):
                    reales.append(diagnostico.probar_ftp(cfg['ftp']))
                    url_pub = diagnostico.url_backend(cfg['ftp'])
                    if url_pub.lower().startswith('http'):
                        abiertos = diagnostico.probar_exposicion(url_pub)
                        reales.append(
                            ('falta', 'Carpeta publicada',
                             'EXPUESTA: se pueden bajar ' + ', '.join('/' + r for r, _q in abiertos),
                             'davgen proteger --entorno produccion (y cambiar las contraseñas)')
                            if abiertos else
                            ('ok', 'Carpeta publicada', f'protegida ({url_pub})', ''))
                nombres = {r[1] for r in reales}
                puntos = [pt for pt in puntos if pt[1] not in nombres] + reales
            faltan += _mostrar_requisitos(cfg, puntos)
            if not conexiones:
                dim("· `davgen doctor --conexiones` prueba de verdad la base y el FTP")
            if not cfg['con_entornos']:
                dim("· accesos en un solo archivo: `davgen entornos` los separa en "
                    "desarrollo y producción")
            elif not cfg['acceso_cifrado']:
                dim("· accesos en claro: `davgen acceso cifrar` los guarda cifrados "
                    "con un token")
            propias = plantillas.propias(raiz)
            if propias:
                info(f"{len(propias)} plantilla(s) propia(s) en _plantillas/")
            for extra in plantillas.desconocidas(raiz):
                warn(f"_plantillas/{extra} no corresponde a ninguna plantilla "
                     "de davgen — se ignora (ver `davgen plantillas listar`)")
    else:
        dim("· No hay _configtotal.ini aquí — `davgen nuevo` crea un proyecto.")
    print()
    if faltan:
        info(f"{faltan} punto(s) a revisar. Sin ellos igual se puede generar "
             "código con `davgen generar --local`.")
    else:
        ok("Entorno completo.")
    return 0


def _arg_entorno(sp) -> None:
    sp.add_argument('--entorno', choices=list(configuracion.ENTORNOS), default='',
                    help='qué archivo de accesos usar: desarrollo (por defecto) '
                         'o produccion')


def main(argv=None) -> int:
    """Ejecuta un comando. Los problemas con los accesos cifrados (falta el
    token, token incorrecto) se informan como un mensaje y salida 1.

    Toda la corrida comparte UNA conexión a la base (`bd.una_sola_conexion`):
    el hosting compartido cuenta las conexiones nuevas por hora y el sitio
    publicado usa ese mismo cupo."""
    try:
        with _bd.una_sola_conexion():
            return _main(argv)
    except boveda.TokenIncorrecto:
        error("No se pudieron abrir los accesos cifrados: token (o llave) "
              "incorrecto, o archivo dañado.")
        info("Si se perdió el token:  davgen acceso cambiar-token --con-llave-maestra"
             "   ·   sin llave maestra:  davgen acceso reiniciar")
        return 1
    except boveda.ErrorBoveda as e:
        error(str(e))
        return 1


def _main(argv=None) -> int:
    global _NO_ABRIR
    asegurar_utf8()
    p = argparse.ArgumentParser(
        prog='davgen',
        description=f'davgen v{VERSION} — genera un sistema Laravel + React + '
                    'MySQL a partir de _configtotal.ini')
    p.add_argument('--version', action='version', version=f'davgen v{VERSION}')
    sub = p.add_subparsers(dest='comando')

    sp = sub.add_parser('nuevo', help='crear la estructura de un proyecto nuevo '
                                      '(carpetas 00..05 + _configtotal.ini)')
    sp.add_argument('carpeta', nargs='?', default='',
                    help='carpeta del proyecto (por defecto: la actual)')

    for nombre, ayuda in (
            ('generar', 'validar _configtotal.ini y generar todo en '
                        '03-Backend/_backendGenerado'),
            ('sincronizar', 'regenerar y desplegar SOLO si la BD cambió '
                            'desde la última generación (snapshot)')):
        sp = sub.add_parser(nombre, help=ayuda)
        sp.add_argument('--listar', action='store_true', help='solo análisis')
        sp.add_argument('--si', action='store_true', help='no interactivo')
        sp.add_argument('--local', action='store_true',
                        help='solo generar archivos: no escribe en la BD, no usa '
                             'FTP y no crea Laravel/React con composer/npm '
                             '(implica --si). Para pruebas y CI.')
        sp.add_argument('--produccion', choices=['si', 'no', 'preguntar'],
                        default='preguntar', help='subir el backend a la nube (FTP)')
        sp.add_argument('--front', choices=['si', 'no', 'preguntar'],
                        default='preguntar', help='desplegar el frontend React a la nube')
        _arg_entorno(sp)

    sp = sub.add_parser('verificar',
                        help='comprobar si el código generado (controllers, api.php, '
                             'SPs, frontend) fue modificado a mano')
    _arg_entorno(sp)
    sp = sub.add_parser('comparar',
                        help='mostrar el diff entre el código generado y los archivos '
                             'en su ubicación final; con --remoto, contra lo publicado')
    sp.add_argument('--remoto', action='store_true',
                    help='bajar por FTP el backend publicado (solo lectura) y '
                         'compararlo en local con lo que se desplegaría')
    sp.add_argument('--detalle', action='store_true',
                    help='con --remoto: mostrar las diferencias línea a línea')
    _arg_entorno(sp)
    sp = sub.add_parser('acceso',
                        help='accesos cifrados: cifrar, ver, descifrar, cambiar el '
                             'token o reiniciar')
    sp.add_argument('accion', nargs='?', default='estado',
                    choices=['estado', 'cifrar', 'ver', 'descifrar', 'cambiar-token',
                             'reiniciar'])
    sp.add_argument('--entorno', choices=list(configuracion.ENTORNOS), default='',
                    help='solo ese entorno (por defecto: los dos)')
    sp.add_argument('--sin-llave-maestra', action='store_true',
                    help='al cifrar, no crear llave de recuperación')
    sp.add_argument('--con-llave-maestra', action='store_true',
                    help='en cambiar-token: autorizar con la llave maestra (token perdido)')
    sp.add_argument('--si', action='store_true', help='no pedir confirmación')
    sp = sub.add_parser('proteger',
                        help='cerrar la carpeta publicada del backend (.env, logs, '
                             'dependencias) en un despliegue que ya existe')
    sp.add_argument('--si', action='store_true', help='no pedir confirmación')
    _arg_entorno(sp)
    sp = sub.add_parser('entornos',
                        help='separar los accesos en _acceso.desarrollo.ini y '
                             '_acceso.produccion.ini')
    sp.add_argument('--actual', choices=list(configuracion.ENTORNOS), default='',
                    help='a qué entorno pertenecen los accesos que hoy están en '
                         '_configtotal.ini (se mueven a ese archivo)')
    sp.add_argument('--si', action='store_true', help='no preguntar')
    sp = sub.add_parser('plantillas',
                        help='listar las plantillas o copiar una al proyecto '
                             'para personalizarla')
    sp.add_argument('accion', choices=['listar', 'copiar'], nargs='?',
                    default='listar')
    sp.add_argument('ruta', nargs='?', default='', help='ej: frontend/pagina.jsx')
    sp.add_argument('--forzar', action='store_true',
                    help='reemplazar la copia del proyecto si ya existe')
    sp = sub.add_parser('doctor', help='diagnosticar el entorno y los requisitos '
                                       'del proyecto (PHP, composer, node, accesos)')
    sp.add_argument('--conexiones', action='store_true',
                    help='probar de verdad la base de datos y el FTP (solo lectura)')
    _arg_entorno(sp)
    sp = sub.add_parser('seguridad',
                        help='crear en la BD las tablas de seguridad tbl_seg_* '
                             '(ejecuta 00-seguridad.sql; no toca una base ya sembrada)')
    sp.add_argument('--si', action='store_true', help='no pedir confirmación')
    _arg_entorno(sp)
    sp = sub.add_parser('actualizar',
                        help='poner al día las guías y prompts del proyecto con '
                             'esta versión (no genera código ni toca BD/FTP)')
    sp.add_argument('--ini', action='store_true',
                    help='además limpiar _configtotal.ini de claves de davgen '
                         '4.x que ya no existen (no cambia ningún otro valor)')

    args = p.parse_args(argv)
    if args.comando is None:
        # Sin argumentos (ej: doble clic en el ejecutable) → 'generar'
        args = p.parse_args(['generar'])

    if args.comando == 'acceso':
        return cmd_acceso(args.accion, args.entorno, args.si,
                          args.sin_llave_maestra, args.con_llave_maestra)
    if getattr(args, 'entorno', ''):
        os.environ['DAVGEN_ENTORNO'] = args.entorno
    if args.comando == 'doctor':
        return cmd_doctor(args.conexiones)
    if args.comando == 'entornos':
        return cmd_entornos(args.actual, args.si)
    if args.comando == 'proteger':
        if not args.si and not es_interactiva():
            error("`davgen proteger` sube archivos al servidor: sin una terminal "
                  "interactiva hay que confirmarlo con --si.")
            return 1
        return cmd_proteger(args.si)
    if args.comando == 'plantillas':
        return cmd_plantillas(args.accion, args.ruta, args.forzar)

    banner(f'davgen v{VERSION} — _configtotal.ini → _backendGenerado')

    if args.comando == 'nuevo':
        return cmd_nuevo(args.carpeta)
    if args.comando == 'seguridad':
        if not args.si and not es_interactiva():
            error("`davgen seguridad` escribe en la base de datos: sin una "
                  "terminal interactiva hay que confirmarlo con --si.")
            return 1
        return cmd_seguridad(args.si)
    if args.comando == 'actualizar':
        _NO_ABRIR = True
        return cmd_actualizar(args.ini)

    local = bool(getattr(args, 'local', False))
    no_interactivo = bool(getattr(args, 'si', False)) or local
    _NO_ABRIR = no_interactivo

    # Sin proyecto en esta carpeta: se ofrece crearlo (nunca en silencio).
    if not buscar_carpetas_backend():
        if args.comando not in ('generar', 'sincronizar'):
            error("No hay un proyecto davgen aquí (falta la carpeta 03-Backend*).")
            return 1
        if no_interactivo or not es_interactiva():
            error("No hay un proyecto davgen aquí (falta la carpeta 03-Backend*).")
            info("Crear uno con:  davgen nuevo [carpeta]")
            return 1
        if not confirmar(f"No hay un proyecto aquí. ¿Crear la estructura "
                         f"inicial en {os.getcwd()}?"):
            return 0
        inicializar_proyecto(os.getcwd())
        return 0

    # Plantillas propias del proyecto ({raíz}/_plantillas) — ganan sobre las
    # del paquete. Se activan antes de generar nada.
    raiz = _raiz_proyecto(os.getcwd())
    propias = plantillas.usar_proyecto(raiz)
    if propias:
        info(f"{len(propias)} plantilla(s) propia(s) del proyecto en uso "
             f"(_plantillas/): {', '.join(propias[:5])}"
             + (' …' if len(propias) > 5 else ''))
    for extra in plantillas.desconocidas(raiz):
        warn(f"_plantillas/{extra} no corresponde a ninguna plantilla de davgen "
             "— se ignora (ver `davgen plantillas listar`)")

    # `verificar` y `comparar` no tocan el entorno: solo leen _backendGenerado.
    if args.comando in ('verificar', 'comparar'):
        ruta_backend_generado = _localizar_backend_generado()
        if not ruta_backend_generado:
            error("No se encontró 03-Backend/_backendGenerado — "
                  "ejecutar `davgen generar` primero.")
            return 1
        if args.comando == 'verificar':
            return cmd_verificar(ruta_backend_generado)
        if args.remoto:
            return cmd_comparar_remoto(ruta_backend_generado, args.detalle)
        return cmd_comparar(ruta_backend_generado)

    # La contraseña del administrador se exige ANTES de preparar el entorno:
    # sin ella no tiene sentido descargar Laravel con composer (minutos y red).
    if not args.listar:
        cfg_previa, errores_previos = configuracion.cargar(raiz, archivo='_configtotal.ini')
        if not errores_previos and not _exigir_clave_admin(raiz, cfg_previa, no_interactivo):
            return 1

    # Paso previo: validar entorno (03-Backend, Laravel, BD).
    # Devuelve la ruta de 03-Backend/_backendGenerado, donde se genera TODO.
    ruta_backend_generado = validar_entorno_backend(
        no_interactivo=no_interactivo, solo_listar=bool(args.listar), local=local)
    if not ruta_backend_generado:
        return 1
    return cmd_generar(args.listar, no_interactivo, args.produccion,
                       ruta_backend_generado, args.front,
                       solo_si_cambio=(args.comando == 'sincronizar'),
                       local=local)


def _pausar_si_doble_clic() -> None:
    """Como ejecutable sin argumentos (doble clic) la consola se cierra al
    terminar: esperar Enter para que el usuario pueda leer el resultado."""
    if getattr(sys, 'frozen', False) and len(sys.argv) == 1:
        try:
            input("\n  Presione Enter para salir... ")
        except EOFError:
            pass


def ejecutar() -> None:
    """Punto de entrada del comando `davgen` (ver pyproject.toml)."""
    codigo = 0
    try:
        codigo = main()
    except KeyboardInterrupt:
        print()
        warn("Interrumpido por el usuario.")
        codigo = 130
    except _bd.SinControlador as _exc:
        error(str(_exc))
        codigo = 1
    except Exception as _exc:
        import traceback
        error(f"Error inesperado: {_exc}")
        if os.environ.get('DAVGEN_DEBUG'):
            traceback.print_exc()
        else:
            info("Detalle completo: repetir con la variable DAVGEN_DEBUG=1")
        codigo = 1
    _pausar_si_doble_clic()
    sys.exit(codigo)


if __name__ == '__main__':
    ejecutar()
