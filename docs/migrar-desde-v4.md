# Pasar un proyecto de davgen 4.x a davgen 5

davgen 5 genera **el mismo sistema** que 4.36 (mismas rutas, mismos SPs, misma
estructura de carpetas): las plantillas se extrajeron sin cambiar su contenido,
y eso se verificó comparando la salida antes y después. Lo que cambia es cómo
se instala y se usa el generador, los valores por defecto, y un puñado de
correcciones que sí alteran archivos generados (lista más abajo).

## 1 · Instalar

```bash
pip install davgen
davgen --version
```

El `_davgen4-*.exe` y el bundle `_davgen4-*.zip` que estén en la carpeta del
proyecto ya no se usan: se pueden borrar. (El `.exe` de la v4 sigue funcionando
por su cuenta; simplemente no es davgen 5.)

- **Ya no hay contraseña de acceso** (día × hora) ni archivo `~/.davgen_lock`.
  Si el equipo quedó bloqueado por la v4, ese archivo solo afecta al `.exe`
  viejo. La línea `validar_acceso` del `.ini` se puede borrar (davgen 5 solo
  avisa que sobra).
- **Ya no hace falta la tubería** `echo "" | …` para automatizar: `--si` y
  `--local` nunca preguntan nada.

## 2 · Poner al día el proyecto

```bash
davgen actualizar --ini
```

Renueva las guías y prompts que davgen escribe en la raíz (`leeme.html`,
`_davgen.leeme.md`, `CONFIGURAR-GOOGLE-AUTH.md`, `_prompts/`), escribe
`_configtotal.ejemplo.ini` y, con `--ini`, quita de `_configtotal.ini` la clave
`validar_acceso` (no cambia ningún otro valor). Avisa de las claves ausentes
cuyo valor por defecto cambió y de los restos de la v4 que se pueden borrar.
**No genera código ni se conecta a la base o al FTP.**

### Revisar `_configtotal.ini`

davgen 5 lee el `.ini` de la v4 sin cambios, pero **los valores por defecto de
las claves que falten son otros**. Si tu `.ini` no tiene alguna de estas líneas,
agrégala con el valor que tenías en la práctica:

| Clave | Por defecto en 4.x | Por defecto en 5 | Si lo usabas… |
|---|---|---|---|
| `[generar] produccion` | `si` | `no` | poner `produccion = si` |
| `[generar] front` | `si` | `no` | poner `front = si` |
| `[seguridad] google_auth_activo` | `si` | `no` | poner `google_auth_activo = si` |
| `[seguridad] google_client_id` | uno fijo, del autor | *(vacío)* | poner tu Client ID |
| `[seguridad] owner_email` | una cuenta fija | *(vacío)* | poner tu correo dueño |
| `[seguridad] admin_password` | — (una fija, igual en todos los sistemas) | la que escribes tú | ver abajo |
| `[proyecto] autor` | un autor fijo | *(vacío: sin `@author`)* | poner el tuyo |

> En una base **ya sembrada** nada de esto cambia datos: los parámetros de
> Google y los usuarios se siembran con `INSERT IGNORE` / sin tocar la
> contraseña. Los valores nuevos solo rigen para bases nuevas.

**Contraseña del administrador.** Un proyecto de la v4 no tiene
`admin_password` en el `.ini`, y davgen 5 ya no asume ninguna: la pide. Haz
esto, en este orden:

1. Si tu sistema todavía usa la contraseña fija que traía la versión 4,
   **cámbiala primero desde la aplicación**: era la misma en todos los sistemas
   generados.
2. Escribe en `_acceso.<entorno>.ini` → `[seguridad] admin_password` la
   contraseña que tu administrador usa hoy (o deja que davgen la pida por
   teclado). En una base ya sembrada davgen **no** cambia la contraseña: ese
   valor solo se usa al crear una base nueva.

**Otros cambios del `.ini`:**

