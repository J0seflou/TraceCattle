"""
Servicio criptográfico: SHA-256 hashing, ECDSA signing, encadenamiento de eventos.
"""
import hashlib
import json
from datetime import datetime
from uuid import UUID

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
from cryptography.exceptions import InvalidSignature

from sqlalchemy.orm import Session
from backend.models.models import EventoGanadero


def generate_event_hash(
    animal_id: UUID,
    actor_id: UUID,
    tipo_evento: str,
    datos_evento: dict,
    timestamp: datetime,
    hash_anterior: str | None = None,
) -> str:
    """Genera hash SHA-256 del evento concatenando todos los campos relevantes."""
    payload = (
        f"{str(animal_id)}|"
        f"{str(actor_id)}|"
        f"{tipo_evento}|"
        f"{json.dumps(datos_evento, sort_keys=True, default=str)}|"
        f"{timestamp.isoformat()}|"
        f"{hash_anterior or 'GENESIS'}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_ecdsa_keys() -> tuple[bytes, bytes]:
    """Genera un par de claves ECDSA (privada, pública) en formato PEM."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def sign_event(private_key_pem: bytes, hash_evento: str) -> str:
    """Firma un hash de evento con la clave privada ECDSA. Retorna firma en hex."""
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    signature = private_key.sign(
        hash_evento.encode("utf-8"),
        ec.ECDSA(hashes.SHA256()),
    )
    return signature.hex()


def verify_signature(public_key_pem: bytes, hash_evento: str, signature_hex: str) -> bool:
    """Verifica la firma digital de un evento."""
    try:
        public_key = serialization.load_pem_public_key(public_key_pem)
        signature = bytes.fromhex(signature_hex)
        public_key.verify(
            signature,
            hash_evento.encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except (InvalidSignature, Exception):
        return False


def verify_event_signature(evento) -> bool:
    """Verifica la firma digital de un evento usando su clave pública almacenada."""
    if not evento.clave_publica_pem or not evento.firma_digital:
        return False
    try:
        public_key_pem = evento.clave_publica_pem.encode("utf-8")
        return verify_signature(public_key_pem, evento.hash_evento, evento.firma_digital)
    except Exception:
        return False


def get_last_event_hash(db: Session, animal_id: UUID) -> str | None:
    """Obtiene el hash del último evento registrado para un animal."""
    last_event = (
        db.query(EventoGanadero)
        .filter(EventoGanadero.id_animales == animal_id)
        .order_by(EventoGanadero.registrado_en.desc())
        .first()
    )
    return last_event.hash_evento if last_event else None


def verify_chain_integrity(db: Session, animal_id: UUID) -> list[dict]:
    """Verifica la integridad de la cadena de hashes para un animal."""
    eventos = (
        db.query(EventoGanadero)
        .filter(EventoGanadero.id_animales == animal_id)
        .order_by(EventoGanadero.registrado_en.asc())
        .all()
    )

    resultados = []
    hash_anterior = None

    for pos, evento in enumerate(eventos, 1):
        cadena_integra = evento.hash_evento_pasado == hash_anterior
        resultados.append({
            "posicion": pos,
            "id_eventos": evento.id_eventos,
            "tipo_evento": evento.tipo_evento.value if hasattr(evento.tipo_evento, 'value') else evento.tipo_evento,
            "hash_evento": evento.hash_evento,
            "hash_esperado": hash_anterior,
            "cadena_integra": cadena_integra,
            "registrado_en": evento.registrado_en,
        })
        hash_anterior = evento.hash_evento

    return resultados
