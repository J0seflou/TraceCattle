-- ═══════════════════════════════════════════════════════════════════════════
-- SCRIPT DE LIMPIEZA Y RESET DE BASE DE DATOS — Trace Cattle
-- ═══════════════════════════════════════════════════════════════════════════
-- Qué hace este script:
--   1. Elimina TODOS los datos de la BD excepto el usuario Administrador.
--   2. Actualiza la contraseña del Administrador con hash bcrypt correcto.
--   3. Conserva los roles del sistema.
--
-- IMPORTANTE: Ejecutar con precaución. Esta operación es IRREVERSIBLE.
-- Requiere privilegios de escritura sobre la base de datos.
-- ═══════════════════════════════════════════════════════════════════════════

BEGIN;

-- ── 1. Limpiar bitácora del sistema ──────────────────────────────────────────
DELETE FROM bitacora_sistema;

-- ── 2. Limpiar códigos de cambio biométrico ──────────────────────────────────
DELETE FROM codigos_cambio_biometrico;

-- ── 3. Limpiar validaciones biométricas (depende de eventos) ─────────────────
DELETE FROM validaciones_biometricas;

-- ── 4. Limpiar eventos ganaderos ──────────────────────────────────────────────
DELETE FROM eventos_ganaderos;

-- ── 5. Limpiar animales ───────────────────────────────────────────────────────
-- Primero romper referencias genealógicas (madre/padre) para evitar FK conflict
UPDATE animales SET madre_id = NULL, padre_id = NULL;
DELETE FROM animales;

-- ── 6. Limpiar plantillas biométricas ────────────────────────────────────────
DELETE FROM plantillas_biometricas;

-- ── 7. Eliminar todos los usuarios que NO sean el Administrador ───────────────
DELETE FROM users
WHERE email != 'admin@tracecattle.com';

-- ── 8. Eliminar todas las fincas (el admin no tiene finca) ────────────────────
DELETE FROM fincas;

-- ── 9. Actualizar finca_id del admin a NULL (si quedó alguna referencia) ──────
UPDATE users
SET finca_id = NULL
WHERE email = 'admin@tracecattle.com';

-- ── 10. Actualizar contraseña del Administrador con hash bcrypt correcto ───────
--
-- Contraseña: Admin2024*
-- Hash generado con bcrypt (cost 12):
--
UPDATE users
SET
    contrasena_hash = '$2b$12$bkxJGK9LF0c.DgYeF7/23OHr1HhVyQS.kMq.pSE7okidnRA2f5OA.',
    nombre          = 'Administrador',
    apellido        = 'Sistema',
    activo          = TRUE,
    actualizado_en  = NOW()
WHERE email = 'admin@tracecattle.com';

-- ── 11. Asegurarse de que el rol admin existe ──────────────────────────────────
INSERT INTO roles (nombre, descripcion)
VALUES ('admin', 'Administrador del sistema con acceso total.')
ON CONFLICT (nombre) DO NOTHING;

-- ── 12. Verificar estado final ────────────────────────────────────────────────
DO $$
DECLARE
    v_admin_id   UUID;
    v_admin_rol  VARCHAR(50);
    v_total_users INT;
BEGIN
    SELECT u.id_users, r.nombre
    INTO   v_admin_id, v_admin_rol
    FROM   users u
    JOIN   roles r ON r.id_roles = u.rol_id
    WHERE  u.email = 'admin@tracecattle.com';

    SELECT COUNT(*) INTO v_total_users FROM users;

    RAISE NOTICE '═══════════════════════════════════════════════════';
    RAISE NOTICE 'Limpieza completada exitosamente.';
    RAISE NOTICE '───────────────────────────────────────────────────';
    RAISE NOTICE 'Total usuarios restantes : %', v_total_users;
    RAISE NOTICE 'Administrador ID         : %', v_admin_id;
    RAISE NOTICE 'Rol del Administrador    : %', v_admin_rol;
    RAISE NOTICE 'Email                    : admin@tracecattle.com';
    RAISE NOTICE 'Contraseña               : Admin2024*  (cambiar en producción)';
    RAISE NOTICE '═══════════════════════════════════════════════════';
END $$;

COMMIT;
