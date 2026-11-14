# Plantillas

Cada archivo que davgen escribe sale de una plantilla. Hasta la versión 4 esas
plantillas eran texto incrustado en el código Python del generador: para
cambiar una coma de una página generada había que modificar davgen y volver a
compilarlo. Desde la versión 5 son **archivos** en `src/davgen/plantillas/`, y
cualquier proyecto puede reemplazar las que quiera.

## Personalizar una plantilla

```bash
davgen plantillas listar
davgen plantillas copiar frontend/pagina.jsx
```

Eso crea `_plantillas/frontend/pagina.jsx` en la raíz de tu proyecto. Edítala y
vuelve a ejecutar `davgen generar`.

**Regla de resolución** — para cada plantilla, davgen usa:

1. `{raíz del proyecto}/_plantillas/<grupo>/<archivo>`, si existe;
2. si no, la del paquete.

Al generar, la consola dice cuántas plantillas propias se están usando.
Un archivo en `_plantillas/` cuyo nombre no coincide con ninguna plantilla se
avisa (suele ser un nombre mal escrito) y se ignora. `davgen plantillas listar`
marca las que tienes personalizadas.

`_plantillas/` se versiona con tu proyecto: es parte de él.

## Grupos

| Grupo | Qué produce |
|---|---|
| `backend/` | PHP de Laravel: controllers, services, middleware, utilidades |
| `frontend/` | `api.js`, `authService.js`, `App.jsx`, páginas CRUD |
| `google/` | Botón de Google y panel de solicitudes de acceso |
| `componentes/` | Hooks y componentes React reutilizables (extra) |
| `sql/` | Script de seguridad (`tbl_seg_*`) y sus guías |
| `pruebas/` | Piezas de las pruebas PHPUnit |
| `despliegue/` | Extractor del zip en el servidor, «siguientes pasos» |
| `documentos/` | Guías y plantillas de documentos del proyecto |
| `prompts/` | Prompts de IA por fase |
| `proyecto/` | `_configtotal.ini`, `.gitignore` y guía de un proyecto nuevo |

## Marcadores

El motor es deliberadamente simple: sustitución de texto. Hay dos estilos y
cada plantilla usa uno solo — basta mirar la plantilla original para saber cuál:

- **`__NOMBRE__`** (la mayoría del PHP y JSX): se reemplaza tal cual. Las llaves
  `{ }` del lenguaje se escriben normales.

  ```php
  class __CTRL_CLASS__ extends BaseController
  {
      protected string $view = '__VISTA__';
  ```

- **`{nombre}`** (SQL, Markdown, `.ini`): formato de Python. Una llave literal
  se escribe doble: `{{` y `}}`.

Quitar un marcador no rompe nada (ese dato simplemente no aparece). Inventar
uno nuevo no hace nada: los datos disponibles los decide el código del
generador.

## Límites actuales

- Las partes con lógica por columna (las rutas, el cuerpo de los `pcru*`, el
  service JS por tabla, los archivos de prueba) todavía se arman en Python y
  **no** son plantillas reemplazables. Moverlas es trabajo pendiente.
- Al actualizar davgen, una plantilla propia sigue siendo la tuya: no recibe
  las mejoras de la plantilla original. Tras actualizar, compara:

  ```bash
  davgen plantillas copiar frontend/pagina.jsx --forzar   # ¡pisa la tuya!
  git diff _plantillas/                                   # y fusiona a mano
  ```

  Por eso conviene personalizar pocas plantillas y mantenerlas en git.

## Para quien desarrolla davgen

- Una plantilla nueva se agrega como archivo y se carga con
  `_plantilla('grupo/archivo.ext', __name__, 'NOMBRE_DE_LA_CONSTANTE')`. Los dos
  últimos argumentos registran quién la usa, para poder recargar ese módulo
  cuando un proyecto la reemplaza.
- Las plantillas se guardan con finales de línea LF (`.gitattributes` lo fuerza
  y una prueba lo comprueba).
- Cambiar una plantilla cambia lo que reciben todos los proyectos al
  regenerar: va al `CHANGELOG.md`, y si altera un contrato (rutas, firma de un
  SP, nombres de archivos) es un cambio de versión MAYOR.
