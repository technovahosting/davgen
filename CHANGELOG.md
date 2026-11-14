# Cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
versiones según [SemVer](https://semver.org/lang/es/).

## [5.1.0] — sin publicar

### Límite de conexiones del hosting compartido (errores 1226 y 1203)

Un sistema en producción quedó caído una hora, login incluido: el hosting
limita las conexiones **nuevas** a MySQL por hora de cada usuario de la base, y
el backend abría una por petición. Guía: «Límites del hosting» en
[docs/solucion-de-problemas.md](docs/solucion-de-problemas.md).

- **Conexiones persistentes en el backend generado.** `bootstrap/app.php`
  activa `PDO::ATTR_PERSISTENT` para `mysql` y `mariadb`. Va en ese archivo y
  no en `config/database.php` porque el despliegue incremental sí lo lleva: un
  sitio ya publicado recibe el cambio con solo regenerar y desplegar, sin tocar
  su `.env` ni su configuración. Nueva clave `[opciones]
  conexiones_persistentes` (`si` por defecto) e interruptor `DB_PERSISTENT` en
  el `.env` (se agrega si falta; nunca se vuelve a encender si se apagó).
- **davgen usa una sola conexión por corrida** (`bd.una_sola_conexion`): antes
  conectaba una vez por paso (validar, leer el esquema, comparar y aplicar
  procedimientos, seeds), descontando del mismo cupo que el sitio publicado.
- **Mensajes claros** para el 1226 («el hosting bloqueó las conexiones por una
  hora») y el 1203 («conexiones simultáneas», con cómo apagar las
  persistentes), en lugar del texto crudo de MySQL. No se reintenta.
- **Frontend:** `descargar()` en `api.js` guarda en memoria los archivos con
  sesión (fotos, PDF) y no vuelve a pedirlos; `SelectRelacion` comparte la
  lista de cada catálogo entre desplegables. `api.js` solo se crea si no
  existe: en un proyecto anterior hay que copiar `descargar()` a mano.

### Privacidad, términos, conservación de datos y accesibilidad

- **Política de privacidad y términos de uso** generados
  (`components/generados/AvisoLegal.jsx`), con los datos de la nueva sección
  `[legal]` del `.ini`. Describen lo que el sistema hace de verdad con los
  datos. El `App.jsx` de un proyecto nuevo los muestra en el ingreso y en el
  menú; en uno anterior se montan con una línea (`LEEME-LEGAL.md`).
- **Conservación de datos definida y aplicada.** `app/Utils/Retencion.php`
  borra la bitácora pasada de `retencion_bitacora_dias` (365 por defecto, `0` =
  no se borra) y, un día después de vencer, los códigos de verificación, los
  enlaces de recuperación y las sesiones. Corre en algunos inicios de sesión
  (no necesita tareas programadas) y nunca toca cuentas, archivos ni datos del
  negocio.
- **Sin aviso de cookies, a propósito:** el sistema no usa cookies ni recursos
  de terceros; el texto de privacidad lo dice y `LEEME-LEGAL.md` explica cuándo
  sí haría falta.
- **Accesibilidad** de las pantallas generadas: nombre para los controles que
  no lo tenían (búsqueda, «, », filas por página, acciones de cada fila,
  interruptor del menú), ventanas que se cierran con Esc y reciben el foco,
  avisos y errores anunciados, encabezados de tabla con `scope`, etiquetas
  visibles en el ingreso, enlace «Saltar al contenido», y `index.html` con
  `lang="es"` y el nombre del sistema como título.

### La contraseña del administrador la pone el usuario

- **davgen ya no trae ninguna contraseña de administrador**, ni fija ni
  inventada. La escribe quien crea el proyecto en `_acceso.<entorno>.ini`
  (`[seguridad] admin_password`); si falta, `generar` y `seguridad` la piden
  por teclado (sin mostrarla) o, sin terminal, se detienen diciendo dónde
  escribirla. Para integración continua: variable `DAVGEN_ADMIN_PASSWORD`
  (no se guarda).
- Se exige un mínimo: 8 caracteres, letras y números, sin repetir casi siempre
  el mismo carácter y distinta del correo del administrador.
- **Cambio de comportamiento:** un proyecto nuevo nace con `admin_password`
  vacía (antes, una aleatoria), y un proyecto que venía de la 4.x sin esa clave
  ya no usa la contraseña fija de aquella versión: hay que escribirla
  ([migrar-desde-v4.md](docs/migrar-desde-v4.md)). `generar --listar` no la
  necesita.
- davgen ya no muestra la contraseña en la consola: dice en qué archivo está.
- El `00-seguridad.sql` de un proyecto recién creado avisa en su cabecera que
  todavía no lleva la contraseña; `davgen seguridad` lo completa.

### Responsabilidad y textos legales

- **`DESCARGO.md`**: en lenguaje llano, qué es davgen y qué no. Sin garantía,
  el sistema generado y sus datos son responsabilidad de quien lo opera, los
  textos legales son plantillas y no asesoría, davgen no recoge ningún dato,
  y qué tener en cuenta al usarlo con un asistente de IA o para estudiar.
- **Privacidad y términos generados, más completos:** por qué se usan los
  datos, con quién se comparten, dónde se guardan, cómo se protegen, menores,
  derechos y cambios; y en los términos: aceptación, contenido cargado,
  disponibilidad «tal como está» y límite de responsabilidad sin recortar
  derechos irrenunciables.
- La pantalla de ingreso de un proyecto nuevo dice «Al ingresar aceptas…»
  (`<AvisoLegal conAceptacion />`).
- Claves nuevas en `[legal]`: `alojamiento` y `vigente_desde`.
- `LEEME-LEGAL.md` suma quién responde por qué, una lista de control para el
  desarrollador antes de publicar y las normas a consultar en Bolivia.

### Skill para Claude: crear un sistema conversando

- **Skill `crear-sistema`** (`skills/crear-sistema/`): con ella instalada,
  Claude lleva a la persona de «quiero un sistema de…» al sistema funcionando
  —propone las tablas, escribe el mockup, ejecuta davgen y guía la puesta en
  marcha—, explicando cada paso. Pensada para quien recién empieza. Trae las
  reglas del mockup con sus límites, la guía para ejecutarlo en local y dónde
  va el código propio.
- **El repositorio es un plugin de Claude Code** (`.claude-plugin/`): se
  instala con `/plugin marketplace add` y `/plugin install davgen@davgen`.
- **Descarga directa**: `scripts/empaquetar_skill.py` arma
  `dist/crear-sistema.zip` con la skill y el código de davgen adentro; no
  necesita el repositorio ni un índice de paquetes.
- La skill instala davgen desde su propia carpeta la primera vez.
- Guía: [docs/skill.md](docs/skill.md). `tests/test_skill.py` comprueba que
  cada comando y cada clave que enseña la skill existen.

### Pendiente (detectado al usar la 5.0)

- Las pruebas generadas `tests/Feature/Generados/RutasTest.php` usan las rutas
  de la versión 4 (`/api/tbl_x/sel`) y fallan con 404; las reales son
  `/api/{mod}/{recurso}/listar`.
- Un `<select>` del mockup con más de 10 opciones pierde las que sobran sin
  avisar (`esquema.py`).
- El listado público no filtra los registros inactivos en el servidor.
- Todas las columnas de un mockup salen `NOT NULL`, tengan o no `required`.

## [5.0.0] — sin publicar

Primera versión preparada para publicarse. Parte de davgen 4.36.0 y **genera el
mismo sistema** (rutas, SPs y estructura), con el generador reorganizado como
paquete instalable, probado y sin nada propio de su autor adentro. Cómo pasar
un proyecto existente: [docs/migrar-desde-v4.md](docs/migrar-desde-v4.md).

### Publicación

- **Paquete de Python** (`pip install davgen`, comando `davgen`) con
  `pyproject.toml`; el wheel pesa ~0,2 MB. El `.exe` pasa a ser opcional
  (`scripts/compilar-exe.ps1`) y ya no se versiona.
- **Licencia MIT** y `AVISOS-TERCEROS.md` (licencias y marcas de terceros).
  El código generado pertenece al usuario.
- **Eliminado el bundle** `_davgen4-*.zip` (56 MB) con Laravel y React
  preinstalados: redistribuía `vendor/` y `node_modules/`. Los proyectos se
  crean con `composer` y `npm`; el proyecto React ahora se crea con
  `create-vite` cuando falta (antes solo se avisaba).
- **Controlador MySQL**: PyMySQL (MIT) en lugar de `mysql-connector-python`
  (GPL), que se sigue aceptando si es el que está instalado.
- **Eliminada la «protección de acceso»** (contraseña día × hora y
  `~/.davgen_lock`, que inutilizaba el generador en todo el equipo).
- **Valores por defecto neutros**: sin Client ID de Google, sin cuenta dueña
  sembrada, sin autor fijo; Google apagado; `produccion` y `front` en `no`.
- **Contraseña de administrador aleatoria** por proyecto
  (`[seguridad] admin_password`) en lugar de una fija.
- `_configtotal.ini` queda fuera de git en los proyectos nuevos y se escribe
  `_configtotal.ejemplo.ini` sin secretos.

### Seguridad (de una batería de ataques en local — [docs/seguridad.md](docs/seguridad.md))

- **Crítico: la carpeta publicada servía por web el `.env`, los logs y los
  archivos de los usuarios.** El despliegue sube Laravel completo dentro de una
  carpeta pública y el `.htaccess` de Laravel entrega todo archivo que exista.
  Ahora el despliegue antepone reglas que niegan lo interno, pone un
  «denegar todo» en cada carpeta interna, deja de subir lo que es de la PC de
  desarrollo (archivos subidos, sesiones, caché, pruebas, sqlite) y comprueba
  desde afuera el resultado. `davgen proteger` lo aplica a un sitio ya
  publicado; el despliegue incremental también.
- El código de verificación en dos pasos solo se escribe en el log en
  desarrollo.
- Los errores de MySQL ya no llegan al cliente (solo los mensajes `SIGNAL` de
  reglas de negocio); un id no numérico responde 422 en vez de 500.
- El login tarda lo mismo exista o no el correo.
- Las sesiones vencen (`sesion_minutos`, 12 horas por defecto).
- Sin `Accept: application/json` una ruta protegida responde 401, no 500.
- El alta pública no deja elegir el id ni el estado del registro.
- Sin inyección SQL ni saltos de permisos en las pruebas; una prueba automática
  impide que una plantilla arme SQL con datos de la petición.

### Entornos, requisitos y diagnóstico

- **Dos archivos de acceso**: `_acceso.desarrollo.ini` y
  `_acceso.produccion.ini` (base, FTP y contraseña inicial del admin).
  `_configtotal.ini` queda sin contraseñas y se versiona. `--entorno` elige;
  **en desarrollo nunca se publica por FTP**. `davgen entornos` separa los
  accesos de un proyecto anterior, que sigue funcionando sin hacerlo.
- **Accesos cifrados** (`davgen acceso`): los archivos de accesos se guardan
  cifrados (AES-256-GCM, clave derivada con scrypt) con un token por proyecto
  que se pide al ejecutar. Llave maestra opcional para poner un token nuevo si
  se pierde; sin ella, `acceso reiniciar`. Nueva dependencia: `cryptography`.
  Ver [docs/accesos-cifrados.md](docs/accesos-cifrados.md).
- **Requisitos al ejecutar**: `generar` y `doctor` listan mockup, base, FTP y
  Google con su estado y qué hacer con lo que falta.
- **`davgen doctor --conexiones`** prueba de verdad la base y el FTP (solo
  lectura) y traduce los errores típicos a una causa y un arreglo
  ([docs/solucion-de-problemas.md](docs/solucion-de-problemas.md)).
- **`davgen comparar --remoto`** baja una vez el backend publicado y lo compara
  en local con lo que se desplegaría; valida la sintaxis PHP antes de publicar.
- **Interfaz adaptable y con tema**: el `App.jsx` nuevo usa un menú tipo cajón
  (fijo en PC, oculto en el celular) y los colores del tema; `tema.js` y
  `SelectorTema.jsx` se generan siempre (claro, oscuro o el del sistema, que es
  el valor por defecto).

### Arquitectura

- **Plantillas como datos**: 66 plantillas extraídas del código Python a
  `src/davgen/plantillas/`. Un proyecto reemplaza las que quiera en
  `_plantillas/`. Comandos `davgen plantillas listar | copiar`.
  La extracción no cambió la salida (comparada archivo por archivo).
- **Modo `--local`**: genera todo sin base de datos, sin FTP y sin crear
  Laravel/React. Es la base de las pruebas y sirve para CI.
- Conexión a la base centralizada en `nucleo/bd.py`; fechas en
  `nucleo/reloj.py` (salida reproducible con `SOURCE_DATE_EPOCH`).
- `davgen seguridad`: crea en la base las tablas `tbl_seg_*` ejecutando
  `00-seguridad.sql` (reescrito antes con los valores del `.ini`). Antes había
  que hacerlo a mano con un cliente de MySQL. No toca una base ya sembrada.
- Comandos nuevos: `davgen nuevo`, `davgen doctor` y `davgen actualizar`
  (pone al día las guías y el `.ini` de un proyecto de la 4.x sin generar nada). `generar`/`verificar` ya no
  crean archivos en una carpeta que no es un proyecto, y `--version` no escribe
  nada.
- Se retiró `gen_frontend.py` (generador TypeScript alternativo que nunca se
  conectó al flujo).

### Pruebas

- 60+ pruebas con pytest, sin servicios externos: mockup → tablas,
  configuración, plantillas, generación de punta a punta, reproducibilidad,
  `php -l` de todo el PHP generado, selección de archivos del despliegue,
  aplicación de SPs con un doble de la conexión, y comportamiento del comando.
- `scripts/probar.ps1` / `probar.sh` para correrlo todo en local; CI en GitHub
  Actions (Linux y Windows).

### Corregido (observado en proyectos en producción)

- **`generar` borraba el proyecto Laravel** si no tenía `vendor/` (lo normal
  tras un `git clone`) y lo recreaba, llevándose el código propio. Ahora ejecuta
  `composer install`; una carpeta que no es un Laravel se aparta, no se borra.
- **El delta por FTP no subía código propio** fuera de `app/**/Custom/` y
  `app/Providers/` (`routes/Custom/`, rutas de dominio, `app/Dominio/`…): la API
  quedaba en 404/500. Ahora es propio todo PHP de `app/` y `routes/` sin la
  cabecera `@generated`, y nunca se borra del servidor.
- **`bootstrap/app.php` carga solo `routes/Custom/*.php`**: un punto de
  extensión estándar que no depende de editar archivos generados ni de un
  Provider que falla si el archivo aún no está en el servidor.
- **El botón de Google no aparecía**: comparaba el parámetro con `'1'` cuando la
  API entrega `true`, y además devolvía `null` antes de que existiera el nodo
  donde Google dibuja el botón.
- **Fechas y ENUM vacíos** se enviaban como `''` al SP y MySQL estricto los
  rechazaba incluso al leer o dar de baja; ahora van como `null`.
- **Las rutas públicas compartían el límite del login** (5/min por IP): límite
  propio `rate_limit_publico` (60/min, administrable en la base).
- **El `.env` del Laravel nuevo** traía sesión, caché y colas en `database`
  (tablas que davgen no crea) y daba 500 en local: ahora `file`/`sync`. Se lee
  con BOM y las contraseñas con símbolos se entrecomillan.
- Contraseñas del `.ini` con `;`, `#` o `%` se leían cortadas o fallaban.
- `guia.md` listaba las rutas anteriores a la 4.32 (`/tbl_x/sel…`).
- El nombre de la app de Capacitor siempre era «App», y la pantalla mostraba
  el marcador `__NOMBRE__` en vez del nombre del sistema.
- El módulo admite de 2 a 6 letras.

### Pendiente

- Mover a plantillas las partes que aún se arman en Python (rutas, cuerpo de
  los `pcru*`, service JS por tabla, archivos de prueba).
- Pruebas de integración con MySQL y con un servidor FTP reales (hoy se prueba
  la lógica con dobles; la subida y `leer_bd` se validaron a mano en la v4).
- `davgen diagnosticar`: decir qué cambiaría una versión nueva en un proyecto
  antes de regenerar (columnas, SPs, archivos personalizados).
- Las páginas generadas usan clases de daisyUI que cambiaron entre sus
  versiones 4 y 5; `COLLATE` explícito en los `pcru*` para MariaDB 10.11+;
  paginación en las páginas; regeneración por tabla; reinicio de opcache tras
  desplegar.
- Mensajes y documentación en inglés.

## 4.x

Uso interno. Su historial no forma parte de este repositorio.
