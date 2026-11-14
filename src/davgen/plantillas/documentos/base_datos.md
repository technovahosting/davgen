# Base de datos — (nombre del proyecto)

> PLANTILLA davgen · fase 2 — las tablas de NEGOCIO las crea el usuario
> (generarlas con `_prompts\prompt-2-tablas-desde-mockup.md`); las de
> seguridad (`tbl_seg_*`) las trae `00-seguridad.sql`. Reglas completas
> en `readme_cero.md` (generado por davgen en esta carpeta).

## 1. Estándar (resumen davgen)

- Tablas `tbl_{modulo}_{entidad}` (singular, snake_case) + vista `vis_*`.
- Columnas estándar: `id` (PK), `activo` (baja lógica), `created_at`,
  `updated_at`. FKs `{entidad}_id` con `ON DELETE RESTRICT`.
- NUNCA crear tablas de usuarios/roles/permisos/tokens (ya existen).

## 2. Modelo entidad-relación

(Pegar aquí el diagrama: imagen, mermaid o enlace.)

## 3. Diccionario de datos

| Tabla | Columna | Tipo | Descripción / regla |
|---|---|---|---|
| (tbl_xxx_entidad) | (columna) | (tipo) | (completar) |

## 4. Operaciones de negocio (SPs `pag_*`)

| SP | Regla que implementa |
|---|---|
| (ej: pag_ven_pedido_confirmar) | (validaciones y cambios que hace) |

(Generarlos con `_prompts\prompt-3-sp-dominio.md`.)
