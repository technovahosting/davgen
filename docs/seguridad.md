# Seguridad del sistema generado

Qué se probó, qué se encontró, qué quedó corregido y qué conviene hacer en cada
proyecto. Las pruebas se hicieron **en local**: un sistema de ejemplo generado
completo, con su base MySQL, su API corriendo en PHP 8.3 y la misma carpeta
que se subiría al hosting servida por un Apache.

## Resultado

| Área | Resultado |
|---|---|
| Inyección SQL (login, filtros, id, alta, rutas públicas) | **No vulnerable** |
| Saltos de autenticación y de permisos | **No vulnerable** |
| Carga de archivos (php, phtml, .htaccess, html, exe, svg, `../`, doble extensión) | **No vulnerable** |
| Acceso a archivos de otro usuario | **No vulnerable** |
| **Carpeta publicada (`.env`, logs, archivos de usuarios)** | **Vulnerable — corregido** |
| Código de verificación en dos pasos escrito en el log | **Corregido** |
| Mensajes internos de MySQL en errores | **Corregido** |
| Averiguar qué correos existen por el tiempo de respuesta | **Corregido** |
| Sesiones que no vencían nunca | **Corregido** |

### Por qué no hay inyección SQL

- La escritura pasa por procedimientos almacenados con todos los valores
  **enlazados** (`CALL pcru…(?, ?, …)`); nunca se arma SQL con texto del usuario.
- En los listados, el **campo** y el **operador** de cada filtro se comparan
  contra una lista cerrada, y el valor va enlazado.
- Hay una prueba automática que impide volver atrás: ninguna plantilla PHP puede
  usar `whereRaw`, `DB::raw` con datos de la petición ni interpolar variables en
  un SQL.

Se probaron, entre otras: `' OR '1'='1`, `UNION SELECT` sobre la tabla de
usuarios, sentencias apiladas con `DROP`/`DELETE`, subconsultas como nombre de
campo, operadores inventados e identificadores como `1 OR 1=1`.

## Lo que sí era grave: la carpeta publicada

En hosting compartido el proyecto Laravel **completo** se sube dentro de una
carpeta servida por web (`/servicio`). Con el `.htaccess` original de Laravel,
todo archivo que existe se entrega tal cual. Cualquiera podía bajar:

| Archivo | Qué exponía |
|---|---|
| `/servicio/.env` | Usuario y contraseña de la base de datos, clave de la aplicación |
| `/servicio/storage/logs/laravel.log` | Errores, correos y —si no había correo configurado— **códigos de verificación válidos** |
| `/servicio/storage/app/archivos/…` | Los archivos privados que suben los usuarios |
| `/servicio/composer.lock`, `vendor/composer/installed.json` | Versiones exactas de todo (para buscar fallas conocidas) |
| `/servicio/database/database.sqlite` | La base de muestra de Laravel |

Con el `.env` no hace falta ninguna inyección: se entra directo a la base.

**Corrección (desde davgen 5):**

- El despliegue antepone un bloque de reglas al `.htaccess` de la raíz que
  niega las carpetas internas, los archivos ocultos y los archivos sueltos del
  proyecto; y pone un `.htaccess` «denegar todo» dentro de cada carpeta interna
  (segunda barrera, por si alguien reemplaza el de la raíz).
- Ya no viajan al servidor las pruebas, `.env.example`, la base sqlite, ni lo
  que es de la PC de desarrollo: archivos subidos, sesiones, caché y
  configuración cacheada.
- Después de cada despliegue davgen **pide esos archivos desde afuera** y avisa
  si alguno se puede bajar.

Medido en local: 12 archivos sensibles expuestos antes, 0 después; `robots.txt`
y `favicon.ico` siguen públicos.

### Sitios publicados con versiones anteriores

No tienen esta protección. Para cada proyecto ya publicado:

```bash
davgen doctor --conexiones --entorno produccion   # dice si la carpeta está expuesta
davgen proteger --entorno produccion              # sube solo los .htaccess de protección
```

