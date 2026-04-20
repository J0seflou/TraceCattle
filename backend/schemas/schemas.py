from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


# ── Fincas ──

class FincaCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    ubicacion: Optional[str] = Field(None, max_length=300)
    descripcion: Optional[str] = None


class FincaResponse(BaseModel):
    id_finca: UUID
    nombre: str
    ubicacion: Optional[str] = None
    descripcion: Optional[str] = None
    codigo_acceso: str
    activa: bool
    creado_en: datetime
    total_usuarios: Optional[int] = None
    total_animales: Optional[int] = None

    model_config = {"from_attributes": True}


# ── Auth ──

class UserCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    contrasena: str = Field(..., min_length=6)
    telefono: Optional[str] = None
    rol_nombre: str = Field(..., description="Nombre del rol: ganadero, veterinario, transportista, auditor")
    # Para ganaderos: datos de la finca nueva
    finca_nombre: Optional[str] = Field(None, max_length=150)
    finca_ubicacion: Optional[str] = Field(None, max_length=300)
    # Para otros roles: código de acceso a una finca existente
    codigo_finca: Optional[str] = Field(None, max_length=10)
    # Para auditores: carné de identificación SENASA
    carnet_senasa: Optional[str] = Field(None, max_length=30, description="Carné SENASA obligatorio para registrarse como auditor")


class UserLogin(BaseModel):
    email: EmailStr
    contrasena: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id_users: UUID
    nombre: str
    apellido: str
    email: str
    telefono: Optional[str] = None
    rol_nombre: str
    activo: bool
    creado_en: datetime
    finca: Optional[FincaResponse] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None


# ── Animales ──

class AnimalCreate(BaseModel):
    codigo_unico: str = Field(..., min_length=1, max_length=50)
    especie: str = Field(..., min_length=1, max_length=60)
    raza: str = Field(..., min_length=1, max_length=60)
    nombre: str = Field(..., min_length=1, max_length=60)
    fecha_nacimiento: date = Field(..., description="Fecha de nacimiento obligatoria")
    sexo: str = Field(..., pattern="^[MHI]$", description="M=Macho, H=Hembra, I=Indefinido")
    peso_kg: Decimal = Field(..., gt=0, description="Peso en kg obligatorio")
    color: str = Field(..., min_length=1, max_length=50)
    marcas: Optional[str] = None
    madre_id: Optional[UUID] = None
    padre_id: Optional[UUID] = None
    es_inseminada: Optional[bool] = False
    info_pajilla: Optional[str] = None
    origen_desconocido: Optional[bool] = False

    @model_validator(mode="after")
    def validar_trazabilidad_genealogica(self) -> "AnimalCreate":
        if not self.origen_desconocido:
            if self.madre_id is None and self.padre_id is None and not self.es_inseminada:
                raise ValueError(
                    "La trazabilidad genealógica es obligatoria: indique la madre, el padre, "
                    "si es inseminada, o marque 'Origen desconocido'."
                )
        return self


class AnimalUpdate(BaseModel):
    especie: Optional[str] = None
    raza: Optional[str] = None
    nombre: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[str] = Field(None, pattern="^[MHI]$")
    peso_kg: Optional[Decimal] = None
    color: Optional[str] = None
    marcas: Optional[str] = None
    madre_id: Optional[UUID] = None
    padre_id: Optional[UUID] = None
    es_inseminada: Optional[bool] = None
    info_pajilla: Optional[str] = None
    origen_desconocido: Optional[bool] = None
    activo: Optional[bool] = None


class AnimalResponse(BaseModel):
    id_animales: UUID
    codigo_unico: str
    especie: str
    raza: Optional[str] = None
    nombre: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[str] = None
    peso_kg: Optional[Decimal] = None
    color: Optional[str] = None
    marcas: Optional[str] = None
    madre_id: Optional[UUID] = None
    padre_id: Optional[UUID] = None
    madre_nombre: Optional[str] = None
    padre_nombre: Optional[str] = None
    es_inseminada: bool = False
    info_pajilla: Optional[str] = None
    origen_desconocido: bool = False
    hermanos: Optional[list] = None
    propietario_nombre: Optional[str] = None
    activo: bool
    registrado_en: datetime

    model_config = {"from_attributes": True}


