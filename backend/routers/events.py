"""
Router de eventos ganaderos - MÓDULO CRÍTICO.
Implementa la lógica de 3 llaves biométricas + criptografía.
"""
import base64
from uuid import UUID
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import settings
from backend.models.models import (
    User, Animal, EventoGanadero, PlantillaBiometrica,
    ValidacionBiometrica, Role,
)
from backend.schemas.schemas import EventoCreate, EventoResponse, BiometricValidationResponse
from backend.utils.security import get_current_user
from backend.utils.permissions import check_permission
from backend.services import (
    event_service,
    crypto_service,
    biometric_signature,
    biometric_face,
    biometric_voice,
)

router = APIRouter(prefix="/api/eventos", tags=["Eventos Ganaderos"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registrar un evento ganadero con validación de 3 llaves biométricas.

    Flujo:
    1. Verificar permiso del rol para el tipo de evento
    2. Validar firma manuscrita (Llave 1)
    3. Validar reconocimiento facial (Llave 2)
    4. Validar verificación de voz (Llave 3)
    5. Si las 3 llaves pasan: generar hash, encadenar, firmar y registrar
    6. Si alguna falla: rechazar y registrar en bitácora
    """
    ip_origen = request.client.host if request.client else None

    # ── Paso 1: Verificar permiso del rol ──
    rol_nombre = current_user.rol.nombre if current_user.rol else ""
    if not check_permission(rol_nombre, data.tipo_evento):
        event_service.log_to_bitacora(
            db, current_user.id_users,
            "registro_evento", "rechazado", ip_origen,
            {"motivo": "rol_no_autorizado", "rol": rol_nombre, "tipo_evento": data.tipo_evento},
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail=f"El rol '{rol_nombre}' no puede registrar eventos de tipo '{data.tipo_evento}'",
        )

    # Verificar que el animal existe
    animal = db.query(Animal).filter(Animal.id_animales == data.id_animales).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal no encontrado")

    # Verificar que el usuario tiene plantilla biométrica registrada
    plantilla = db.query(PlantillaBiometrica).filter(
        PlantillaBiometrica.id_users == current_user.id_users
    ).first()
    if not plantilla:
        raise HTTPException(
            status_code=400,
            detail="Debe registrar sus datos biométricos antes de crear eventos",
        )

    # ── Paso 2: Validación de firma manuscrita (Llave 1) ──
    try:
        firma_bytes = base64.b64decode(data.firma_imagen)
    except Exception:
        raise HTTPException(status_code=400, detail="Imagen de firma en base64 inválida")

    firma_ok, score_firma = biometric_signature.compare_signatures(
        plantilla.firma_manuscrita, firma_bytes, settings.SIGNATURE_THRESHOLD
    )

    if not firma_ok:
        event_service.log_to_bitacora(
            db, current_user.id_users,
            "validacion_biometrica", "rechazado", ip_origen,
            {"llave": "firma", "score": score_firma, "umbral": settings.SIGNATURE_THRESHOLD},
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail={
                "mensaje": "Validación de firma manuscrita FALLIDA. Registro denegado.",
                "llave_fallida": "firma",
                "score": score_firma,
                "umbral": settings.SIGNATURE_THRESHOLD,
            },
        )

    # ── Paso 3: Validación facial (Llave 2) ──
    try:
        rostro_bytes = base64.b64decode(data.rostro_imagen)
    except Exception:
        raise HTTPException(status_code=400, detail="Imagen facial en base64 inválida")

    rostro_ok, score_rostro = biometric_face.compare_faces(
        plantilla.vector_facial, rostro_bytes, settings.FACE_THRESHOLD
    )

    if not rostro_ok:
        event_service.log_to_bitacora(
            db, current_user.id_users,
            "validacion_biometrica", "rechazado", ip_origen,
            {"llave": "rostro", "score": score_rostro, "umbral": settings.FACE_THRESHOLD},
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail={
                "mensaje": "Validación facial FALLIDA. Registro denegado.",
                "llave_fallida": "rostro",
                "score": score_rostro,
                "umbral": settings.FACE_THRESHOLD,
            },
        )

    # ── Paso 4: Validación de voz (Llave 3) ──
    try:
        voz_bytes = base64.b64decode(data.audio_voz)
    except Exception:
        raise HTTPException(status_code=400, detail="Audio de voz en base64 inválido")

    voz_ok, score_voz = biometric_voice.compare_voices(
        plantilla.patron_voz, voz_bytes, settings.VOICE_THRESHOLD
    )

    if not voz_ok:
        event_service.log_to_bitacora(
            db, current_user.id_users,
            "validacion_biometrica", "rechazado", ip_origen,
            {"llave": "voz", "score": score_voz, "umbral": settings.VOICE_THRESHOLD},
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail={
                "mensaje": "Validación de voz FALLIDA. Registro denegado.",
                "llave_fallida": "voz",
                "score": score_voz,
                "umbral": settings.VOICE_THRESHOLD,
            },
        )

    # ── Paso 5: Las 3 llaves aprobadas → Registro criptográfico ──
    # Generar claves ECDSA para firma digital del evento
    private_key_pem, public_key_pem = crypto_service.generate_ecdsa_keys()

    evento = event_service.register_event(
        db=db,
        animal_id=data.id_animales,
        actor_id=current_user.id_users,
        tipo_evento=data.tipo_evento,
        datos_evento=data.datos_evento,
        ubicacion=data.ubicacion,
        private_key_pem=private_key_pem,
        public_key_pem=public_key_pem,
    )

    # ── Paso 6: Registrar validación biométrica ──
    validacion = ValidacionBiometrica(
        id_user=current_user.id_users,
        id_eventos=evento.id_eventos,
        firma_ok=firma_ok,
        rostro_ok=rostro_ok,
        voz_ok=voz_ok,
        score_firma=score_firma,
        score_rostro=score_rostro,
        score_voz=score_voz,
    )
    db.add(validacion)

    # ── Paso 7: Registrar en bitácora ──
    event_service.log_to_bitacora(
        db, current_user.id_users,
        "registro_evento", "exitoso", ip_origen,
        {
            "tipo_evento": data.tipo_evento,
            "animal_id": str(data.id_animales),
            "hash_evento": evento.hash_evento,
            "scores": {
                "firma": score_firma,
                "rostro": score_rostro,
                "voz": score_voz,
            },
        },
    )

    db.commit()
    db.refresh(evento)

    return {
        "evento": {
            "id_eventos": str(evento.id_eventos),
            "id_animales": str(evento.id_animales),
            "tipo_evento": data.tipo_evento,
            "datos_evento": evento.datos_evento,
            "ubicacion": evento.ubicacion,
            "hash_evento": evento.hash_evento,
            "hash_evento_pasado": evento.hash_evento_pasado,
            "firma_digital": evento.firma_digital[:50] + "...",
            "actor": f"{current_user.nombre} {current_user.apellido}",
            "registrado_en": str(evento.registrado_en),
        },
        "validacion_biometrica": {
            "firma_ok": firma_ok,
            "rostro_ok": rostro_ok,
            "voz_ok": voz_ok,
            "score_firma": score_firma,
            "score_rostro": score_rostro,
            "score_voz": score_voz,
            "aprobado": True,
        },
        "mensaje": "Evento registrado exitosamente. Las 3 llaves biométricas fueron aprobadas.",
    }


@router.get("/", response_model=list[EventoResponse])
def list_events(
    animal_id: Optional[UUID] = Query(None),
    actor_id: Optional[UUID] = Query(None),
    tipo_evento: Optional[str] = Query(None),
    fecha_desde: Optional[datetime] = Query(None),
    fecha_hasta: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar eventos con filtros."""
    query = db.query(EventoGanadero)

    if animal_id:
        query = query.filter(EventoGanadero.id_animales == animal_id)
    if actor_id:
        query = query.filter(EventoGanadero.id_actor == actor_id)
    if tipo_evento:
        query = query.filter(EventoGanadero.tipo_evento == tipo_evento)
    if fecha_desde:
        query = query.filter(EventoGanadero.registrado_en >= fecha_desde)
    if fecha_hasta:
        query = query.filter(EventoGanadero.registrado_en <= fecha_hasta)

    eventos = query.order_by(EventoGanadero.registrado_en.desc()).all()

    result = []
    for e in eventos:
        actor = db.query(User).filter(User.id_users == e.id_actor).first()
        result.append(EventoResponse(
            id_eventos=e.id_eventos,
            id_animales=e.id_animales,
            tipo_evento=e.tipo_evento.value if hasattr(e.tipo_evento, 'value') else e.tipo_evento,
            datos_evento=e.datos_evento,
            ubicacion=e.ubicacion,
            hash_evento=e.hash_evento,
            hash_evento_pasado=e.hash_evento_pasado,
            firma_digital=e.firma_digital,
            actor_nombre=f"{actor.nombre} {actor.apellido}" if actor else None,
            registrado_en=e.registrado_en,
        ))
    return result


@router.get("/{event_id}")
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener detalles de un evento con su validación biométrica."""
    evento = db.query(EventoGanadero).filter(EventoGanadero.id_eventos == event_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    actor = db.query(User).filter(User.id_users == evento.id_actor).first()
    validacion = db.query(ValidacionBiometrica).filter(
        ValidacionBiometrica.id_eventos == event_id
    ).first()

    return {
        "evento": {
            "id_eventos": str(evento.id_eventos),
            "id_animales": str(evento.id_animales),
            "tipo_evento": evento.tipo_evento.value if hasattr(evento.tipo_evento, 'value') else evento.tipo_evento,
            "datos_evento": evento.datos_evento,
            "ubicacion": evento.ubicacion,
            "hash_evento": evento.hash_evento,
            "hash_evento_pasado": evento.hash_evento_pasado,
            "firma_digital": evento.firma_digital,
            "actor": f"{actor.nombre} {actor.apellido}" if actor else None,
            "rol_actor": actor.rol.nombre if actor and actor.rol else None,
            "registrado_en": str(evento.registrado_en),
        },
        "validacion_biometrica": {
            "firma_ok": validacion.firma_ok,
            "rostro_ok": validacion.rostro_ok,
            "voz_ok": validacion.voz_ok,
            "score_firma": float(validacion.score_firma) if validacion.score_firma else None,
            "score_rostro": float(validacion.score_rostro) if validacion.score_rostro else None,
            "score_voz": float(validacion.score_voz) if validacion.score_voz else None,
            "aprobado": validacion.firma_ok and validacion.rostro_ok and validacion.voz_ok,
        } if validacion else None,
    }
