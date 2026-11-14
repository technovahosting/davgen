# Cómo escribir el mockup para davgen

El mockup es **un archivo HTML simple**. davgen no mira el diseño: mira la
estructura, y de ella saca las tablas. Si la estructura es correcta, el sistema
sale completo; si no, faltan tablas o campos y davgen no siempre avisa.

## La forma que davgen entiende

```html
<section>
  <h2>Productos</h2>                                   <!-- una TABLA -->
  <form>
    <label>Nombre</label>      <input type="text"   name="nombre" required>
    <label>Precio</label>      <input type="number" name="precio" step="0.01">
    <label>Categoría</label>   <input type="number" name="categoria_id">
    <label>Estado</label>
    <select name="estado">
      <option>Seleccione…</option>
      <option>Disponible</option><option>Agotado</option>
    </select>
    <label>Descripción</label> <textarea name="descripcion"></textarea>
  </form>
</section>
```

| En el HTML | Lo que davgen crea |
|---|---|
| `<h2>` seguido de un `<form>` | Una tabla `tbl_{modulo}_{nombre}` con su pantalla |
| Cada campo con `name` | Una columna |
| `type="number"` | Entero; con `step="0.01"`, decimal |
| `type="date"`, `email`, `tel`, `checkbox` | Fecha, texto, texto, sí/no |
| `<textarea>` | Texto largo |
| `<select>` con opciones escritas | Lista fija de valores (ENUM) |
| Un campo llamado `algo_id` | Relación con la tabla `algo` |

## Reglas

1. **Un `<h2>` por tabla**, y el formulario inmediatamente debajo. El título
   puede ir en plural («Productos»): davgen lo pasa a singular.
2. **Todo campo lleva `name`**, en minúsculas, sin acentos ni espacios, con
   guion bajo: `fecha_ingreso`, `precio_unitario`.
3. **Mínimo dos campos por tabla.** Un formulario con un solo campo se ignora.
4. **Relaciones:** el campo se llama como la otra tabla en singular más `_id`
   (`cliente_id` apunta a «Clientes»). La tabla apuntada debe existir en el
   mismo mockup.
5. **No pongas** `id`, `activo`, `created_at` ni `updated_at`: davgen los agrega
   en todas las tablas.
6. **No pongas** pantallas de usuarios, roles, permisos ni inicio de sesión:
   ya vienen incluidas.
7. **Nombres reservados para buscadores:** `buscar`, `busqueda`, `search`,
   `filtro`, `filter` y `q` se ignoran. No los uses para datos.
8. La primera opción de un `<select>` puede ser «Seleccione…»: se descarta sola.

## Límites que conviene saber antes

Estos son comportamientos reales de la versión actual. Diseña el mockup para
esquivarlos y avísale a la persona cuando alguno le afecte.

| Límite | Qué hacer |
|---|---|
| Un `<select>` de lista fija admite **hasta 10 opciones**; las demás se pierden sin aviso | Si hay más de 10 (países, ciudades), que sea una tabla aparte y un campo `_id` |
| **Todos los campos salen obligatorios** en la base | No pongas en el mockup campos que casi nunca se llenan; o ajusta después la columna con `ALTER TABLE … NULL` y vuelve a generar |
| Un campo `_id` es siempre obligatorio | Si la relación es opcional, modela distinto (por ejemplo, un registro «Ninguno» en la tabla apuntada) |
| `<input type="file">` se ignora | Los archivos se manejan con el módulo de archivos incluido o con código propio |
| Una `<table>` sola (sin formulario) bajo un `<h3>` no crea tabla | Usa siempre `<h2>` + `<form>` |

## Comprobar el mockup

```bash
davgen generar --listar
```

Lista las tablas y columnas que entendió, sin escribir nada. Debe coincidir con
lo que se acordó con la persona. Si no coincide, casi siempre es por la regla 1,
2 o 3.

## Consejos para un buen primer sistema

- Empieza por los **catálogos** (categorías, clientes) y luego lo que los usa
  (productos, ventas): así las relaciones `_id` siempre encuentran su tabla.
- Agrega debajo de cada formulario una `<table>` con una o dos filas de ejemplo.
  No cambia lo generado, pero el mockup se entiende al abrirlo en el navegador
  y sirve para mostrárselo a quien pidió el sistema.
- Guarda el archivo en UTF-8 y con `<html lang="es">`.
