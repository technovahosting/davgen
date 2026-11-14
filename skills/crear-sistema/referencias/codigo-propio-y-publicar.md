# Cambios, código propio y publicación

## Cambiar el sistema

| Se quiere | Cómo |
|---|---|
| Otra tabla u otro campo | Editar el mockup, ejecutar en la base el cambio (`CREATE TABLE` / `ALTER TABLE … ADD COLUMN … AFTER …`) y `davgen generar` |
| Quitar una tabla del sistema | `[opciones] excluir = tbl_x` en `_configtotal.ini` |
| Una pantalla de solo consulta | `[opciones] solo_consulta = tbl_x` |
| Un listado visible sin iniciar sesión | `[opciones] publico = tbl_x:sel,get` |
| Desplegables en vez de números en los campos `_id` | `[generar] componentes_react = si` |
| Validaciones, pruebas, exportar a CSV, documentación de la API | Las opciones `form_requests`, `tests`, `export`, `openapi` de `[generar]` |
| Roles, permisos y menú | Se administran en las tablas `tbl_seg_*` de la base, sin tocar código |

Cuando el sistema ya tiene su base de datos, la base manda: se puede cambiar
`[entrada] tipo = bd` y davgen lee las tablas reales en vez del mockup.

Regenerar es seguro: davgen reescribe solo sus propios archivos.

## Dónde va el código propio

Los archivos generados llevan la cabecera `@generated davgen` y **no se editan**
(el cambio se pierde al regenerar; `davgen verificar` avisa si alguien lo hizo).
Lo propio del negocio va en lugares que davgen nunca toca:

| Qué | Dónde |
|---|---|
| Rutas propias de la API | `routes/Custom/*.php` — se cargan solas bajo `/api` |
| Controladores y servicios propios | `app/**/Custom/` — pueden extender los generados |
| Procedimientos de la base | Con prefijo `pag_{modulo}_` (davgen solo toca los `pcru*`) |
| Pantallas propias | `src/pages/` (fuera de `generados/`) y `src/components/` |
| El menú y el armazón de la aplicación | `src/App.jsx` — davgen lo escribe una sola vez |
| Cambiar cómo se ven **todas** las pantallas generadas | `davgen plantillas copiar frontend/pagina.jsx` y editar la copia |

Dos cosas que sorprenden al llamar la API a mano:

- Los parámetros llevan una `p` delante: `pnombre`, `pprecio`.
- Actualizar reemplaza el registro entero: hay que enviar todos los campos.

## Publicar en un hosting

Solo cuando la persona lo pida expresamente. Publicar escribe en la base real y
sube archivos a su sitio.

1. La persona completa `_acceso.produccion.ini` (base y FTP del hosting, la
   dirección con `https://` y **su** contraseña de administrador para ese
   entorno, distinta de la de desarrollo). El servidor necesita PHP 8.2 o
   superior.
2. Completar `[legal]` en `_configtotal.ini` (quién responde por los datos,
   contacto, país, dónde se alojan) y repasar con la persona la lista de
   `src/components/generados/LEEME-LEGAL.md`. Los textos de privacidad y
   términos son un punto de partida: **no los presentes como asesoría legal**
   ni afirmes que cumplen una ley; recomienda que los revise un abogado, sobre
   todo si el sistema guarda datos de salud, de menores o financieros.
3. `davgen doctor --conexiones --entorno produccion` comprueba que todo responde.
4. En `_configtotal.ini`: `[generar] produccion = si` (la API) y `front = si`
   (la aplicación).
5. Muéstrale a dónde se va a publicar y espera su confirmación. Entonces:

   ```bash
   davgen generar --entorno produccion
   ```

davgen deja protegida la carpeta publicada y lo comprueba desde afuera al
terminar. Si prefiere no dejar las contraseñas en texto plano:
`davgen acceso cifrar` (el token lo elige y lo escribe la persona; nunca tú).

## Para entregar un trabajo de curso

- `RESUMEN.md` en `03-Backend/_backendGenerado/` lista todo lo generado: sirve
  de base para el informe.
- `05-Testing/generados/` trae una colección de Postman y un `api.http` para
  mostrar la API funcionando.
- `leeme.html` (en la raíz del proyecto) es una guía que se abre con doble clic.
- Antes de subir el proyecto a GitHub: los archivos `_acceso.*.ini` ya están en
  `.gitignore`. No quitarlos de ahí.
- Decir con honestidad qué generó la herramienta y qué se escribió a mano: lo
  propio es lo que está fuera de las carpetas `generados/` y de los archivos
  con la cabecera `@generated`.
