CREATE EXTENSION IF NOT EXISTS "pgcrypto";

drop type if exists tipo_evento_enum;
drop type if exists resultado_enum;

--Estos son los eventos ganaderos que reconoce el sistema
CREATE TYPE tipo_evento_enum AS ENUM (
'nacimiento',
'vacunacion',
'desparacitacion',
'traslado',
'cambio_propietario',
'certificacion_sanitaria',
'muerte',
'venta',
'auditoria'
);

--Resultados de operación que se registran en la bitácora
CREATE TYPE resultado_enum AS ENUM (
'exitoso',
'rechazado',
'error'
);

--Esta tabla define los tipos de actores autorizados en el sistema
--Cada rol determina los tipos de eventos que puede registrar
CREATE TABLE roles (
id_roles UUID PRIMARY KEY DEFAULT gen_random_uuid(),
nombre VARCHAR(50) NOT NULL UNIQUE,
descripcion TEXT,
creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);


--Estos son los roles base del sistema
INSERT INTO roles (nombre, descripcion) VALUES
('ganadero', 'Propietario de animales. Puede registrar nacimientos, ventas y cambios de propietario.'),
('veterinario', 'Profesional de salud animal. Puede registrar vacunaciones, desparacitaciones y certificaciones sanitarias.'),
('transportista', 'Responsable de traslados. Puede registrar movimientos de animales.'),
('auditor', 'Auditor del sistema. Puede consultar historiales y validar integridad criptográfica.');