# ── Eventos ──

class EventoCreate(BaseModel):
    id_animales: UUID
    tipo_evento: str
    datos_evento: dict
    ubicacion: Optional[str] = None
    # Datos biométricos en base64
    firma_imagen: str = Field(..., description="Imagen de firma en base64")
    rostro_imagen: str = Field(..., description="Foto del rostro en base64")
    audio_voz: str = Field(..., description="Audio de voz en base64 (WAV)")


class EventoResponse(BaseModel):
    id_eventos: UUID
    id_animales: UUID
    tipo_evento: str
    datos_evento: dict
    ubicacion: Optional[str] = None
    hash_evento: str
    hash_evento_pasado: Optional[str] = None
    firma_digital: str
    actor_nombre: Optional[str] = None
    registrado_en: datetime

    model_config = {"from_attributes": True}


# ── Biometría – cambio de credenciales ──

class SolicitarCambioRequest(BaseModel):
    tipo_credencial: str = Field(
        ...,
        description="Credencial a cambiar: 'firma', 'rostro' o 'voz'",
        pattern="^(firma|rostro|voz)$",
    )


class SolicitarCambioResponse(BaseModel):
    mensaje: str
    email_destino: str  # enmascarado, p.ej. "jo***@gmail.com"
    expira_minutos: int


# ── Biometría ──

class BiometricValidationResponse(BaseModel):
    firma_ok: bool
    rostro_ok: bool
    voz_ok: bool
    score_firma: float
    score_rostro: float
    score_voz: float
    aprobado: bool


class BiometricStatusResponse(BaseModel):
    registrado: bool
    algoritmo_firma: Optional[str] = None
    algoritmo_facial: Optional[str] = None
    algoritmo_voz: Optional[str] = None
    registrado_en: Optional[datetime] = None


class BiometricVerifyRequest(BaseModel):
    firma_imagen: str
    rostro_imagen: str
    audio_voz: str


# ── Validaciones ──

class ValidacionResponse(BaseModel):
    id_valbio: UUID
    id_user: UUID
    id_eventos: UUID
    firma_ok: bool
    rostro_ok: bool
    voz_ok: bool
    score_firma: Optional[float] = None
    score_rostro: Optional[float] = None
    score_voz: Optional[float] = None
    aprobado: bool
    validado_en: datetime

    model_config = {"from_attributes": True}


# ── Bitácora ──

class BitacoraResponse(BaseModel):
    id_bitacora: UUID
    id_user: Optional[UUID] = None
    usuario_nombre: Optional[str] = None
    accion: str
    resultado: str
    ip_origen: Optional[str] = None
    detalle: Optional[dict] = None
    ocurrido_en: datetime

    model_config = {"from_attributes": True}


# ── Auditoría ──

class IntegridadEventoResponse(BaseModel):
    posicion: int
    id_eventos: UUID
    tipo_evento: str
    hash_evento: str
    hash_esperado: Optional[str] = None
    cadena_integra: bool
    registrado_en: datetime


class AuditoriaAnimalResponse(BaseModel):
    animal: AnimalResponse
    total_eventos: int
    eventos: list[EventoResponse]
    integridad: list[IntegridadEventoResponse]
    cadena_completa_integra: bool


class AlertaBiometricaResponse(BaseModel):
    ocurrido_en: datetime
    usuario: str
    rol: str
    ip_origen: Optional[str] = None
    detalle: Optional[dict] = None


# ── Auditores Autorizados (SENASA) ──

class AuditorAutorizadoCreate(BaseModel):
    carnet_senasa: str = Field(..., min_length=3, max_length=30, description="Número de carné SENASA")
    nombre_completo: str = Field(..., min_length=3, max_length=200)


class AuditorAutorizadoResponse(BaseModel):
    id: UUID
    carnet_senasa: str
    nombre_completo: str
    activo: bool
    disponible: bool  # True si aún no tiene usuario registrado
    registrado_en: datetime

    model_config = {"from_attributes": True}


# Resolver referencia forward
TokenResponse.model_rebuild()
