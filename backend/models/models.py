import uuid
import enum
import secrets
import string
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Date, Numeric,
    ForeignKey, Enum, LargeBinary, JSON, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Computed

from backend.database import Base


def _generar_codigo_finca():
    """Genera un código único de 6 caracteres para la finca."""
    chars = string.ascii_uppercase + string.digits
    return "FIN-" + "".join(secrets.choice(chars) for _ in range(5))


class TipoEventoEnum(str, enum.Enum):
    nacimiento = "nacimiento"
    vacunacion = "vacunacion"
    desparacitacion = "desparacitacion"
    traslado = "traslado"
    cambio_propietario = "cambio_propietario"
    certificacion_sanitaria = "certificacion_sanitaria"
    muerte = "muerte"
    venta = "venta"
    auditoria = "auditoria"


class ResultadoEnum(str, enum.Enum):
    exitoso = "exitoso"
    rechazado = "rechazado"
    error = "error"


class Finca(Base):
    __tablename__ = "fincas"

    id_finca = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(150), nullable=False)
    ubicacion = Column(String(300))
    descripcion = Column(Text)
    codigo_acceso = Column(String(10), nullable=False, unique=True, default=_generar_codigo_finca)
    propietario_id = Column(UUID(as_uuid=True), nullable=True)  # se llena después del registro
    activa = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    usuarios = relationship("User", back_populates="finca")
    animales = relationship("Animal", back_populates="finca")


class Role(Base):
    __tablename__ = "roles"

    id_roles = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(50), nullable=False, unique=True)
    descripcion = Column(Text)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    users = relationship("User", back_populates="rol")


class User(Base):
    __tablename__ = "users"

    id_users = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rol_id = Column(UUID(as_uuid=True), ForeignKey("roles.id_roles", ondelete="RESTRICT"), nullable=False)
    finca_id = Column(UUID(as_uuid=True), ForeignKey("fincas.id_finca", ondelete="RESTRICT"), nullable=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    contrasena_hash = Column(Text, nullable=False)
    telefono = Column(String(20))
    numero_senasa = Column(String(50), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    rol = relationship("Role", back_populates="users")
    finca = relationship("Finca", back_populates="usuarios")
    plantilla_biometrica = relationship("PlantillaBiometrica", back_populates="user", uselist=False)
    animales = relationship("Animal", back_populates="propietario")
    eventos = relationship("EventoGanadero", back_populates="actor")
    validaciones = relationship("ValidacionBiometrica", back_populates="user")
    bitacoras = relationship("BitacoraSistema", back_populates="user")


class PlantillaBiometrica(Base):
    __tablename__ = "plantillas_biometricas"

    id_bio = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_users = Column(UUID(as_uuid=True), ForeignKey("users.id_users", ondelete="CASCADE"), nullable=False, unique=True)
    firma_manuscrita = Column(LargeBinary, nullable=False)
    vector_facial = Column(LargeBinary, nullable=False)
    patron_voz = Column(LargeBinary, nullable=False)
    algoritmo_firma = Column(String(50), nullable=False, default="DTW")
    algoritmo_facial = Column(String(50), nullable=False, default="FaceNet")
    algoritmo_voz = Column(String(50), nullable=False, default="MFCC")
    registrado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="plantilla_biometrica")


class Animal(Base):
    __tablename__ = "animales"

    id_animales = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finca_id = Column(UUID(as_uuid=True), ForeignKey("fincas.id_finca", ondelete="RESTRICT"), nullable=True)
    propietario_id = Column(UUID(as_uuid=True), ForeignKey("users.id_users"), nullable=False)
    codigo_unico = Column(String(50), nullable=False, unique=True)
    especie = Column(String(60), nullable=False)
    raza = Column(String(60))
    nombre = Column(String(60))
    fecha_nacimiento = Column(Date)
    sexo = Column(String(1))
    peso_kg = Column(Numeric(8, 2))
    color = Column(String(50))
    marcas = Column(Text)
    madre_id = Column(UUID(as_uuid=True), ForeignKey("animales.id_animales"), nullable=True)
    padre_id = Column(UUID(as_uuid=True), ForeignKey("animales.id_animales"), nullable=True)
    es_inseminada = Column(Boolean, nullable=False, default=False)
    activo = Column(Boolean, nullable=False, default=True)
    registrado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("sexo IN ('M', 'H', 'I')", name="chk_sexo"),
    )

    propietario = relationship("User", back_populates="animales")
    finca = relationship("Finca", back_populates="animales")
    eventos = relationship("EventoGanadero", back_populates="animal")
    madre = relationship("Animal", foreign_keys=[madre_id], remote_side=[id_animales], backref="hijos_como_madre")
    padre = relationship("Animal", foreign_keys=[padre_id], remote_side=[id_animales], backref="hijos_como_padre")


