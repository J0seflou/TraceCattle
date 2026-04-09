-- ═══════════════════════════════════════════════════════════════
-- MIGRACIÓN: Mejoras Trace Cattle
-- Ejecutar sobre la base de datos existente para aplicar cambios
-- ═══════════════════════════════════════════════════════════════

-- 1. Agregar campos de trazabilidad genealógica a la tabla animales
ALTER TABLE animales ADD COLUMN IF NOT EXISTS madre_id UUID REFERENCES animales(id_animales);
ALTER TABLE animales ADD COLUMN IF NOT EXISTS padre_id UUID REFERENCES animales(id_animales);
ALTER TABLE animales ADD COLUMN IF NOT EXISTS es_inseminada BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Agregar clave pública PEM a eventos para validación criptográfica
ALTER TABLE eventos_ganaderos ADD COLUMN IF NOT EXISTS clave_publica_pem TEXT;

-- 3. Corregir typo en nombre de columna (validad_en → validado_en)
ALTER TABLE validaciones_biometricas RENAME COLUMN validad_en TO validado_en;

-- 4. Corregir constraint UNIQUE en especie (no debería ser unique)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'animales_especie_key'
        OR conname = 'animales_especie_unique'
    ) THEN
        ALTER TABLE animales DROP CONSTRAINT IF EXISTS animales_especie_key;
        ALTER TABLE animales DROP CONSTRAINT IF EXISTS animales_especie_unique;
        RAISE NOTICE 'Constraint UNIQUE en especie eliminado correctamente.';
    ELSE
        RAISE NOTICE 'No se encontró constraint UNIQUE en especie (ya estaba correcto).';
    END IF;
END $$;

-- 5. Crear índices para los nuevos campos
CREATE INDEX IF NOT EXISTS idx_animales_madre ON animales(madre_id);
CREATE INDEX IF NOT EXISTS idx_animales_padre ON animales(padre_id);

-- 6. Verificación
DO $$
BEGIN
    RAISE NOTICE '══════════════════════════════════════════';
    RAISE NOTICE 'Migración completada exitosamente.';
    RAISE NOTICE '══════════════════════════════════════════';
END $$;
