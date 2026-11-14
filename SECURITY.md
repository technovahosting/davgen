# Seguridad

## Reportar una vulnerabilidad

No abras un *issue* público. Usa **«Report a vulnerability»** en la pestaña
*Security* del repositorio (aviso privado de GitHub). Incluye la versión de
davgen (`davgen --version`), qué archivo generado o qué parte del generador
está afectada y cómo reproducirlo.

Se consideran en alcance:

- fallas del **generador** (por ejemplo, que escriba fuera del proyecto, que
  filtre credenciales del `.ini` a un archivo que se versiona o se despliega);
- fallas en el **código que davgen genera** (autenticación, permisos,
  inyección SQL, carga de archivos, el extractor del despliegue), porque
  afectan a todos los sistemas generados.

Solo recibe correcciones la última versión publicada.

## Lo que davgen hace con tus credenciales

- Las contraseñas de la base, del FTP y la inicial del administrador están en
  `_acceso.<entorno>.ini`, en texto plano y fuera de git, o —con
  `davgen acceso cifrar`— en `_acceso.<entorno>.cifrado`, que solo se abre con el
  token del proyecto ([docs/accesos-cifrados.md](docs/accesos-cifrados.md) explica
  qué protege y qué no).
- davgen solo se conecta a la base y al FTP que figuran en ese archivo. No
  envía telemetría ni datos a ningún otro servicio.
- La contraseña de la base se escribe en el `.env` del proyecto Laravel (que
  Laravel necesita) y viaja al servidor en el primer despliegue. El `.env`
  remoto no se vuelve a tocar.
- La contraseña inicial del administrador **no** se escribe en los archivos de
  prueba generados (`api.http`, colección Postman, script de humo): llevan un
  marcador para completarla al probar. Sí se muestra en pantalla al terminar
  `generar` y `seguridad`. **Cámbiala al primer ingreso**: el seed no la
  restablece.
- El despliegue usa **FTP sin cifrar**, que es lo que ofrece la mayoría del
  hosting compartido: las credenciales viajan en claro. En redes que no
  controlas, despliega por otro medio.
- El extractor que se sube en el primer despliegue está protegido por un token
  aleatorio de un solo uso.

## Carpeta publicada

El despliegue en hosting compartido deja el proyecto Laravel completo dentro de
una carpeta servida por web. davgen la protege con reglas `.htaccess` y, al
terminar, pide desde afuera el `.env` y los logs para confirmar que no se
pueden bajar. **Un sitio desplegado con una versión anterior a la 5 no tiene
esa protección**: `davgen proteger --entorno produccion`, y después cambiar la
contraseña de la base de datos. Detalle en [docs/seguridad.md](docs/seguridad.md).

## Lista mínima antes de poner un sistema generado en producción

1. Cambiar la contraseña del administrador y revisar los usuarios sembrados.
2. `[ftp] url` con `https://`.
3. Confirmar que `APP_DEBUG=false` en el `.env` del servidor (davgen lo deja
   así al desplegar).
4. Si activas Google: Client ID propio, con solo tus dominios como orígenes
   autorizados.
5. Rotar cualquier credencial que haya estado alguna vez en un repositorio.
