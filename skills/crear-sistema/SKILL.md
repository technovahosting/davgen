---
name: crear-sistema
description: Crea un sistema web completo (base de datos MySQL, API en Laravel y aplicación React con inicio de sesión, roles y una pantalla de altas, bajas y cambios por cada tabla) a partir de una descripción en palabras o de un mockup HTML, usando el generador davgen. Usar cuando alguien pida "crear un sistema", "hacer un CRUD", "generar el backend y el frontend", "un sistema de inventario / ventas / biblioteca / notas", un proyecto de curso con Laravel y React, o cuando mencione davgen, _configtotal.ini o un mockup para generar código. Use when the user wants to scaffold a full-stack CRUD system (Laravel + React + MySQL) from a description or an HTML mockup.
---

# davgen — de una idea a un sistema funcionando

davgen es un generador: lee un **mockup HTML** (o una base MySQL que ya existe) y
escribe el SQL, la API en Laravel, la aplicación React y las pruebas. Tu trabajo
con esta skill es acompañar a la persona desde «quiero un sistema de…» hasta
verlo funcionando, sin que tenga que saber cómo funciona davgen.

Quien te escribe suele ser **estudiante**: explica cada paso en una línea antes
de hacerlo, usa palabras simples (di «tabla» y «pantalla», no «entidad» ni
«scaffolding») y muestra el comando que ejecutas para que pueda repetirlo.
Responde en español salvo que te escriban en otro idioma.

## Paso 0 · ¿Está instalado davgen?

Ejecuta `davgen --version`. Si responde, sigue al paso 1.

Si no existe, instálalo con el primer origen que encuentres, avisando antes qué
vas a instalar (necesita Python 3.10 o superior; `python --version`):

1. **Esta misma carpeta trae el código.** Busca un `pyproject.toml` en
   `fuente/` (junto a este archivo) o dos carpetas más arriba de este archivo
   (`../../pyproject.toml`). Si está: `python -m pip install "<esa carpeta>"`.
2. Si no: `python -m pip install davgen`.

Si `davgen` queda instalado pero la terminal no lo encuentra, úsalo como
`python -m davgen` en todos los comandos. Si falta Python, indica cómo
instalarlo (python.org, marcando «Add to PATH» en Windows) y detente ahí.

## Paso 1 · Entender qué sistema quiere

Si ya te dio un mockup HTML o una descripción clara, no preguntes de más.
Si solo dijo «un sistema de ventas», pregunta **una sola vez** y como máximo:

- ¿Qué cosas va a registrar? (productos, clientes, ventas…)
- ¿Qué datos importan de cada una?
- ¿Cómo se llama el sistema?

Con eso propón las tablas en un cuadro (tabla · campos · con qué se relaciona) y
espera un «sí» antes de seguir. Entre 3 y 8 tablas es un buen primer sistema: si
pide veinte, sugiere empezar por las centrales y agregar el resto después
(regenerar es seguro).

No incluyas usuarios, roles, permisos ni inicio de sesión: davgen ya los trae.

## Paso 2 · Crear el proyecto y el mockup

```bash
davgen nuevo mi-sistema      # crea la carpeta con todo ordenado
```

1. Escribe el mockup en `mi-sistema/01-Mockups/index.html` siguiendo
   **[referencias/mockup.md](referencias/mockup.md)** — léelo antes de escribir:
   davgen deduce las tablas de la *estructura* del HTML y hay reglas que, si se
   rompen, hacen que una tabla o un campo desaparezca sin aviso. Un mockup
   completo de muestra: [ejemplos/biblioteca.html](ejemplos/biblioteca.html).
2. En `mi-sistema/_configtotal.ini` completa solo esto:

```ini
[proyecto]
nombre = Biblioteca del barrio
modulo = bib              ; 2 a 6 letras: las tablas se llamarán tbl_bib_*

[entrada]
tipo = mockup
mockup = 01-Mockups/index.html
```

3. **La contraseña del administrador la elige la persona.** davgen no trae
   ninguna y sin ella no genera. Pídele que abra
   `mi-sistema/_acceso.desarrollo.ini` y escriba la suya en
   `[seguridad] admin_password` (mínimo 8 caracteres, con letras y números, y
   que no sea una que ya use en otro sitio). Con ella entrará al sistema la
   primera vez. No la elijas tú ni le pidas que te la diga: espera a que
   confirme que la escribió.

## Paso 3 · Generar (sin base de datos todavía)

Desde la carpeta del proyecto:

```bash
davgen generar --listar     # solo muestra las tablas que entendió: revísalas
davgen generar --local      # escribe todo el código; no toca BD ni internet
```

Compara lo que lista `--listar` con el cuadro del paso 1. Si falta una tabla o
un campo, el problema está en el mockup: corrígelo y repite. No sigas con
tablas faltantes.

El resultado queda en `03-Backend/_backendGenerado/`. Muéstrale a la persona
qué se creó y para qué sirve cada parte, en este orden:

| Carpeta | Qué es |
|---|---|
| `database/` | Los `.sql`: tablas, vistas y procedimientos |
| `backend/` | La API en Laravel (rutas, controladores, servicios) |
| `frontend/` | La aplicación React (pantallas y conexión con la API) |
| `RESUMEN.md` | El detalle de todo lo generado |

**Este es un buen punto para detenerse** si solo quería el código o no tiene
MySQL instalado. Pregunta si quiere verlo funcionando.

## Paso 4 · Verlo funcionando en su computadora

Sigue **[referencias/ejecutar-en-local.md](referencias/ejecutar-en-local.md)**
(requisitos, base de datos, levantar la API y la aplicación, primer ingreso).

## Después: cambios, código propio y publicar

- **Agregar una tabla o un campo:** editar el mockup y volver a generar.
- **Lógica propia del negocio, pantallas a medida, publicar en un hosting:**
  [referencias/codigo-propio-y-publicar.md](referencias/codigo-propio-y-publicar.md).
- **Algo falla:** `davgen doctor` (qué falta en el equipo) y
  `davgen doctor --conexiones` (por qué no conecta la base). Todos los comandos:
  `davgen --help`.

## Reglas que no se rompen

1. **Las contraseñas las escribe la persona, no tú.** Los accesos van en
   `_acceso.desarrollo.ini` y `_acceso.produccion.ini`. Pídele que los complete
   en su editor; no le pidas que te las pegue en el chat, no las muestres y no
   leas esos archivos en voz alta. La contraseña inicial del administrador la
   escribe la persona en `_acceso.desarrollo.ini` → `[seguridad]
   admin_password`: nunca la inventes, la sugieras ni la imprimas.
2. **Nunca publiques por tu cuenta.** `--entorno produccion` escribe en la base
   real y sube archivos al hosting: solo si la persona lo pide con esas
   palabras, y confirmando antes a dónde va.
3. **No edites archivos con la cabecera `@generated davgen`.** Se reescriben al
   generar y el cambio se pierde. Lo propio va aparte (ver la referencia).
4. **Antes de `davgen seguridad` o `davgen generar` contra una base, di qué
   base es** (host y nombre) y espera el visto bueno. `--local` no necesita
   permiso: no sale de la carpeta.
5. **No inventes opciones.** Si dudas de un comando o una clave del `.ini`,
   consulta `davgen <comando> --help` o los comentarios del propio
   `_configtotal.ini`, que explican cada valor.
