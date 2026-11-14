# Usar davgen conversando con Claude (la skill «crear-sistema»)

Una *skill* le enseña a Claude a usar una herramienta. Con esta instalada, basta
escribir en español lo que se quiere:

> Quiero un sistema para la biblioteca de mi colegio: libros, socios y préstamos.

y Claude propone las tablas, escribe el mockup, ejecuta davgen y acompaña hasta
ver el sistema funcionando, explicando cada paso. No hace falta saber de
antemano cómo se usa davgen.

## Qué se necesita

| | |
|---|---|
| **Claude Code** | La aplicación de Anthropic para programar con Claude (terminal, escritorio o VS Code) |
| **Python 3.10 o superior** | `python --version` lo confirma. En Windows, al instalarlo marcar «Add to PATH» |
| Para *ejecutar* el sistema generado | PHP 8.2+, Composer, Node.js y MySQL (Laragon o XAMPP los traen). Para solo *generar el código*, no hacen falta |

No hay que instalar davgen aparte: la skill lo instala la primera vez, desde su
propia carpeta, avisando antes.

## Instalar — opción A (recomendada): como plugin

Dentro de Claude Code, escribir estas dos líneas:

```text
/plugin marketplace add technovahosting/davgen
/plugin install davgen@davgen
```

Las actualizaciones llegan con `/plugin update`.

## Instalar — opción B: descargar el .zip

Sirve si no se quiere usar el catálogo de plugins, o sin conexión a GitHub
desde Claude Code.

1. Descargar `crear-sistema.zip` de la página de *Releases* del repositorio
   (<https://github.com/technovahosting/davgen/releases>).
2. Descomprimirlo de modo que quede la carpeta:
   - Windows: `C:\Users\<tu-usuario>\.claude\skills\crear-sistema\`
   - Linux y macOS: `~/.claude/skills/crear-sistema/`
3. Cerrar y volver a abrir Claude Code.

Dentro de esa carpeta tiene que verse directamente el archivo `SKILL.md`. Si
quedó `crear-sistema\crear-sistema\SKILL.md`, sobra un nivel: subir el contenido.

El mismo `.zip` se puede subir en la aplicación de Claude (Configuración →
Skills). Ahí Claude trabaja en un espacio aislado: puede escribir el mockup y
generar el código, pero no levantar el sistema ni usar una base de datos.

## Comprobar que quedó instalada

En Claude Code, escribir `/` y buscar **crear-sistema** en la lista (instalada
como plugin aparece como `davgen:crear-sistema`). O simplemente preguntar:

> ¿Tienes la skill para crear sistemas con davgen?

## Primer uso: un sistema en diez minutos

1. Crear una carpeta vacía para los proyectos y abrir Claude Code ahí.
2. Pedir el sistema con palabras propias. Tres ejemplos que funcionan bien:

   > Crea un sistema de inventario para una ferretería: productos, categorías y
   > proveedores.

   > Tengo este mockup en `mockup.html`. Genera el sistema completo.

   > Necesito un sistema de notas para un colegio. No sé por dónde empezar.

3. Claude muestra las tablas que propone. Revisarlas y responder «sí» o pedir
   cambios.
4. Claude genera el código y explica qué hay en cada carpeta.
5. Si se quiere verlo funcionando, decirlo: Claude guía la instalación de lo que
   falte, la base de datos y el primer ingreso.

## Lo que la skill nunca hace

- **No pide contraseñas por el chat.** Los accesos a la base se escriben en un
  archivo del proyecto (`_acceso.desarrollo.ini`), que no se sube a git.
- **No publica nada en internet** si no se le pide expresamente.
- **No toca lo que no generó.**
- **No elige tu contraseña de administrador**: la escribes tú en un archivo del
  proyecto. davgen no trae ninguna de fábrica.

Y lo que te toca a ti: lo que escribes en la conversación lo procesa Claude
según los términos de Anthropic, así que no pegues contraseñas ni datos reales
de personas; y el sistema que resulte es tuyo y tu responsabilidad. Ver
[DESCARGO.md](../DESCARGO.md).

## Preguntas frecuentes

**¿Tiene costo?** davgen y la skill son gratuitos y de código abierto (MIT).
Claude Code requiere una cuenta de Claude.

**¿El código generado es mío?** Sí, sin condiciones. No queda ninguna
dependencia de davgen en el sistema.

**¿Puedo presentarlo como trabajo de curso?** Eso lo decide cada docente. Lo
honesto es decir qué generó la herramienta y qué se escribió a mano; la skill
ayuda a distinguirlo.

**¿Y si ya tengo la base de datos hecha?** También sirve: decirle a Claude que
el sistema debe salir de la base existente.

**Claude dice que no encuentra `davgen`.** Pedirle «instala davgen desde la
carpeta de la skill». Si sigue sin aparecer, cerrar y abrir la terminal, o usar
`python -m davgen`.

**Algo falla al ejecutar el sistema.** Pedirle a Claude «ejecuta davgen doctor
y dime qué falta». Los casos más comunes están en
[solucion-de-problemas.md](solucion-de-problemas.md).

## Para quien mantiene davgen

- La skill vive en [`skills/crear-sistema/`](../skills/crear-sistema/SKILL.md);
  el plugin, en `.claude-plugin/`. El repositorio entero es el plugin.
- `python scripts/empaquetar_skill.py` arma `dist/crear-sistema.zip` (la skill
  más el código de davgen en `fuente/`). Se adjunta al Release; no se versiona.
- `claude plugin validate .` revisa los manifiestos.
  `claude --plugin-dir .` carga el plugin en una sesión sin instalarlo.
- `tests/test_skill.py` comprueba que cada comando, opción y clave del `.ini`
  que enseña la skill existe de verdad, y que el recorrido completo funciona.
  Al cambiar un comando de davgen, esa prueba avisa si la skill quedó atrás.
- La versión de `.claude-plugin/plugin.json` debe coincidir con `VERSION`.
