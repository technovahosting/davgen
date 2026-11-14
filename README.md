# davgen

**De una base de datos MySQL —o de un mockup HTML— a un sistema completo:**
scripts SQL, API en Laravel, aplicación React y pruebas. Y, si quieres,
desplegado en un hosting compartido por FTP.

```text
_configtotal.ini ──┐
                   ├──►  davgen generar  ──►  SQL (tablas, vistas, SPs)
BD o mockup HTML ──┘                          Laravel (auth + 2FA + permisos + CRUD)
                                              React  (login + páginas CRUD)
                                              Pruebas (PHPUnit, Postman, api.http)
                                              Despliegue por FTP (opcional)
```

El código generado es **tuyo**: no queda ninguna dependencia de davgen en el
sistema. Lo que es propio de tu negocio se escribe aparte (extendiendo, nunca
editando lo generado), y así regenerar es seguro.

> davgen es un proyecto independiente. No está afiliado a Laravel, React,
> Google ni MySQL — ver [AVISOS-TERCEROS.md](AVISOS-TERCEROS.md). Se entrega sin
> garantía: quien genera y opera el sistema responde por él y por sus datos —
> ver [DESCARGO.md](DESCARGO.md).

## La forma más fácil: pedírselo a Claude

Si usas [Claude Code](https://claude.com/claude-code), instala la skill y
describe el sistema con tus palabras; Claude se encarga de davgen:

```text
/plugin marketplace add technovahosting/davgen
/plugin install davgen@davgen
```

> Quiero un sistema para la biblioteca de mi colegio: libros, socios y préstamos.

Guía paso a paso, pensada para quien recién empieza: [docs/skill.md](docs/skill.md).

## Instalación

Requiere **Python 3.10 o superior**.

```bash
pip install davgen          # o: pipx install davgen
davgen doctor               # dice qué falta en el equipo
```

Desde el código fuente (o mientras la versión no esté en PyPI):

```bash
git clone https://github.com/technovahosting/davgen.git && cd davgen
pip install .
```

Para *crear y ejecutar* el sistema generado hacen falta PHP 8.2+, Composer y
Node.js. Para *generar el código* no hace falta ninguno (`--local`).

## Primer proyecto en 5 minutos (sin base de datos)

```bash
davgen nuevo mi-sistema
cd mi-sistema
```

1. Copia tu mockup a `01-Mockups/index.html` (hay uno de ejemplo en
   [`ejemplos/biblioteca`](ejemplos/biblioteca/index.html)).
2. En `_configtotal.ini` completa `[proyecto] nombre`, `modulo` y
   `[entrada] mockup = 01-Mockups/index.html`.
3. En `_acceso.desarrollo.ini` escribe tu contraseña de administrador
   (`[seguridad] admin_password`, mínimo 8 caracteres con letras y números).
4. Genera:

```bash
davgen generar --local
```

Todo queda en `03-Backend/_backendGenerado/`: los `.sql`, el backend, el
frontend, las pruebas y un `RESUMEN.md`. `--local` no se conecta a ninguna base
de datos, no usa FTP y no instala nada.

## Qué necesitas tener

- El **mockup** del sistema en HTML (o las tablas ya creadas en la base).
- Acceso a una **base de datos** MySQL o MariaDB para desarrollar.
- Para publicar: la base y el **FTP** de tu hosting.
- PHP 8.2+, Composer y Node.js (`davgen doctor` dice qué falta).

Al ejecutar, davgen muestra esta lista con el estado de cada punto y qué hacer
con lo que falte. La aplicación que genera es **web y adaptable** (celular,
tablet y PC), con tema claro, oscuro o el del sistema operativo.

## Dos entornos: desarrollo y producción

Los usuarios y contraseñas no van en `_configtotal.ini` sino en dos archivos,
uno por entorno, que no se versionan:

| Archivo | Qué lleva | Cuándo se usa |
|---|---|---|
| `_acceso.desarrollo.ini` | La base donde desarrollas y pruebas | Siempre, salvo que pidas otro |
| `_acceso.produccion.ini` | La base y el FTP del sitio publicado | Con `--entorno produccion` |

```bash
davgen generar                        # desarrollo: nunca publica nada
davgen generar --entorno produccion   # aplica en la base de producción y publica por FTP
```

En desarrollo no se sube nada por FTP, diga lo que diga la configuración:
publicar es siempre una decisión explícita.

### Accesos cifrados (opcional)

```bash
davgen acceso cifrar
```

Guarda los dos archivos de accesos cifrados con un **token** tuyo (uno por
proyecto) y borra los `.ini` en claro; davgen pide el token al ejecutar. Entrega
además una **llave maestra** para poner un token nuevo si el actual se pierde.
Sin token ni llave, la salida es `davgen acceso reiniciar` y volver a cargar los
accesos. Detalle y límites: [docs/accesos-cifrados.md](docs/accesos-cifrados.md).

## Flujo completo

```bash
davgen generar
```

Con `[bd]` configurada, davgen además crea el proyecto Laravel y el React (con
`composer` y `npm`), copia ahí el código, aplica en la base los procedimientos
almacenados y —solo si lo activas— despliega por FTP. Antes de tocar la base o
el hosting muestra **a dónde** va a escribir y pide confirmación.

| Comando | Qué hace |
|---|---|
| `davgen nuevo [carpeta]` | Crea la estructura de un proyecto |
| `davgen generar` | Genera todo (interactivo) |
| `davgen generar --si` | Sin preguntas: usa lo que diga el `.ini` (CI, tareas programadas) |
| `davgen generar --local` | Solo archivos: sin BD, sin FTP, sin instalar nada |
| `davgen generar --listar` | Solo analiza la entrada y lista las tablas |
| `davgen sincronizar --si` | Regenera únicamente si el esquema de la BD cambió |
| `davgen verificar` | ¿Alguien editó a mano el código generado? (salida 0/1, para CI) |
| `davgen comparar` | Muestra ese diff |
| `davgen comparar --remoto` | Baja el backend publicado (solo lectura) y lo compara en local con lo que se desplegaría |
| `davgen proteger` | Cierra la carpeta publicada (`.env`, logs, dependencias) en un sitio ya desplegado |
| `davgen entornos` | Separa los accesos en desarrollo y producción |
| `davgen acceso [cifrar\|ver\|descifrar\|cambiar-token\|reiniciar]` | Accesos cifrados con un token por proyecto |
| `davgen plantillas [listar\|copiar X]` | Personalizar lo que se genera |
| `davgen seguridad` | Crea en la base las tablas de seguridad `tbl_seg_*` (pide confirmación; no toca una base ya sembrada) |
| `davgen doctor [--conexiones]` | Requisitos y diagnóstico; con `--conexiones` prueba la base y el FTP y explica por qué fallan |
| `davgen actualizar [--ini]` | Pone al día las guías de un proyecto (p. ej. al venir de davgen 4); no genera ni toca BD/FTP |

## Qué genera

- **Base de datos** — `tbl_seg_*` (usuarios, roles, permisos, menú, parámetros,
  bitácora), tablas y vistas de negocio, y un procedimiento `pcru<Tabla>` por
  tabla (alta, lectura, cambio y baja lógica).
- **Backend Laravel** — login con token (Sanctum), segundo factor por correo o
  app (TOTP), permisos por rol × módulo × operación administrados **en la base
  de datos**, límites de tasa, carga de archivos y un controller + service por
  tabla. Opcionales: FormRequests, pruebas PHPUnit, exportación CSV, OpenAPI.
- **Frontend React** — cliente de la API, login, menú por permisos y una página
  CRUD por tabla.
- **Pruebas** — colección Postman, `api.http`, script de humo en PowerShell.
- **Inicio de sesión con Google** — opcional y **apagado por defecto**; se
  activa con un Client ID propio.

## Personalizar sin tocar davgen

Cada archivo que davgen genera sale de una **plantilla**. Para cambiar una:

```bash
davgen plantillas listar
davgen plantillas copiar frontend/pagina.jsx     # → _plantillas/frontend/pagina.jsx
# editarla y volver a generar: la del proyecto gana sobre la del paquete
```

Más en [docs/plantillas.md](docs/plantillas.md). Dónde poner el código propio
del negocio: [docs/arquitectura.md](docs/arquitectura.md#código-propio).

## Seguridad: lo que conviene saber

- Las contraseñas (BD, FTP, admin inicial) viven en `_acceso.<entorno>.ini`,
  que el `.gitignore` del proyecto excluye; para git están sus
  `.ejemplo.ini`, que davgen escribe sin los secretos. `_configtotal.ini` no
  lleva contraseñas y se versiona.
- davgen **no trae ninguna contraseña de administrador**: la escribes tú en
  `_acceso.<entorno>.ini` (o la pide por teclado) y exige un mínimo de
  fortaleza. Cámbiala desde la aplicación al primer ingreso.
- davgen no trae cuentas, correos ni identificadores de nadie, y no envía datos
  a ningún servicio. Solo se conecta a la base y al FTP que tú configures.
- El despliegue protege la carpeta publicada (nadie puede bajar el `.env`, los
  logs ni los archivos de los usuarios) y lo comprueba desde afuera al terminar.
  **Los sitios publicados con versiones anteriores no tienen esa protección:**
  `davgen proteger --entorno produccion`. Ver [docs/seguridad.md](docs/seguridad.md).
- Para reportar una vulnerabilidad: [SECURITY.md](SECURITY.md).

## Desarrollo y pruebas

```powershell
.\scripts\probar.ps1            # Windows
```
```bash
scripts/probar.sh               # Linux / macOS
```

Crea un entorno virtual en `.tmp/`, pasa el linter y corre las pruebas. No
necesita MySQL, FTP, Composer ni Node: las pruebas generan el proyecto de
ejemplo en carpetas temporales con `--local`. Detalle en
[CONTRIBUTING.md](CONTRIBUTING.md).

## Documentación

- [docs/skill.md](docs/skill.md) — usar davgen conversando con Claude:
  instalar la skill y crear el primer sistema.
- [docs/arquitectura.md](docs/arquitectura.md) — cómo está hecho el generador y
  la arquitectura del sistema generado.
- [docs/plantillas.md](docs/plantillas.md) — personalizar las plantillas.
- [docs/solucion-de-problemas.md](docs/solucion-de-problemas.md) — no conecta
  MySQL, no despliega al FTP, no aparece el botón de Google.
- [docs/seguridad.md](docs/seguridad.md) — pruebas de ataque hechas al sistema
  generado, qué se corrigió y qué queda a cargo de cada proyecto.
- [docs/accesos-cifrados.md](docs/accesos-cifrados.md) — guardar los accesos
  cifrados con un token, y qué hacer si el token se pierde.
- [docs/migrar-desde-v4.md](docs/migrar-desde-v4.md) — pasar un proyecto de
  davgen 4.x a 5.
- [docs/publicar.md](docs/publicar.md) — lista de control para publicar una
  versión.
- [CHANGELOG.md](CHANGELOG.md) — qué cambió.

## Licencia y responsabilidad

[MIT](LICENSE). El código que davgen genera en tu proyecto te pertenece, sin
condiciones — y con él, la responsabilidad de revisarlo, protegerlo y cumplir la
ley con los datos que guarde. davgen no recoge ningún dato tuyo. El detalle,
en lenguaje llano: [DESCARGO.md](DESCARGO.md).