- Una contraseña con `;` o `#` ahora se lee completa (antes dependía del
  parser). No hace falta entrecomillarla.
- El módulo admite de 2 a 6 letras (antes 2 a 4).
- Con `[entrada] tipo = mockup`, `[bd]` es opcional.

## 3 · Separar los accesos por entorno (recomendado)

```bash
davgen entornos --actual produccion     # o --actual desarrollo
```

Mueve `[bd]`, `[ftp]` y `admin_password` de `_configtotal.ini` a
`_acceso.produccion.ini`, crea `_acceso.desarrollo.ini` vacío para que cargues
tu base local, y agrega ambos al `.gitignore`. Desde ahí `davgen generar`
trabaja contra desarrollo y solo publica con `--entorno produccion`.
Es opcional: sin hacerlo, el proyecto sigue funcionando como antes.

## 3b · Secretos y git

davgen 5 escribe `_configtotal.ejemplo.ini` (el `.ini` sin contraseñas) en cada
generación, y el `.gitignore` de los proyectos **nuevos** excluye
`_configtotal.ini`. En un proyecto existente davgen no toca tu `.gitignore`:
decide tú. Si el repositorio es compartido o puede hacerse público:

```bash
echo _configtotal.ini >> .gitignore
git rm --cached _configtotal.ini
git add _configtotal.ejemplo.ini .gitignore
```

y **rota las contraseñas** que ya quedaron en el historial.

## 4 · Regenerar

```bash
davgen generar --local      # primero en seco: no toca BD ni FTP
davgen comparar             # qué cambiaría respecto de lo que está en uso
davgen generar              # cuando el diff sea el esperado
```

Archivos generados que **sí cambian** respecto de 4.36:

| Archivo | Cambio |
|---|---|
| `bootstrap/app.php` | Carga solo todo `routes/Custom/*.php` |
| `routes/api.php`, `routes/{mod}_api.php` | Las rutas `*Publico` usan su propio límite (`throttle:publico`, parámetro `rate_limit_publico`, 60/min) en vez del límite del login |
| Controllers por tabla | Fechas y ENUM vacíos se envían como `null` (antes `''`, que MySQL estricto rechazaba) |
| `01_seguridad.sql` | Nuevo parámetro `rate_limit_publico`; Google y owner según el `.ini` |
| `BotonGoogle.jsx` | Corregido: no se mostraba nunca |
| `.github/workflows/ci.yml` (si `ci = si`) | Instala davgen con `pip` en vez de buscar un `.exe` |
| `_davgen.leeme.md`, `leeme.html`, guías | Texto actualizado |
| Cabecera `@generated` de todos los PHP | Dice `v5.0.0` |

Si tenías rutas propias registradas a mano (en `AppServiceProvider` o en el
bloque `then:` de `bootstrap/app.php`, que davgen reescribe), lo más simple es
moverlas a `routes/Custom/` y borrar el registro manual.

## 5 · Primer despliegue con davgen 5

El delta por FTP ahora incluye **todo** tu PHP propio bajo `app/` y `routes/`
(antes solo `**/Custom/**` dentro de `app/` y `app/Providers/`). El primer
despliegue va a subir de una vez los archivos que nunca habían viajado, y
volverá a subir los propios que ya estaban (cambió la forma de registrarlos).
Es esperado e idempotente: el segundo despliegue ya no sube nada.

davgen 5 **no borra** un proyecto Laravel que no tenga `vendor/` (lo normal
tras clonar el repositorio): ejecuta `composer install` y deja el código como
está.

## 6 · Si usabas el bundle para crear proyectos sin red

davgen ya no distribuye `_laravel.zip` / `_react.zip` (traían `vendor/` y
`node_modules/` de terceros). Los proyectos nuevos se crean con `composer` y
`npm`. Para conservar la creación rápida y sin red en tu equipo:

```powershell
.\scripts\empaquetar-plantillas.ps1     # deja ~\.davgen\_laravel.zip
```
