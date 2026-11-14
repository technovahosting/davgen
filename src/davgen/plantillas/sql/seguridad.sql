-- =============================================================================
-- 01_seguridad.sql — Módulo de seguridad davgen v4.0 — {fecha}
-- Usuarios, tokens Sanctum, verificación en dos pasos (correo/app), archivos
-- por usuario y CONFIGURACIÓN DE ACCESO (roles, módulos, permisos, parámetros,
-- bitácora). Idempotente: re-ejecutar NUNCA pisa lo administrado en la BD.
-- =============================================================================
SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE TABLE IF NOT EXISTS `tbl_seg_usuario` (
  `id`                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `nombre`              VARCHAR(150)    NOT NULL,
  `email`               VARCHAR(191)    NOT NULL,
  `email_verificado_en` TIMESTAMP       NULL DEFAULT NULL,
  `password`            VARCHAR(255)    NOT NULL,
  `rol`                 VARCHAR(50)     NOT NULL DEFAULT 'usuario'
                        COMMENT 'nombre del rol — ver tbl_seg_rol',
  `metodo_2fa`          ENUM('ninguno','correo','app') NOT NULL DEFAULT 'ninguno',
  `totp_secret`         VARCHAR(64)     NULL COMMENT 'secreto base32 TOTP',
  `activo`              TINYINT(1)      NOT NULL DEFAULT 1,
  `remember_token`      VARCHAR(100)    DEFAULT NULL,
  `created_at`          TIMESTAMP       NULL DEFAULT NULL,
  `updated_at`          TIMESTAMP       NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_seg_usuario_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Usuarios del sistema con rol, estado y 2FA';

CREATE TABLE IF NOT EXISTS `personal_access_tokens` (
  `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tokenable_type` VARCHAR(255)    NOT NULL,
  `tokenable_id`   BIGINT UNSIGNED NOT NULL,
  `name`           VARCHAR(255)    NOT NULL,
  `token`          VARCHAR(64)     NOT NULL,
  `abilities`      TEXT            DEFAULT NULL,
  `last_used_at`   TIMESTAMP       NULL DEFAULT NULL,
  `expires_at`     TIMESTAMP       NULL DEFAULT NULL,
  `created_at`     TIMESTAMP       NULL DEFAULT NULL,
  `updated_at`     TIMESTAMP       NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_pat_token` (`token`),
  KEY `idx_pat_tokenable` (`tokenable_type`, `tokenable_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Tokens API de Laravel Sanctum';

CREATE TABLE IF NOT EXISTS `tbl_seg_token_reset` (
  `email`      VARCHAR(191) NOT NULL,
  `token`      VARCHAR(255) NOT NULL,
  `created_at` TIMESTAMP    NULL DEFAULT NULL,
  PRIMARY KEY (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Tokens de recuperación de contraseña';

CREATE TABLE IF NOT EXISTS `tbl_seg_codigo_verificacion` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `usuario_id`  BIGINT UNSIGNED NOT NULL,
  `codigo`      VARCHAR(255)    NOT NULL COMMENT 'hash sha256 del código',
  `proposito`   ENUM('login','activacion') NOT NULL DEFAULT 'login',
  `expira_en`   TIMESTAMP       NOT NULL,
  `usado`       TINYINT(1)      NOT NULL DEFAULT 0,
  `created_at`  TIMESTAMP       NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_seg_codigo_usuario` (`usuario_id`, `proposito`, `usado`),
  CONSTRAINT `fk_seg_codigo_usuario`
    FOREIGN KEY (`usuario_id`) REFERENCES `tbl_seg_usuario` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Códigos temporales de verificación 2FA por correo';

CREATE TABLE IF NOT EXISTS `tbl_seg_archivo` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `usuario_id`      BIGINT UNSIGNED NOT NULL,
  `nombre_original` VARCHAR(255)    NOT NULL,
  `ruta`            VARCHAR(500)    NOT NULL COMMENT 'ruta en storage/app',
  `mime`            VARCHAR(100)    NOT NULL,
  `extension`       VARCHAR(10)     NOT NULL,
  `tamanio_kb`      INT UNSIGNED    NOT NULL DEFAULT 0,
  `descripcion`     VARCHAR(255)    NULL,
  `activo`          TINYINT(1)      NOT NULL DEFAULT 1,
  `created_at`      TIMESTAMP       NULL DEFAULT NULL,
  `updated_at`      TIMESTAMP       NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_seg_archivo_usuario` (`usuario_id`, `activo`),
  CONSTRAINT `fk_seg_archivo_usuario`
    FOREIGN KEY (`usuario_id`) REFERENCES `tbl_seg_usuario` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Archivos subidos por usuario (PDF, imágenes, documentos)';

-- =============================================================================
-- CONFIGURACIÓN DE ACCESO — la administración de la aplicación se hace AQUÍ,
-- en la BD, nunca editando el código generado.
-- =============================================================================
CREATE TABLE IF NOT EXISTS `tbl_seg_rol` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `nombre`      VARCHAR(50)     NOT NULL,
  `descripcion` VARCHAR(255)    NULL,
  `es_admin`    TINYINT(1)      NOT NULL DEFAULT 0
                COMMENT 'acceso total: ignora tbl_seg_permiso',
  `activo`      TINYINT(1)      NOT NULL DEFAULT 1,
  `created_at`  TIMESTAMP       NULL DEFAULT NULL,
  `updated_at`  TIMESTAMP       NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_seg_rol_nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Roles del sistema (agregar filas para nuevos roles)';

CREATE TABLE IF NOT EXISTS `tbl_seg_modulo` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `clave`      VARCHAR(100)    NOT NULL
               COMMENT 'tabla de negocio o módulo del sistema',
  `titulo`     VARCHAR(100)    NOT NULL,
  `icono`      VARCHAR(50)     NULL,
  `orden`      INT UNSIGNED    NOT NULL DEFAULT 0,
  `tipo`       ENUM('negocio','sistema') NOT NULL DEFAULT 'negocio',
  `visible`    TINYINT(1)      NOT NULL DEFAULT 1 COMMENT 'aparece en el menú',
  `activo`     TINYINT(1)      NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP       NULL DEFAULT NULL,
  `updated_at` TIMESTAMP       NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_seg_modulo_clave` (`clave`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Módulos del portal: título, orden y visibilidad del menú';

CREATE TABLE IF NOT EXISTS `tbl_seg_permiso` (
  `rol_id`     BIGINT UNSIGNED NOT NULL,
  `modulo_id`  BIGINT UNSIGNED NOT NULL,
  `sel`        TINYINT(1)      NOT NULL DEFAULT 0,
  `get`        TINYINT(1)      NOT NULL DEFAULT 0,
  `add`        TINYINT(1)      NOT NULL DEFAULT 0,
  `upd`        TINYINT(1)      NOT NULL DEFAULT 0,
  `del`        TINYINT(1)      NOT NULL DEFAULT 0,
  `updated_at` TIMESTAMP       NULL DEFAULT NULL,
  PRIMARY KEY (`rol_id`, `modulo_id`),
  CONSTRAINT `fk_seg_permiso_rol`
    FOREIGN KEY (`rol_id`) REFERENCES `tbl_seg_rol` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_seg_permiso_modulo`
    FOREIGN KEY (`modulo_id`) REFERENCES `tbl_seg_modulo` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Permisos por rol × módulo × operación (sel/get/add/upd/del)';

CREATE TABLE IF NOT EXISTS `tbl_seg_parametro` (
  `clave`       VARCHAR(100) NOT NULL,
  `valor`       VARCHAR(500) NOT NULL,
  `tipo`        ENUM('texto','numero','booleano','lista') NOT NULL DEFAULT 'texto',
  `descripcion` VARCHAR(255) NULL,
  `activo`      TINYINT(1)   NOT NULL DEFAULT 1,
  `updated_at`  TIMESTAMP    NULL DEFAULT NULL,
  PRIMARY KEY (`clave`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Parámetros de la aplicación en runtime (editar el valor aquí)';

CREATE TABLE IF NOT EXISTS `tbl_seg_bitacora` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `usuario_id` BIGINT UNSIGNED NOT NULL,
  `modulo`     VARCHAR(100)    NOT NULL,
  `operacion`  VARCHAR(20)     NOT NULL COMMENT 'login, add, upd, del',
  `detalle`    VARCHAR(500)    NULL,
  `ip`         VARCHAR(45)     NULL,
  `created_at` TIMESTAMP       NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_seg_bitacora_usuario` (`usuario_id`, `created_at`),
  CONSTRAINT `fk_seg_bitacora_usuario`
    FOREIGN KEY (`usuario_id`) REFERENCES `tbl_seg_usuario` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Auditoría: logins y operaciones de escritura por usuario';

-- ── Migración idempotente: rol ENUM (v4.0) → VARCHAR(50) ─────────────────────
DELIMITER //
DROP PROCEDURE IF EXISTS `seg_migrar_v41`//
CREATE PROCEDURE `seg_migrar_v41`()
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.COLUMNS
             WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tbl_seg_usuario'
               AND COLUMN_NAME = 'rol' AND DATA_TYPE = 'enum') THEN
    ALTER TABLE `tbl_seg_usuario`
      MODIFY `rol` VARCHAR(50) NOT NULL DEFAULT 'usuario'
      COMMENT 'nombre del rol — ver tbl_seg_rol';
  END IF;
END//
DELIMITER ;
CALL `seg_migrar_v41`();
DROP PROCEDURE `seg_migrar_v41`;

-- ── Vistas seg (sin columnas sensibles) ──────────────────────────────────────
CREATE OR REPLACE VIEW `vis_seg_usuario` AS
SELECT u.id, u.nombre, u.email, u.rol, u.metodo_2fa, u.activo,
       u.email_verificado_en, u.created_at, u.updated_at
FROM `tbl_seg_usuario` u;

CREATE OR REPLACE VIEW `vis_seg_archivo` AS
SELECT a.id, a.usuario_id, u.nombre AS usuario_nombre,
       a.nombre_original, a.mime, a.extension, a.tamanio_kb,
       a.descripcion, a.activo, a.created_at
FROM `tbl_seg_archivo` a
JOIN `tbl_seg_usuario` u ON u.id = a.usuario_id;

CREATE OR REPLACE VIEW `vis_seg_rol` AS
SELECT r.id, r.nombre, r.descripcion, r.es_admin, r.activo,
       r.created_at, r.updated_at
FROM `tbl_seg_rol` r;

CREATE OR REPLACE VIEW `vis_seg_modulo` AS
SELECT m.id, m.clave, m.titulo, m.icono, m.orden, m.tipo, m.visible,
       m.activo, m.created_at, m.updated_at
FROM `tbl_seg_modulo` m;

CREATE OR REPLACE VIEW `vis_seg_permiso` AS
SELECT p.rol_id, r.nombre AS rol_nombre, p.modulo_id,
       m.clave AS modulo_clave, m.titulo AS modulo_titulo, m.tipo AS modulo_tipo,
       p.`sel`, p.`get`, p.`add`, p.`upd`, p.`del`, p.updated_at
FROM `tbl_seg_permiso` p
JOIN `tbl_seg_rol` r    ON r.id = p.rol_id
JOIN `tbl_seg_modulo` m ON m.id = p.modulo_id;

CREATE OR REPLACE VIEW `vis_seg_parametro` AS
SELECT p.clave, p.valor, p.tipo, p.descripcion, p.activo, p.updated_at
FROM `tbl_seg_parametro` p;

CREATE OR REPLACE VIEW `vis_seg_bitacora` AS
SELECT b.id, b.usuario_id, u.nombre AS usuario_nombre, u.email AS usuario_email,
       b.modulo, b.operacion, b.detalle, b.ip, b.created_at
FROM `tbl_seg_bitacora` b
JOIN `tbl_seg_usuario` u ON u.id = b.usuario_id;

-- ── Solicitudes de acceso (cola de aprobación para logins Google nuevos) ─────
CREATE TABLE IF NOT EXISTS `tbl_seg_acceso_solicitud` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `email`        VARCHAR(190) NOT NULL,
  `nombre`       VARCHAR(190) NULL,
  `estado`       ENUM('pendiente','aprobada','denegada') NOT NULL DEFAULT 'pendiente',
  `rol`          VARCHAR(50)  NOT NULL DEFAULT 'cliente',
  `origen`       VARCHAR(20)  NOT NULL DEFAULT 'google',
  `resuelto_por` BIGINT UNSIGNED NULL,
  `resuelto_at`  TIMESTAMP NULL,
  `activo`       TINYINT(1) NOT NULL DEFAULT 1,
  `created_at`   TIMESTAMP NULL,
  `updated_at`   TIMESTAMP NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_acceso_email` (`email`),
  KEY `idx_acceso_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE OR REPLACE VIEW `vis_seg_acceso_solicitud` AS
SELECT s.id, s.email, s.nombre, s.estado, s.rol, s.origen,
       s.resuelto_por, u.nombre AS resuelto_por_nombre, s.resuelto_at,
       s.activo, s.created_at, s.updated_at
FROM `tbl_seg_acceso_solicitud` s
LEFT JOIN `tbl_seg_usuario` u ON u.id = s.resuelto_por;

-- =============================================================================
-- SEEDS — INSERT IGNORE por clave única: regenerar agrega lo nuevo y
-- CONSERVA todo lo que el administrador haya ajustado en la BD.
-- =============================================================================

-- ── Roles iniciales ───────────────────────────────────────────────────────────
INSERT IGNORE INTO `tbl_seg_rol` (`nombre`, `descripcion`, `es_admin`, `activo`, `created_at`)
VALUES
  ('admin',   'Administrador del sistema (acceso total)', 1, 1, NOW()),
  ('usuario', 'Usuario estándar (solo lectura inicial)',  0, 1, NOW()),
  ('cliente', 'Cliente externo (acceso solo con Google)', 0, 1, NOW());

-- ── Módulos del sistema ───────────────────────────────────────────────────────
INSERT IGNORE INTO `tbl_seg_modulo` (`clave`, `titulo`, `tipo`, `orden`, `created_at`)
VALUES
  ('archivos',       'Mis archivos',   'sistema', 900, NOW()),
  ('seguridad',      'Seguridad (2FA)','sistema', 910, NOW()),
  ('accesos',        'Solicitudes de acceso', 'sistema', 915, NOW()),
  ('administracion', 'Administración', 'sistema', 920, NOW());

-- ── Módulos de negocio (uno por tabla generada) ──────────────────────────────
{seed_modulos}

-- ── Permisos iniciales ────────────────────────────────────────────────────────
-- admin: todo sobre todo (cubre módulos nuevos en cada regeneración)
INSERT IGNORE INTO `tbl_seg_permiso`
  (`rol_id`, `modulo_id`, `sel`, `get`, `add`, `upd`, `del`)
SELECT r.id, m.id, 1, 1, 1, 1, 1
FROM `tbl_seg_rol` r CROSS JOIN `tbl_seg_modulo` m
WHERE r.nombre = 'admin';

-- usuario: solo lectura sobre negocio
INSERT IGNORE INTO `tbl_seg_permiso`
  (`rol_id`, `modulo_id`, `sel`, `get`, `add`, `upd`, `del`)
SELECT r.id, m.id, 1, 1, 0, 0, 0
FROM `tbl_seg_rol` r CROSS JOIN `tbl_seg_modulo` m
WHERE r.nombre = 'usuario' AND m.tipo = 'negocio';

-- usuario: autoservicio completo en archivos y seguridad (2FA propia)
INSERT IGNORE INTO `tbl_seg_permiso`
  (`rol_id`, `modulo_id`, `sel`, `get`, `add`, `upd`, `del`)
SELECT r.id, m.id, 1, 1, 1, 1, 1
FROM `tbl_seg_rol` r CROSS JOIN `tbl_seg_modulo` m
WHERE r.nombre = 'usuario' AND m.clave IN ('archivos', 'seguridad');

-- ── Parámetros de la aplicación (editar `valor` directamente en la BD) ───────
INSERT IGNORE INTO `tbl_seg_parametro` (`clave`, `valor`, `tipo`, `descripcion`)
VALUES
  ('max_archivo_mb',      '{max_mb}',      'numero',   'Tamaño máximo de archivo subido (MB)'),
  ('extensiones_archivo', '{extensiones}', 'lista',    'Extensiones permitidas, separadas por coma'),
  ('2fa_obligatorio',     '0',             'booleano', 'Exigir verificación en dos pasos a todos (1=sí)'),
  ('codigo_2fa_minutos',  '10',            'numero',   'Vigencia del código 2FA por correo (minutos)'),
  ('sesion_unica',        '1',             'booleano', 'Un solo token activo por usuario (1=sí)'),
  ('bitacora_activa',     '1',             'booleano', 'Registrar logins y escrituras en la bitácora (1=sí)'),
  ('google_auth_activo',  '{google_activo}', 'booleano', 'Habilitar inicio de sesión con Google (1=sí)'),
  ('google_client_id',    '{google_client_id}', 'texto', 'Client ID OAuth de Google (audiencia del ID token)'),
  ('google_dominios_permitidos', '{google_dominios}', 'lista', 'Dominios Gmail auto-aceptados al entrar con Google (coma) — el resto va a cola de aprobacion'),
  ('roles_solo_google',   '{roles_solo_google}', 'lista', 'Roles que SOLO entran con Google (se les rechaza login por contraseña)'),
  ('rate_limit_auth',     '5',             'numero',   'Máx. intentos por minuto e IP en login/verificar/google (anti fuerza bruta y DoS)'),
  ('rate_limit_publico',  '60',            'numero',   'Máx. peticiones por minuto e IP en las rutas públicas de negocio (sin token)'),
  ('sesion_minutos',      '720',           'numero',   'Minutos que dura una sesión antes de pedir login de nuevo (0 = no vence)'),
  ('rate_limit_api',      '120',           'numero',   'Máx. peticiones por minuto y usuario en las rutas con token (anti DoS)'),
  ('retencion_bitacora_dias', '{retencion_dias}', 'numero', 'Días que se conserva la bitácora antes de borrarse sola (0 = no se borra)');

-- ── Usuario administrador inicial (contraseña inicial: admin_password del .ini) ──
-- ON DUPLICATE KEY UPDATE: regenerar RECONCILIA correo/nombre/rol del admin
-- (NO la contraseña, para no pisar la que el admin haya cambiado).
INSERT INTO `tbl_seg_usuario`
  (`id`, `nombre`, `email`, `password`, `rol`, `activo`, `created_at`)
VALUES
  (1, '{admin_nombre}', '{admin_email}', '{hash_admin}', 'admin', 1, NOW())
ON DUPLICATE KEY UPDATE
  `nombre` = VALUES(`nombre`), `email` = VALUES(`email`),
  `rol`    = VALUES(`rol`),    `activo` = VALUES(`activo`);

-- ── Owner (cuenta Google dueña, opcional [seguridad] owner_email) ────────────
-- Sembrado como admin verificado: puede entrar con Google desde el inicio y
-- aprobar/denegar el acceso de otros correos. Sin password (solo Google).
{owner_seed}
