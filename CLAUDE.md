# CLAUDE.md — davgen 5

> Versión: `src/davgen/nucleo/version.py` (única fuente). Cambios: `CHANGELOG.md`.
> Este repositorio está pensado para hacerse **público**: todo lo que se escriba
> aquí —código, plantillas, pruebas, documentos, este archivo— debe poder leerlo
> cualquiera.

## Qué es

`davgen` es un generador en Python: a partir de `_configtotal.ini` y una
entrada (BD MySQL existente o mockup HTML) genera SQL, backend Laravel,
frontend React y pruebas, y puede desplegar por FTP a hosting compartido.
La v5 es la v4.36 reorganizada para publicarse: paquete instalable, plantillas
como datos, pruebas, y sin nada propio del autor adentro.

Mapa del código y de la arquitectura generada: `docs/arquitectura.md`.

## Cómo trabajar aquí

```powershell
.\scripts\probar.ps1              # venv en .tmp\ + ruff + pytest (sin BD/FTP/composer/node)
.\scripts\probar.ps1 -Paquete     # además construye el wheel y lo prueba instalado
python scripts\generar_ejemplo.py .tmp\x --extras   # proyecto de ejemplo generado
```

- `davgen` se puede ejecutar directo desde la terminal de Claude: **no pide
  contraseña ni bloquea el equipo** (eso era el `.exe` de la v4; las reglas de
  «usar siempre tubería» no aplican a la v5).
- Para probar un cambio de generación: generar el ejemplo antes y después y
  hacer `diff -r`. Con `SOURCE_DATE_EPOCH` fijo la salida es reproducible; lo
  único que varía es el hash bcrypt del admin (sal aleatoria).
- PHP del PATH en este equipo es 8.1; para `php -l` usar el 8.3
  (`DAVGEN_PHP`, `probar.ps1` lo busca solo).

## Entornos (lo que más cambia el día a día)

- Accesos en `_acceso.desarrollo.ini` / `_acceso.produccion.ini`; el del
  entorno elegido se superpone a `_configtotal.ini` (`configuracion.leer_ini`).
  Entorno por defecto: desarrollo. `--entorno` o `DAVGEN_ENTORNO` lo cambian.
- En desarrollo `generar` nunca publica. Para tocar producción hay que pedirlo
  con `--entorno produccion`: tratarlo como una acción que requiere
  confirmación del usuario.
- Accesos cifrados: `nucleo/boveda.py` (`_acceso.<entorno>.cifrado`). El token
  llega por `DAVGEN_TOKEN` o por teclado; nunca escribirlo en un archivo, un
  comando ni un mensaje. Para guardar un secreto usar
  `configuracion.guardar_secreto`, que sabe escribir en un archivo cifrado.
  Sin token, `cargar`/`leer_ini` lanzan `boveda.FaltaToken`.
- La carpeta publicada va protegida por `.htaccess` (`resumen.HTACCESS_PROTECCION`,
  `proteger_remoto`, `diagnostico.probar_exposicion`). Cualquier cambio en el
  empaquetado del despliegue debe mantener en verde `tests/test_seguridad_despliegue.py`.
- Diagnóstico: `nucleo/diagnostico.py`; comparación con lo publicado:
  `nucleo/remoto.py` (solo lectura sobre el FTP).

## Reglas inquebrantables

1. **Nada del autor ni de clientes en el repo**: ni correos, dominios, IPs,
   usuarios de hosting, Client IDs, contraseñas, nombres de proyectos de
   clientes. Tampoco en comentarios ni en este archivo. `tests/test_publicacion.py`
   lo vigila. Las referencias a proyectos reales van como «un proyecto en
   producción».
2. **Sin binarios en git** (`.exe`, `.zip`): van a GitHub Releases.
3. **Toda corrección trae su prueba** (que falle sin el arreglo).
4. **Nada sale del proyecto del usuario sin pedirlo**: lo que escribe en BD/FTP
   o instala algo respeta `--local` y se confirma mostrando el destino.
5. **Nunca borrar lo que davgen no generó.** Generado = lleva la cabecera
   `@generated davgen`.
6. **Valores por defecto neutros** (ver `nucleo/configuracion.py`).
7. **Plantillas = archivos** en `src/davgen/plantillas/` (LF). No incrustar
   PHP/JSX/SQL largos en Python. Marcadores `__X__` o `{x}` según la plantilla
   (`docs/plantillas.md`).
8. **BD solo vía `nucleo/bd.py`; fecha solo vía `nucleo/reloj.py`.**
9. **Semver**: cambiar rutas de la API, firma de un SP o nombre/ubicación de un
   archivo generado es MAYOR. Todo cambio visible va a `CHANGELOG.md`.
10. El código generado NO se edita a mano; el generador NO crea tablas de
    negocio en la BD (solo `tbl_seg_*` vía script y los `pcru*`); la
    administración del sistema generado vive en `tbl_seg_*`.
11. Consola y código generado en español.

## Trampas conocidas

- **Scripts largos en línea en el Bash de Claude** (heredocs con comillas
  mezcladas) fallan con «unexpected EOF»: escribir el script a un archivo y
  ejecutarlo.
- **`/tmp` de Git Bash ≠ `/tmp` de Python en Windows**: pasar rutas de Windows.
- **Plantillas con `{campo}`** (`str.format`): una llave literal va doble.
  Las de `__TOKEN__` no.
- **`plantillas.usar_proyecto()` recarga módulos** generadores cuando un
  proyecto trae plantillas propias; las pruebas lo restablecen con un fixture
  `autouse`. Un módulo nuevo que cargue plantillas debe hacerlo con
  `_plantilla(ruta, __name__, 'CONSTANTE')` para quedar registrado.
- **PowerShell 5.1**: `$ErrorActionPreference = 'Continue'` en los scripts que
  llaman a pip/pyinstaller (escriben en stderr sin fallar); `Set-Content` mete
  BOM → leer `.ini`/`.env` con `utf-8-sig`.
- **PyInstaller** necesita `--add-data` de `plantillas/` (lo hace
  `scripts/compilar-exe.ps1`).
- **API generada**: requiere `Accept: application/json`; parámetros con prefijo
  `p`; `actualizar` sobrescribe todas las columnas; el orden de parámetros del
  SP es el de las columnas.
- **`.env` de Laravel**: sesión/caché en `file` y cola `sync` (el hosting
  compartido y un proyecto recién creado no tienen esas tablas).

## Qué NO está probado automáticamente

La subida por FTP en sí, la creación de proyectos con `composer`/`npm`,
`leer_bd` contra un MySQL real y `scripts/empaquetar-plantillas.ps1`. Tocar esas
zonas exige una prueba manual y decirlo en el PR. Lista de pendientes:
`CHANGELOG.md` → «Pendiente».

## Relación con la v4

El repositorio de la v4 es privado y **no se publica**. No copiar de ahí archivos de
configuración, bitácoras ni documentos sin revisarlos contra la regla 1.
Migrar un proyecto generado con 4.x: `docs/migrar-desde-v4.md`.
