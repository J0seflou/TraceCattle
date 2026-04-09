"""
Servicio orquestador de registro de eventos ganaderos.
Coordina la validación de roles, biometría y criptografía.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.models import EventoGanadero, Animal, User, ValidacionBiometrica, BitacoraSistema
from backend.services import crypto_service
from backend.utils.permissions import check_permission, get_allowed_events


def validate_role_permission(rol_nombre: str, tipo_evento: str) -> bool:
    """Verifica si un rol tiene permiso para registrar un tipo de evento."""
    return check_permission(rol_nombre, tipo_evento)


def register_event(
    db: Session,
    animal_id: UUID,
    actor_id: UUID,
    tipo_evento: str,
    datos_evento: dict,
    ubicacion: str | None,
    private_key_pem: bytes,
    public_key_pem: bytes,
) -> EventoGanadero:
    """
    Registra un evento ganadero con protección criptográfica completa.
    1. Obtiene hash del evento anterior
    2. Genera hash SHA-256 del nuevo evento
    3. Firma digitalmente el hash
    4. Crea el registro encadenado
    """
    timestamp = datetime.utcnow()

    # Obtener hash anterior para encadenamiento
    hash_anterior = crypto_service.get_last_event_hash(db, animal_id)

    # Generar hash del evento
    hash_evento = crypto_service.generate_event_hash(
        animal_id=animal_id,
        actor_id=actor_id,
        tipo_evento=tipo_evento,
        datos_evento=datos_evento,
        timestamp=timestamp,
        hash_anterior=hash_anterior,
    )

    # Firmar digitalmente
    firma_digital = crypto_service.sign_event(private_key_pem, hash_evento)

    # Crear evento
    evento = EventoGanadero(
        id_animales=animal_id,
        id_actor=actor_id,
        tipo_evento=tipo_evento,
        datos_evento=datos_evento,
        ubicacion=ubicacion,
        hash_evento=hash_evento,
        hash_evento_pasado=hash_anterior,
        firma_digital=firma_digital,
        clave_publica_pem=public_key_pem.decode("utf-8"),
        registrado_en=timestamp,
    )

    db.add(evento)
    db.flush()  # Para obtener el ID sin hacer commit

    return evento


def get_animal_history(db: Session, animal_id: UUID) -> list[dict]:
    """Obtiene el historial completo de eventos de un animal."""
    eventos = (
        db.query(EventoGanadero)
        .filter(EventoGanadero.id_animales == animal_id)
        .order_by(EventoGanadero.registrado_en.asc())
        .all()
    )

    result = []
    for e in eventos:
        actor = db.query(User).filter(User.id_users == e.id_actor).first()
        validacion = (
            db.query(ValidacionBiometrica)
            .filter(ValidacionBiometrica.id_eventos == e.id_eventos)
            .first()
        )

        result.append({
            "id_eventos": e.id_eventos,
            "id_animales": e.id_animales,
            "tipo_evento": e.tipo_evento.value if hasattr(e.tipo_evento, 'value') else e.tipo_evento,
            "datos_evento": e.datos_evento,
            "ubicacion": e.ubicacion,
            "hash_evento": e.hash_evento,
            "hash_evento_pasado": e.hash_evento_pasado,
            "firma_digital": e.firma_digital,
            "actor_nombre": f"{actor.nombre} {actor.apellido}" if actor else None,
            "registrado_en": e.registrado_en,
            "firma_verificada": crypto_service.verify_event_signature(e),
            "validacion": {
                "firma_ok": validacion.firma_ok,
                "rostro_ok": validacion.rostro_ok,
                "voz_ok": validacion.voz_ok,
                "aprobado": validacion.firma_ok and validacion.rostro_ok and validacion.voz_ok,
            } if validacion else None,
        })

    return result


def verify_animal_integrity(db: Session, animal_id: UUID) -> dict:
    """Verifica la integridad de la cadena criptográfica de un animal."""
    resultados = crypto_service.verify_chain_integrity(db, animal_id)
    cadena_integra = all(r["cadena_integra"] for r in resultados) if resultados else True
    return {
        "total_eventos": len(resultados),
        "cadena_completa_integra": cadena_integra,
        "detalle": resultados,
    }


def log_to_bitacora(
    db: Session,
    user_id: UUID | None,
    accion: str,
    resultado: str,
    ip_origen: str | None = None,
    detalle: dict | None = None,
):
    """Registra una entrada en la bitácora del sistema."""
    entry = BitacoraSistema(
        id_user=user_id,
        accion=accion,
        resultado=resultado,
        ip_origen=ip_origen,
        detalle=detalle,
    )
    db.add(entry)
