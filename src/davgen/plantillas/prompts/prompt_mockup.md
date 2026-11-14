# Prompt — crear el mockup .html del sistema (fase 1)

> Uso: pegar este prompt en la IA junto con los requisitos del sistema
> (00-Requisitos). Guardar el resultado como un solo .html en 01-Mockups\
> y apuntarlo en _configtotal.ini ([entrada] tipo=mockup, mockup=...).
> davgen parsea este HTML para derivar las entidades del sistema.

---

# Rol
Eres un diseñador UX. A partir de los requisitos que te proporciono al
final, genera UN SOLO archivo .html autocontenido (CSS embebido, sin
frameworks ni JavaScript obligatorio) con el mockup de todas las pantallas
CRUD del sistema. El archivo será PARSEADO por un generador de código, por
lo que la estructura es OBLIGATORIA.

# Estructura OBLIGATORIA (el generador deriva las entidades de aquí)
1. Una sección por ENTIDAD del negocio, encabezada por un `<h2>` con el
   nombre de la entidad en ESPAÑOL y SINGULAR (ej: `<h2>Producto</h2>`).
2. Debajo del título, un `<form>` con los campos de la entidad:
   - `name` en snake_case, singular, en español (ej: `precio_unitario`).
     El `id` puede llevar prefijo `entidad-campo`; el generador lo limpia.
   - Tipo HTML correcto: `text`, `number`, `date`, `email`, `checkbox`,
     `<textarea>` para descripciones largas.
   - Referencias a OTRA entidad: `<select name="{entidad}_id">` (ej:
     `cliente_id`) con 2-3 `<option>` de ejemplo.
   - Catálogos fijos (estado, tipo, categoría): `<select>` con sus
     opciones literales.
3. Después del formulario, un `<table>` de listado con un `<th>` por
   columna visible.

# PROHIBICIONES
- NO crear pantallas de login, usuarios, roles, permisos ni parámetros:
  el sistema de seguridad ya existe y se genera aparte.
- NO usar `name="buscar"`, `search`, `filtro`, `q` en campos de datos
  (el generador los ignora; resérvalos para cajas de búsqueda).
- NO poner campos `id`, `activo`, `created_at`, `updated_at`: son
  estándar y los agrega el generador.

# Formato de salida
Entrega ÚNICAMENTE el archivo HTML completo, estético (CSS embebido,
paleta sobria), con datos de ejemplo realistas en los listados.

# Requisitos del sistema
{pegar aquí los requisitos / casos de uso}