`proteger` no toca el código ni el `.env` del servidor, y también se aplica solo
en el siguiente despliegue. **Si un sitio estuvo expuesto, hay que dar por
conocidas sus contraseñas**: cambiar la de la base de datos (y actualizar el
`.env` del servidor), la de los administradores y, si se usa, regenerar
`APP_KEY`.

## Otras correcciones

| Qué pasaba | Ahora |
|---|---|
| Sin correo configurado, el código de verificación se escribía en el log | Solo en desarrollo (`APP_DEBUG=true`); en producción se registra el error, no el código |
| Un id no numérico devolvía 500 con el mensaje de MySQL («Data truncated for column…») | 422 «Identificador inválido»; los errores de la base van al log y al cliente un texto genérico. Solo los mensajes de reglas de negocio (`SIGNAL`) se muestran |
| El login respondía más rápido si el correo no existía (460 ms contra 57 ms) | Mismo tiempo en los dos casos |
| Sin la cabecera `Accept: application/json`, una ruta protegida respondía 500 | 401 |
| Los tokens de sesión no vencían | Vencen a las 12 horas (`sesion_minutos` en `tbl_seg_parametro`; 0 = nunca) |
| El alta pública pasaba al procedimiento el `pid` y el `pactivo` que mandara el visitante | Se fuerzan a «registro nuevo» y «activo» (medida preventiva: en la prueba no se logró pisar un registro) |
| Las respuestas no llevaban cabeceras de seguridad | El bloque de `.htaccess` agrega `nosniff`, `X-Frame-Options`, `Referrer-Policy` y HSTS |

## Lo que queda a cargo de cada proyecto

1. **Cambiar la contraseña del administrador** al primer ingreso y revisar los
   usuarios sembrados.
2. **HTTPS obligatorio** y `[ftp] url` con `https://`.
3. **Configurar el correo** (`MAIL_*` en el `.env` del servidor) antes de
   activar la verificación en dos pasos por correo; o usar la de aplicación
   (TOTP), que no depende del correo.
4. **Activar la verificación en dos pasos** para los administradores
   (`2fa_obligatorio` en `tbl_seg_parametro`).
5. **CORS**: Laravel permite por defecto llamadas desde cualquier origen. Con
   tokens en cabecera (no cookies) eso no permite suplantar a nadie, pero si la
   app vive en el mismo dominio que la API conviene restringirlo en
   `config/cors.php` (`allowed_origins`).
6. **El token de sesión se guarda en el navegador** (`localStorage`). Un script
   malicioso inyectado en la página podría leerlo: no agregar HTML sin escapar
   (`dangerouslySetInnerHTML`) ni scripts de terceros que no sean de confianza.
7. **Límites de intentos**: `rate_limit_auth` (5 por minuto por IP),
   `rate_limit_publico` y `rate_limit_api` se ajustan en la base. El código de
   verificación tiene 6 dígitos y vence en 10 minutos: con 5 intentos por
   minuto no es adivinable desde una IP, pero no hay bloqueo de cuenta ante
   ataques repartidos.
8. **PHP 8.2 o superior** y actualizar dependencias (`composer update`) con
   cierta regularidad.
9. **Respaldos** de la base fuera del servidor.
10. El **FTP viaja sin cifrar**: no desplegar desde redes públicas.

## Lo que no se probó

- El sistema publicado de verdad en un hosting: el Apache local reproduce las
  reglas, pero cada hosting (LiteSpeed, nginx por delante) puede comportarse
  distinto. Por eso davgen comprueba la exposición **después** de desplegar, y
  `davgen doctor --conexiones` lo repite cuando se quiera.
- El inicio de sesión con Google (necesita un Client ID real y un token de
  Google).
- Denegación de servicio con mucho volumen, y ataques que requieran una sesión
  de navegador real (XSS en el frontend, clickjacking).
- Una auditoría hecha por un tercero. Esto es una batería de pruebas honesta,
  no una certificación.