class EventoGanadero(Base):
    __tablename__ = "eventos_ganaderos"

    id_eventos = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_animales = Column(UUID(as_uuid=True), ForeignKey("animales.id_animales", ondelete="RESTRICT"), nullable=False)
    id_actor = Column(UUID(as_uuid=True), ForeignKey("users.id_users", ondelete="RESTRICT"), nullable=False)
    tipo_evento = Column(Enum(TipoEventoEnum, name="tipo_evento_enum", create_type=False), nullable=False)
    datos_evento = Column(JSON, nullable=False)
    ubicacion = Column(String(200))
    hash_evento = Column(String(64), nullable=False, unique=True)
    hash_evento_pasado = Column(String(64))
    firma_digital = Column(Text, nullable=False, default="ECDSA-SHA256")
    clave_publica_pem = Column(Text, nullable=True)
    registrado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("hash_evento ~ '^[a-f0-9]{64}$'", name="chk_hash_formato"),
        CheckConstraint(
            "hash_evento_pasado IS NULL OR hash_evento_pasado ~ '^[a-f0-9]{64}$'",
            name="chk_hash_evento_pasado"
        ),
    )

    animal = relationship("Animal", back_populates="eventos")
    actor = relationship("User", back_populates="eventos")
    validacion = relationship("ValidacionBiometrica", back_populates="evento", uselist=False)


class CodigoCambioBiometrico(Base):
    """Códigos temporales de verificación para cambiar credenciales biométricas."""
    __tablename__ = "codigos_cambio_biometrico"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_users = Column(UUID(as_uuid=True), ForeignKey("users.id_users", ondelete="CASCADE"), nullable=False)
    codigo = Column(String(6), nullable=False)
    tipo_credencial = Column(String(10), nullable=False)  # "firma", "rostro", "voz"
    usado = Column(Boolean, nullable=False, default=False)
    expira_en = Column(DateTime, nullable=False)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User")


class ValidacionBiometrica(Base):
    __tablename__ = "validaciones_biometricas"

    id_valbio = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_user = Column(UUID(as_uuid=True), ForeignKey("users.id_users", ondelete="RESTRICT"), nullable=False)
    id_eventos = Column(UUID(as_uuid=True), ForeignKey("eventos_ganaderos.id_eventos", ondelete="CASCADE"), nullable=False)
    firma_ok = Column(Boolean, nullable=False, default=False)
    rostro_ok = Column(Boolean, nullable=False, default=False)
    voz_ok = Column(Boolean, nullable=False, default=False)
    score_firma = Column(Numeric(5, 4))
    score_rostro = Column(Numeric(5, 4))
    score_voz = Column(Numeric(5, 4))
    aprobado = Column(Boolean, Computed("firma_ok AND rostro_ok AND voz_ok", persisted=True))
    validado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="validaciones")
    evento = relationship("EventoGanadero", back_populates="validacion")


class BitacoraSistema(Base):
    __tablename__ = "bitacora_sistema"

    id_bitacora = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_user = Column(UUID(as_uuid=True), ForeignKey("users.id_users", ondelete="SET NULL"))
    accion = Column(String(200), nullable=False)
    resultado = Column(Enum(ResultadoEnum, name="resultado_enum", create_type=False), nullable=False)
    ip_origen = Column(INET)
    detalle = Column(JSON)
    ocurrido_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="bitacoras")
