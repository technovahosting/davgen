# Prompt — crear stored procedures de DOMINIO (operaciones de negocio)

> Uso: para operaciones que van más allá del CRUD (confirmar un pedido,
> cambiar de estado, cancelar…). Los SPs CRUD `pcru*` ya los genera davgen:
> aquí solo se crean los de NEGOCIO. Pegar el prompt en la IA junto con la
> regla de negocio y el script de las tablas involucradas.

---

# Rol
Eres un desarrollador MySQL senior. Genera stored procedures de DOMINIO
para la operación de negocio que te describo al final, siguiendo los
estándares del proyecto (generador davgen).

# Estándares OBLIGATORIOS
- Nombre: `pag_{tabla sin tbl_}_{operacion}` (ej: `pag___MODULO___pedido_confirmar`).
- Parámetros: prefijo `p` + columna (ej: `ppedido_id`, `pusuario_id`).
- Idempotente: `DROP PROCEDURE IF EXISTS` antes de cada `CREATE`, con
  `DELIMITER $$ … $$ DELIMITER ;`.
- Validaciones PRIMERO; cada error de negocio se reporta con:
  `SIGNAL SQLSTATE '45000' SET MYSQL_ERRNO = 1644,
   MESSAGE_TEXT = '<mensaje claro en español para el usuario final>';`
  (el backend muestra EXACTAMENTE ese texto al usuario).
- Escrituras dentro de `START TRANSACTION … COMMIT` con
  `DECLARE EXIT HANDLER FOR SQLEXCEPTION` que haga `ROLLBACK` y `RESIGNAL`.
- Toda actualización fija `updated_at = NOW()`; NUNCA `DELETE` físico
  (usar `activo = 0` o un estado).
- Si la entidad tiene tabla de historial (`*_historial`), registrar ahí
  cada cambio de estado con el usuario y la fecha.
- Comentar el SP con la regla de negocio que implementa.

# Formato de salida
Entrega ÚNICAMENTE el script SQL (sin explicación), en español.

# Operación de negocio
{describir aquí la regla: tabla(s), condición, qué cambia, qué se valida}

# Tablas involucradas
```sql
{pegar aquí los CREATE TABLE relevantes}
```
