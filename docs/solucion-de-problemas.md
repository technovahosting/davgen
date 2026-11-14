# Solución de problemas

Lo que más veces trabó a los proyectos reales, con su causa y su arreglo.
Primer paso siempre:

```bash
davgen doctor --conexiones                       # entorno de desarrollo
davgen doctor --conexiones --entorno produccion  # base y FTP del hosting
```

Abre la conexión, mira y cierra (no escribe nada) y, si algo falla, dice la
causa probable y qué hacer.

## No conecta a MySQL

| Síntoma | Causa | Qué hacer |
|---|---|---|
| «MySQL no está iniciado en esta PC» (error 2003 con host `127.0.0.1`) | El servicio está apagado | Iniciar MySQL (XAMPP, Laragon, servicio de Windows). Revisar `[bd] puerto` |
| «no hay respuesta de host:3306» (2003 con un host remoto) | El hosting no acepta conexiones remotas desde tu IP | En el panel del hosting, **MySQL remoto**: autorizar tu IP (o «cualquier host») para ese usuario |
| «usuario o contraseña rechazados» (1045) | Credenciales, o usuario sin permiso desde tu IP | En hosting compartido el usuario lleva el prefijo de la cuenta (`u123_usuario`). Revisar que la IP esté autorizada |
| «el usuario no tiene permisos sobre la base» (1044) | Usuario no asignado a la base | Asignarlo con todos los privilegios |
| «la base no existe» (1049) | Nombre mal escrito o base sin crear | Crearla en `utf8mb4` o corregir `[bd] database` |
| «el hosting bloqueó las conexiones por una hora» (1226) | El usuario de MySQL agotó su cupo de conexiones nuevas por hora | Ver «Límites del hosting» más abajo |
| «todas las conexiones simultáneas» (1203) | Demasiadas conexiones abiertas a la vez | Ver «Límites del hosting» más abajo |
| La contraseña «no funciona» y lleva `;` `#` o `%` | (versiones anteriores la leían cortada) | davgen 5 la lee completa, sin comillas |
| «No hay controlador de MySQL» | Falta la librería | `pip install pymysql` |

### Límites del hosting: el sitio da 500 en todo, también en el login

El hosting compartido limita cuántas conexiones **nuevas** puede abrir por hora
cada usuario de MySQL (un valor habitual es 500). PHP abre una por petición, y
cada petición autenticada consulta la base: unos pocos usuarios activos —o una
pantalla con muchas fotos, que son un pedido cada una— agotan el cupo en
minutos, y el sitio queda caído hasta que empieza la hora siguiente.

**Cómo reconocerlo.** En `storage/logs/laravel.log` del servidor se repite:

```
SQLSTATE[HY000] [1226] User '…' has exceeded the 'max_connections_per_hour' resource
```

**Qué hacer en el momento.** Esperar a que pase la hora. No ejecutar `davgen`
contra producción mientras tanto: sus conexiones salen del mismo cupo.

**Qué hace davgen para evitarlo:**

- El backend generado usa **conexiones persistentes**: el servidor web las
  reutiliza en vez de abrir una por petición. Lo activa `bootstrap/app.php`, que
  viaja en el despliegue incremental: un sitio ya publicado lo recibe con
  `davgen generar --entorno produccion`, sin tocar su `.env` ni su configuración.
  Se comprueba con `SHOW PROCESSLIST`: aparecen conexiones en `Sleep`.
- Una corrida de `davgen` usa **una sola conexión** de principio a fin.
- El frontend guarda en memoria los archivos ya descargados (`descargar()` de
  `api.js`) y las listas de los desplegables, para no volver a pedirlos.

**El efecto contrario (error 1203).** Las conexiones persistentes quedan
abiertas, y el hosting también limita las simultáneas (`max_user_connections`).
Si aparece el error 1203, apagarlas: `DB_PERSISTENT=false` en el `.env` del
servidor, o `[opciones] conexiones_persistentes = no` y volver a generar.

Otra cosa a saber: una conexión reutilizada conserva lo que la petición anterior
dejó a medias. El código generado no deja transacciones abiertas ni usa tablas
temporales; el código propio debe cerrar las suyas (`DB::transaction(...)`).

**No tengo MySQL y solo quiero ver el código:** `davgen generar --local` genera
todo sin base de datos.

**«Faltan tablas de seguridad»:** se crean con `davgen seguridad` (antes había
que ejecutar `00-seguridad.sql` a mano, y sin cliente de MySQL no había cómo).

**Error 1267 «Illegal mix of collations» en un `pcru*`** (MariaDB 10.11 o
superior): la base usa una colación por defecto distinta de la de las tablas
(`utf8mb4_unicode_ci`, la que usan los scripts). Suele resolverse creando la
base con esa misma colación; si persiste, hay que poner `COLLATE` explícito en
la comparación que falla. Está anotado como pendiente del generador.

## No despliega al FTP

