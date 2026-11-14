# Ver el sistema funcionando en la computadora

Hasta aquí solo hay archivos. Para abrir el sistema en el navegador hacen falta
programas instalados y una base de datos. Ve paso a paso y comprueba cada uno
antes de seguir: es donde más se traban quienes empiezan.

## 1 · Qué tiene que estar instalado

```bash
davgen doctor
```

Dice qué hay y qué falta. Se necesita:

| Programa | Para qué | Cómo conseguirlo |
|---|---|---|
| PHP 8.2 o superior | Ejecutar la API | Viene con Laragon o XAMPP (Windows), `brew`/`apt` |
| Composer | Descargar Laravel | getcomposer.org |
| Node.js 20 o superior | Ejecutar la aplicación React | nodejs.org |
| MySQL o MariaDB | La base de datos | Viene con Laragon o XAMPP; debe estar **iniciado** |

Si falta algo, explica cómo instalarlo y espera a que la persona lo haga. No
instales programas del sistema por tu cuenta.

## 2 · La base de datos

1. Crear una base vacía. Con cualquier cliente (phpMyAdmin, HeidiSQL, consola):

   ```sql
   CREATE DATABASE biblioteca_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. Pedirle a la persona que complete **ella misma** `_acceso.desarrollo.ini`:

   ```ini
   [bd]
   host = 127.0.0.1
   puerto = 3306
   usuario = (su usuario de MySQL; en Laragon y XAMPP suele ser root)
   password = (la suya; en Laragon y XAMPP suele ir vacía)
   database = biblioteca_dev
   ```

3. Comprobar:

   ```bash
   davgen doctor --conexiones
   ```

   Si no conecta, el mensaje explica por qué (MySQL apagado, usuario o
   contraseña incorrectos, la base no existe).

## 3 · Crear las tablas y generar

En tu terminal no puedes responder las preguntas de davgen: agrega `--si` a
estos comandos, **después** de decirle a la persona en qué base se va a
escribir y recibir su visto bueno en el chat.

```bash
davgen seguridad --si       # tablas de usuarios, roles y permisos (una sola vez)
```

Las tablas del negocio (las del mockup) **no las crea davgen**: las deja
escritas en `03-Backend/_backendGenerado/database/02_negocio.sql` y hay que
ejecutarlas una vez en la base. Con la consola:

```bash
mysql -u USUARIO -p biblioteca_dev < 03-Backend/_backendGenerado/database/02_negocio.sql
```

o importando ese archivo desde phpMyAdmin / HeidiSQL. Si pide contraseña, la
escribe la persona.

Después:

```bash
davgen generar --si
```

Esta vez davgen descarga Laravel y React (tarda unos minutos y necesita
internet), copia el código a `03-Backend/` y `04-Frontend/` y crea en la base
los procedimientos. Al terminar muestra un resumen: léelo y cuéntale a la
persona si algo quedó en amarillo o rojo.

## 4 · Levantar la API y la aplicación

Son **dos terminales abiertas a la vez**. Lo más claro para quien aprende es
que las abra la persona y vea cada una:

```bash
# Terminal 1 — la API
cd 03-Backend/backend
php artisan serve                 # queda en http://localhost:8000
```

```bash
# Terminal 2 — la aplicación
cd 04-Frontend/frontend
npm run dev                       # queda en http://localhost:5173
```

Antes de la terminal 2, el archivo `04-Frontend/frontend/.env` debe decir a
dónde está la API (créalo si no existe):

```ini
VITE_API_URL=http://localhost:8000/api
```

Si la carpeta del backend no se llama `backend`, es la otra que hay dentro de
`03-Backend/` además de `_backendGenerado`.

## 5 · Primer ingreso

Abrir `http://localhost:5173`.

- **Correo:** el de `[seguridad] admin_email` en `_configtotal.ini`
  (por defecto `admin@localhost`).
- **Contraseña:** la que la persona escribió en `_acceso.desarrollo.ini`
  (`[seguridad] admin_password`) antes de generar. No la copies al chat.
  Conviene cambiarla al entrar.

Debe aparecer un menú con una pantalla por cada tabla del mockup, donde se
puede agregar, editar, buscar y dar de baja.

## Si algo no sale

| Qué se ve | Causa habitual | Qué hacer |
|---|---|---|
| «Error 501» o la pantalla de ingreso no responde | La aplicación no sabe dónde está la API | Revisar `VITE_API_URL` en `.env` y reiniciar `npm run dev` |
| Error de red al ingresar | La API no está levantada | Revisar la terminal 1 |
| «Table … doesn't exist» | Falta ejecutar `02_negocio.sql` o `davgen seguridad` | Paso 3 |
| `davgen generar` se detiene pidiendo las tablas de seguridad | Falta `davgen seguridad` | Paso 3 |
| `php` no se reconoce, o es una versión vieja | PHP no está en el PATH | `davgen doctor`; en Windows, usar la terminal de Laragon |
| La página carga pero una pantalla sale vacía | Todavía no hay registros | Agregar uno con el botón de alta |

Para cualquier otro caso: `davgen doctor --conexiones` y el archivo
`03-Backend/backend/storage/logs/laravel.log`, que guarda el error real.

Al terminar la sesión, recuerda a la persona cerrar las dos terminales
(`Ctrl + C` en cada una).
