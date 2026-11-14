# Prompt — crear las tablas de negocio a partir de un mockup .html (fase 2)

> Uso: copiar todo el bloque siguiente en la IA y pegar el contenido del
> mockup .html al final. El script resultante se ejecuta en la BD ANTES de
> correr `davgen generar` (tipo=bd), que creará SPs, services,
> controllers, API y páginas para esas tablas.

---

# Rol
Eres un arquitecto de bases de datos MySQL. A partir del mockup HTML que te
proporciono al final, debes generar UN SOLO script SQL con las tablas de
negocio del sistema, siguiendo AL PIE DE LA LETRA los estándares del
proyecto (generador davgen). El script será ejecutado tal cual en una BD
MySQL existente.

# Parámetros
- Módulo: `__MODULO__`   (prefijo corto del proyecto)
- Entrada: el mockup .html al final de este prompt.

# Qué debes hacer
1. Analiza el mockup: cada formulario/listado representa una ENTIDAD.
   Deriva sus campos de los inputs, selects y columnas de tablas HTML.
2. Genera `CREATE TABLE` por entidad y su vista `vis_*` correspondiente.
3. Ordena las tablas por dependencias FK (las referenciadas primero).

# Estándares OBLIGATORIOS

## Nombres
- Tablas: `tbl___MODULO___{entidad}` — entidad en snake_case y SINGULAR.
- Vistas: `vis___MODULO___{entidad}` (una por tabla, mismo sufijo).
- Columnas en snake_case, en español.

## Columnas estándar (en TODAS las tablas, en este orden)
- `id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT` — PRIMARY KEY.
- …campos propios de la entidad…
- `activo TINYINT(1) NOT NULL DEFAULT 1` — baja lógica (nunca DELETE físico).
- `created_at TIMESTAMP NULL DEFAULT NULL`
- `updated_at TIMESTAMP NULL DEFAULT NULL`
  (sin triggers ni DEFAULT CURRENT_TIMESTAMP: los gestiona el SP del sistema)

## Tipos (inferir del campo del mockup)
- Referencia a otra entidad (select con opciones de otra entidad o campo
  `*_id`): `{entidad}_id BIGINT UNSIGNED NOT NULL` + FOREIGN KEY.
- `estado/tipo/categoria/metodo/rol` → `VARCHAR(50) NOT NULL`.
- Fechas → `DATE NULL` · fecha-hora → `DATETIME NULL` · hora → `TIME NULL`.
- Montos/precios → `DECIMAL(12,2) NOT NULL` · cantidades → `INT NOT NULL`.
- Textos cortos → `VARCHAR(150) NOT NULL` · descripciones/observaciones →
  `VARCHAR(500) NULL` o `TEXT NULL`.

## Claves e índices (con `{base}` = nombre de la tabla sin `tbl_`)
- `PRIMARY KEY (id)`
- `KEY idx_{base}_activo (activo)`
- Por cada columna `*_id`: `KEY idx_{base}_{columna}`
- Por cada FK: `CONSTRAINT fk_{base}_{entidad_destino}
  FOREIGN KEY ({columna}) REFERENCES {tabla_destino} (id) ON DELETE RESTRICT`

## Definición de tabla
- `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`
- `COMMENT='Entidad {entidad} — derivada del mockup'`
- Idempotente: `CREATE TABLE IF NOT EXISTS` y `CREATE OR REPLACE VIEW`.
- Encabezado del script: `SET NAMES utf8mb4;`

## Vistas `vis_*` (OBLIGATORIAS: la API lista desde ellas)
- `SELECT` de TODAS las columnas de la tabla (alias `t`).
- Por cada FK, `LEFT JOIN` a la tabla referenciada y agrega su columna
  etiqueta como `{entidad_destino}_{etiqueta}` (etiqueta = la primera que
  exista de: `nombre`, `titulo`, `concepto`, `codigo`, `descripcion`;
  si ninguna existe, `id`).

# PROHIBICIONES
- NO crear tablas de seguridad, autenticación o acceso (usuarios, roles,
  permisos, sesiones, tokens, logins, bitácora): ya existen como
  `tbl_seg_*` en la BD y NO se tocan.
- NO crear stored procedures, índices full-text ni triggers: los SPs
  `pcru*` los genera davgen al regenerar.
- NO usar plural en las entidades ni prefijos distintos de `tbl___MODULO___`.

# Formato de salida
Entrega ÚNICAMENTE el script SQL (sin explicación), con un comentario
`-- ── {tabla} ──` antes de cada CREATE TABLE y una sección
`-- ════════ VISTAS ════════` antes de las vistas, todo en español.

# Mockup
```html
{pegar aquí el contenido del .html}
```