| Síntoma | Causa | Qué hacer |
|---|---|---|
| «el nombre no se resuelve (DNS)» | La red no resuelve el dominio | Poner la **IP** del servidor en `[ftp] host` |
| «usuario o contraseña del FTP rechazados» (530) | Credenciales | El usuario suele ser `cuenta.usuario` y la contraseña es la de la **cuenta FTP**, no la del panel |
| «no hay respuesta de host:21» | Firewall o red que bloquea FTP | Probar otra red; confirmar el host |
| `generar` termina pero **no subió nada** | Estás en desarrollo | Con archivos de acceso por entorno solo se publica con `--entorno produccion` |
| Dice «NO se sube: sin sección [ftp] completa» | Falta host, usuario o password | Completar `[ftp]` en `_acceso.produccion.ini` |
| Subió el zip pero el sitio da 404/500 | No se pudo llamar a `descomprimir.php` (falta `[ftp] url`, o la red no resuelve el dominio) | Poner `[ftp] url` con `https://`; reintentar desde otra red |
| La API responde pero el navegador la bloquea | `[ftp] url` con `http://` y el hosting fuerza HTTPS (contenido mixto) | Usar `https://` y volver a desplegar el frontend |
| 500 con «Composer detected issues… PHP version» | El servidor tiene PHP menor a 8.2 | Subir la versión de PHP en el panel del hosting |
| Tras desplegar sigue el comportamiento viejo | opcache del servidor | Esperar un minuto o reiniciar opcache desde el panel |
| Un archivo propio no llegó al servidor | (versiones anteriores solo subían `Custom/` dentro de `app/`) | davgen 5 sube todo PHP propio de `app/` y `routes/`. Comprobar con `davgen comparar --remoto` |
| «fuentes idénticas» y el frontend no sube | No cambió nada en `src/`, `public/` ni la configuración | Es correcto. Si cambiaste solo `.env`, no cuenta: la URL de la API se fija al desplegar |

### Antes de publicar: comparar con lo que hay en el servidor

```bash
davgen comparar --remoto            # baja el PHP publicado (solo lectura) y compara en local
davgen comparar --remoto --detalle  # con las diferencias línea a línea
```

Baja **una vez** `app/`, `routes/` y `bootstrap/app.php` a
`_backendGenerado/_remoto/` y todo lo demás ocurre en tu PC: qué archivos son
iguales, cuáles cambiarían, cuáles faltan subir y cuáles están en el servidor
sin estar en tu proyecto (subidos a mano). Además valida con `php -l` la
sintaxis de todo lo que se subiría. Si sale un error de sintaxis, **no
desplegar**.

## El botón de Google no aparece o no deja entrar

1. `davgen doctor` debe mostrar «Google: activo con Client ID propio». Si dice
   «activo pero SIN Client ID», falta cargarlo.
2. En la base, `tbl_seg_parametro` debe tener `google_auth_activo = 1` y
   `google_client_id` con tu Client ID. Los parámetros se siembran una sola
   vez: cambiarlos después en el `.ini` no cambia la base — se editan en la
   tabla.
3. En Google Cloud Console, el Client ID debe tener como **orígenes
   autorizados de JavaScript** exactamente los dominios donde corre la app
   (`https://tu-dominio.com`, y `http://localhost:5173` para desarrollo). Sin
   eso Google rechaza el botón.
4. El Client ID debe ser **propio del proyecto**. Uno de otra organización no
   funciona fuera de sus dominios.
5. «Tu acceso está pendiente de aprobación» no es un error: el correo no
   existía y quedó en la cola. Lo aprueba un administrador, o se agrega su
   dominio a `google_dominios_permitidos`.
6. En un proyecto generado antes de la 4.36 hay que montar el botón a mano
   (dos líneas): ver `src/components/generados/LEEME-GOOGLE.md`.

Guía completa: `CONFIGURAR-GOOGLE-AUTH.md` en la raíz de cada proyecto.

## Otros

| Síntoma | Qué pasa |
|---|---|
| Una ruta protegida sin token responde 500 en vez de 401 | Falta la cabecera `Accept: application/json` en la petición |
| Guardar deja campos vacíos | `actualizar` reemplaza todas las columnas: hay que enviar el registro completo, y los parámetros llevan prefijo `p` |
| Tras agregar una columna, el CRUD falla | Regenerar: el SP, el controller y el service deben salir de la misma lectura del esquema |
| Los registros «desaparecen» después del 100 | El listado pagina con un máximo de 100 por página |
| Las fechas salen corridas de día | La base guarda en UTC; la aplicación debe convertir a la hora local al mostrar |
| `generar` «recreó» el proyecto Laravel | No ocurre desde davgen 5: un Laravel sin `vendor/` se repara con `composer install` |
| La app se ve siempre oscura o no cambia de tema | Un `App.jsx` anterior con colores fijos: ver `src/components/generados/LEEME-TEMA.md` |
