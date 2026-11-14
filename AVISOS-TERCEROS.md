# Software de terceros, licencias y marcas

davgen es un generador de código. **No incluye ni redistribuye** ninguno de los
marcos y bibliotecas sobre los que funciona el sistema generado: cada uno se
descarga en el equipo del usuario, desde su fuente oficial y con su propio
gestor de paquetes (`composer`, `npm`, `pip`), en el momento de crear el
proyecto. Este documento resume qué usa cada parte y bajo qué condiciones.

> Las licencias cambian con el tiempo. La tabla refleja lo declarado por cada
> proyecto al preparar esta versión; ante cualquier uso comercial conviene
> revisar el archivo `LICENSE` de la versión concreta que se instale.

## 1 · Dependencias del generador (se instalan con `pip install davgen`)

| Paquete | Licencia | Para qué |
|---|---|---|
| [bcrypt](https://github.com/pyca/bcrypt) | Apache-2.0 | Hash de la contraseña inicial del administrador |
| [PyMySQL](https://github.com/PyMySQL/PyMySQL) | MIT | Leer el esquema y aplicar SPs/seeds |
| [cryptography](https://github.com/pyca/cryptography) | Apache-2.0 o BSD-3-Clause | Accesos cifrados (AES-256-GCM) |

`mysql-connector-python` (Oracle; GPLv2 con la *Universal FOSS Exception*) **no
es una dependencia**. davgen lo usa solo si el usuario ya lo tiene instalado y
no tiene PyMySQL. No se distribuye con davgen.

## 2 · Lo que el sistema generado necesita (lo instala el usuario)

| Componente | Licencia | Cómo llega al proyecto |
|---|---|---|
| [Laravel](https://github.com/laravel/framework) y Laravel Sanctum | MIT | `composer create-project laravel/laravel` |
| [React](https://github.com/facebook/react) | MIT | `npm create vite` |
| [Vite](https://github.com/vitejs/vite) | MIT | `npm` |
| [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) | MIT | `npm install` |
| [daisyUI](https://github.com/saadeghi/daisyui) | MIT | `npm install` |
| [Capacitor](https://github.com/ionic-team/capacitor) (opcional, app móvil) | MIT | `npm install` (lo decide el usuario) |
| [Swagger UI](https://github.com/swagger-api/swagger-ui) (opcional) | Apache-2.0 | Se carga desde un CDN en `swagger.html`; no se copia |
| MySQL / MariaDB | GPLv2 | Servidor que el usuario ya tiene; davgen solo se conecta |

Las **plantillas** de este repositorio (`src/davgen/plantillas/`) son código
original de davgen escrito *para* esas plataformas: usan sus API públicas, no
copian su código fuente.

### Sobre los zips `_laravel.zip` / `_react.zip`

Las versiones 4.x distribuían un «bundle» con un proyecto Laravel y uno React ya
instalados (`vendor/` y `node_modules/` completos: cientos de paquetes de
terceros, cada uno con su licencia y sus avisos). **davgen 5 ya no distribuye
ese bundle.** Quien quiera evitar la descarga en cada proyecto puede empaquetar
los suyos en su propio equipo con `scripts/empaquetar-plantillas.ps1`; esos
zips son para uso propio. Si se comparten con terceros, se están redistribuyendo
esos paquetes y hay que conservar los avisos de licencia que traen dentro.

## 3 · Inicio de sesión con Google (opcional, apagado por defecto)

- El sistema generado carga el script oficial de *Google Identity Services*
  desde `accounts.google.com` y dibuja **el botón oficial**, sin modificarlo:
  es lo que exigen las
  [pautas de marca de Sign in with Google](https://developers.google.com/identity/branding-guidelines).
- Hace falta un **Client ID de OAuth propio** de cada proyecto (Google Cloud
  Console). davgen no trae ninguno. Usar el Client ID de otra organización no
  funciona fuera de sus dominios autorizados y contraviene las
  [Condiciones de los servicios de API de Google](https://developers.google.com/terms).
- Quien activa el login con Google es responsable de su pantalla de
  consentimiento y de su política de privacidad.

## 4 · Marcas

Laravel es una marca de Taylor Otwell. React es una marca de Meta Platforms,
Inc. Google y el logotipo de Google son marcas de Google LLC. MySQL es una marca
de Oracle Corporation. MariaDB es una marca de MariaDB Corporation Ab. Los demás
nombres pertenecen a sus titulares.

**davgen es un proyecto independiente**: no está afiliado, patrocinado ni
avalado por ninguno de ellos. Sus nombres se usan únicamente para describir con
qué tecnologías es compatible el código generado. Si publicas un producto hecho
con davgen, no uses esas marcas en el nombre del producto ni en su dominio.

## 5 · Ejecutable de Windows (opcional)

`scripts/compilar-exe.ps1` produce un `.exe` con
[PyInstaller](https://pyinstaller.org) (GPLv2 con una excepción que permite
distribuir los ejecutables generados bajo cualquier licencia). El ejecutable
incluye el intérprete de Python (licencia PSF), bcrypt, PyMySQL y cryptography; al
distribuirlo deben acompañarlo este archivo y `LICENSE`.