--Users humanos con roles y credenciales. Las contraseñas se guardan como hashes
CREATE TABLE users (
id_users UUID PRIMARY KEY DEFAULT gen_random_uuid(),
rol_id UUID NOT NULL REFERENCES roles(id_roles) ON DELETE RESTRICT,
nombre VARCHAR(100) NOT NULL,
apellido VARCHAR(100) NOT NULL,
email VARCHAR(150) NOT NULL UNIQUE,
contrasena_hash TEXT NOT NULL,
telefono VARCHAR(20),
activo BOOLEAN NOT NULL DEFAULT TRUE,
creado_en TIMESTAMP NOT NULL DEFAULT NOW(),
actualizado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_rol ON users(rol_id);
CREATE INDEX idx_users_email ON users(email);

--Almacenamiento de biometría (firma, vector facial y patron de voz)
CREATE TABLE plantillas_biometricas (
id_bio UUID PRIMARY KEY DEFAULT gen_random_uuid(),
id_users UUID NOT NULL UNIQUE REFERENCES users(id_users) ON DELETE CASCADE,
firma_manuscrita BYTEA NOT NULL,
vector_facial BYTEA NOT NULL,
patron_voz BYTEA NOT NULL,
algoritmo_firma VARCHAR(50) NOT NULL DEFAULT 'DTW',
algoritmo_facial VARCHAR(50) NOT NULL DEFAULT 'FaceNet',
algoritmo_voz VARCHAR(50) NOT NULL DEFAULT 'MFCC',
registrado_en TIMESTAMP NOT NULL DEFAULT NOW(),
actualizado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_biometria_users ON plantillas_biometricas(id_users);

CREATE TABLE animales (
id_animales UUID PRIMARY KEY DEFAULT gen_random_uuid(),
propietario_id UUID NOT NULL REFERENCES users(id_users),
codigo_unico VARCHAR (50) NOT NULL UNIQUE,
especie VARCHAR(60) NOT NULL,
raza VARCHAR(60),
nombre VARCHAR(60),
fecha_nacimiento DATE,
sexo CHAR(1) CHECK (sexo IN ('M', 'H', 'I')),
peso_kg NUMERIC(8,2),
color VARCHAR(50),
marcas TEXT,
madre_id UUID REFERENCES animales(id_animales),
padre_id UUID REFERENCES animales(id_animales),
es_inseminada BOOLEAN NOT NULL DEFAULT FALSE,
activo BOOLEAN NOT NULL DEFAULT TRUE,
registrado_en TIMESTAMP NOT NULL DEFAULT NOW(),
actualizado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_animales_propietario ON animales(propietario_id);
CREATE INDEX idx_animales_codigo ON animales(codigo_unico);
CREATE INDEX idx_animales_especie ON animales(especie);

CREATE TABLE eventos_ganaderos (
id_eventos UUID PRIMARY KEY DEFAULT gen_random_uuid(),
id_animales UUID NOT NULL REFERENCES animales(id_animales) ON DELETE RESTRICT,
id_actor UUID NOT NULL REFERENCES users(id_users) ON DELETE RESTRICT,
tipo_evento tipo_evento_enum NOT NULL,
datos_evento JSONB NOT NULL,
ubicacion VARCHAR (200),
hash_evento VARCHAR (64) NOT NULL UNIQUE,
hash_evento_pasado VARCHAR(64),
firma_digital TEXT NOT NULL DEFAULT 'ECDSA-SHA256',
clave_publica_pem TEXT,
registrado_en TIMESTAMP NOT NULL DEFAULT NOW(),

CONSTRAINT chk_hash_formato
CHECK (hash_evento ~ '^[a-f0-9]{64}$'),

CONSTRAINT chk_hash_evento_pasado
CHECK (hash_evento_pasado IS NULL OR hash_evento_pasado ~ '^[a-f0-9]{64}$')
);

CREATE INDEX idx_eventos_animal ON eventos_ganaderos(id_animales);
CREATE INDEX idx_eventos_actor ON eventos_ganaderos(id_actor);
CREATE INDEX idx_eventos_tipo ON eventos_ganaderos(tipo_evento);
CREATE INDEX idx_eventos_fecha ON eventos_ganaderos(registrado_en);
CREATE INDEX idx_eventos_hash ON eventos_ganaderos(hash_evento);
CREATE INDEX idx_eventos_hash_prev ON eventos_ganaderos(hash_evento_pasado);

--Este es el índice GIN para buscar dentro del JSON de datos del evento
CREATE INDEX idx_eventos_datos_gin ON eventos_ganaderos USING GIN (datos_evento);

--Esta tabla registra las 3 llaves criptograficas, si las 3 llaves no se aprueban, el evento no se crea en la tabla de eventos_ganaderos
--Esta tabla funciona como evidencia de auditoría de autentivcación
CREATE TABLE validaciones_biometricas (
id_valbio UUID PRIMARY KEY DEFAULT gen_random_uuid(),
id_user UUID NOT NULL REFERENCES users(id_users) ON DELETE RESTRICT,
id_eventos UUID NOT NULL REFERENCES eventos_ganaderos(id_eventos) ON DELETE CASCADE,
firma_ok BOOLEAN NOT NULL DEFAULT FALSE, --llave 1
rostro_ok BOOLEAN NOT NULL DEFAULT FALSE, --llave 2
voz_ok BOOLEAN NOT NULL DEFAULT FALSE, --llave 3
score_firma NUMERIC(5,4),
score_rostro NUMERIC(5,4),
score_voz NUMERIC(5,4),
aprobado BOOLEAN NOT NULL GENERATED ALWAYS AS (firma_ok AND rostro_ok AND voz_ok) STORED,
validado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_validaciones_user ON validaciones_biometricas (id_user);
CREATE INDEX idx_validaciones_evento ON validaciones_biometricas (id_eventos);
CREATE INDEX idx_validaciones_aprobado ON validaciones_biometricas (aprobado);

CREATE TABLE bitacora_sistema (
id_bitacora UUID PRIMARY KEY DEFAULT gen_random_uuid(),
id_user UUID REFERENCES users(id_users) ON DELETE SET NULL,
accion VARCHAR(200) NOT NULL,
resultado resultado_enum NOT NULL,
ip_origen INET,
detalle JSONB,
ocurrido_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bitacora_usuario ON bitacora_sistema(id_user);
CREATE INDEX idx_bitacora_accionario ON bitacora_sistema(accion);
CREATE INDEX idx_bitacora_fecha ON bitacora_sistema(ocurrido_en);
CREATE INDEX idx_bitacora_gin ON bitacora_sistema USING GIN (detalle);

--Este es el historial completo de un animal + actor + validacion
CREATE OR REPLACE VIEW v_historial_animal AS SELECT
a.codigo_unico,
a.especie,
a.raza,
e.tipo_evento,
e.datos_evento,
e.ubicacion,
e.hash_evento,
e.hash_evento_pasado,
e.registrado_en,
u.nombre || ' ' || u.apellido AS actor,
r.nombre AS rol_actor,
v.firma_ok,
v.rostro_ok,
v.voz_ok,
v.aprobado AS biometria_aprobada
FROM eventos_ganaderos e 
JOIN animales a ON a.id_animales = e.id_animales
JOIN users u ON u.id_users = e.id_actor
JOIN roles r ON r.id_roles = u.rol_id
LEFT JOIN validaciones_biometricas v ON v.id_eventos = e.id_eventos
ORDER BY a.codigo_unico, e.registrado_en;

CREATE OR REPLACE VIEW v_resumen_animales AS SELECT
a.id_animales,
a.codigo_unico,
a.especie,
a.raza,
a.nombre,
u.nombre || ' ' || u.apellido AS propietario,
COUNT(e.id_eventos) AS total_eventos,
MAX(e.registrado_en) AS ultimo_evento_en
FROM animales a 
JOIN users u ON u.id_users = a.propietario_id
LEFT JOIN eventos_ganaderos e ON e.id_animales = a.id_animales
WHERE a.activo = TRUE
GROUP BY a.id_animales, a.codigo_unico, a.especie, a.raza, a.nombre, propietario;

CREATE OR REPLACE VIEW v_alertas_biometricas AS SELECT
b.ocurrido_en,
u.nombre || ' ' || u.apellido AS new_user,
r.nombre AS rol,
b.ip_origen,
b.detalle
FROM bitacora_sistema b
JOIN users u ON u.id_users = b.id_user
JOIN roles r ON r.id_roles = u.rol_id
WHERE b.accion = 'validacion_biometrica'
AND b.resultado = 'rechazado'
ORDER BY b.ocurrido_en DESC;

CREATE OR REPLACE FUNCTION verificar_integridad_animal(p_animal_id UUID)
RETURNS TABLE (
posicion INT,
id_eventos UUID,
tipo_evento tipo_evento_enum,
hash_evento VARCHAR(64),
hash_esperado VARCHAR(64),
cadena_integra BOOLEAN,
registrado_en TIMESTAMP
) AS $$
DECLARE 
rec RECORD;
hash_pasado VARCHAR(64) := NULL;
pos INT := 1;
BEGIN 
FOR rec IN 
SELECT e.id_eventos, e.tipo_evento, e.hash_evento, hash_evento_pasado, e.registrado_en
FROM eventos_ganaderos e
WHERE e.id_animales = p_animal_id
ORDER BY e.registrado_en ASC
LOOP
posicion := pos;
id_eventos := rec.id_eventos;
tipo_evento := rec.tipo_evento;
hash_evento := rec.hash_evento;
hash_esperado := hash_anterior;
cadena_integra := (rec.hash_evento_pasado IS NOT DISTINCT FROM hash_pasado);
registrado_en := rec.registrado_en;

RETURN NEXT;

hash_pasado := rec.hash_evento;
pos := pos + 1;
END LOOP;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION rol_puede_registrar(
p_rol_nombre VARCHAR,
p_tipo_evento tipo_evento_enum
) RETURNS BOOLEAN AS $$
BEGIN
RETURN CASE p_rol_nombre
WHEN 'ganadero' THEN
p_tipo_evento IN ('nacimiento', 'cambio_propietario', 'venta', 'muerte')
WHEN 'veterinario' THEN
p_tipo_evento IN ('vacunacion', 'desparacitacion', 'certificacion_sanitaria', 'muerte')
WHEN 'transportista' THEN
p_tipo_evento IN ('traslado')
WHEN 'auditor' THEN 
p_tipo_evento IN ('auditoria')
ELSE FALSE
END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION proteger_eventos()
RETURNS TRIGGER AS $$
BEGIN
RAISE EXCEPTION 'Los eventos ganaderos son inmutables. No se permite modificar ni eliminar registros existentes.';
RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_proteger_eventos
BEFORE UPDATE OR DELETE ON eventos_ganaderos
FOR EACH ROW EXECUTE FUNCTION proteger_eventos();

CREATE OR REPLACE FUNCTION actualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
NEW.actualizado_en = NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ts_users
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp();

CREATE TRIGGER trg_ts_animales
BEFORE UPDATE ON animales
FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp();

CREATE TRIGGER trg_ts_biometria
BEFORE UPDATE ON plantillas_biometricas
FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp();
