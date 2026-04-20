"""
Router de auditoría: bitácora, alertas, verificación de integridad.
"""
from uuid import UUID
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import (
    User, Animal, BitacoraSistema, EventoGanadero,
    ValidacionBiometrica, Role,
)
from backend.schemas.schemas import BitacoraResponse, AuditoriaAnimalResponse, AnimalResponse
from backend.utils.security import get_current_user, require_role
from backend.services import event_service, crypto_service

router = APIRouter(prefix="/api/auditoria", tags=["Auditoría"])


@router.get("/bitacora", response_model=list[BitacoraResponse])
def get_bitacora(
    user_id: Optional[UUID] = Query(None),
    accion: Optional[str] = Query(None),
    resultado: Optional[str] = Query(None),
    fecha_desde: Optional[datetime] = Query(None),
    fecha_hasta: Optional[datetime] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("auditor")),
):
    """Consultar bitácora del sistema. Auditores ven todo, otros solo sus propias entradas."""
    query = db.query(BitacoraSistema)

    # If not auditor, restrict to own entries
    rol_nombre = current_user.rol.nombre if current_user.rol else ""
    if rol_nombre != "auditor":
        query = query.filter(BitacoraSistema.id_user == current_user.id_users)
    elif user_id:
        query = query.filter(BitacoraSistema.id_user == user_id)

    if accion:
        query = query.filter(BitacoraSistema.accion.ilike(f"%{accion}%"))
    if resultado:
        query = query.filter(BitacoraSistema.resultado == resultado)
    if fecha_desde:
        query = query.filter(BitacoraSistema.ocurrido_en >= fecha_desde)
    if fecha_hasta:
        query = query.filter(BitacoraSistema.ocurrido_en <= fecha_hasta)

    entries = query.order_by(BitacoraSistema.ocurrido_en.desc()).limit(limit).all()

    result = []
    for e in entries:
        user = db.query(User).filter(User.id_users == e.id_user).first() if e.id_user else None
        result.append(BitacoraResponse(
            id_bitacora=e.id_bitacora,
            id_user=e.id_user,
            usuario_nombre=f"{user.nombre} {user.apellido}" if user else None,
            accion=e.accion,
            resultado=e.resultado.value if hasattr(e.resultado, 'value') else e.resultado,
            ip_origen=str(e.ip_origen) if e.ip_origen else None,
            detalle=e.detalle,
            ocurrido_en=e.ocurrido_en,
        ))
    return result


@router.get("/animal/{animal_id}")
def audit_animal(
    animal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reporte completo de auditoría para un animal."""
    animal = db.query(Animal).filter(Animal.id_animales == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal no encontrado")

    owner = db.query(User).filter(User.id_users == animal.propietario_id).first()

    # Historial de eventos
    historial = event_service.get_animal_history(db, animal_id)

    # Verificar integridad
    integridad = event_service.verify_animal_integrity(db, animal_id)

    return {
        "animal": {
            "id_animales": str(animal.id_animales),
            "codigo_unico": animal.codigo_unico,
            "especie": animal.especie,
            "raza": animal.raza,
            "nombre": animal.nombre,
            "propietario": f"{owner.nombre} {owner.apellido}" if owner else None,
            "activo": animal.activo,
        },
        "total_eventos": len(historial),
        "eventos": historial,
        "integridad": integridad,
    }


@router.get("/alertas")
def get_alerts(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("auditor")),
):
    """Obtener intentos fallidos de validación biométrica."""
    query = (
        db.query(BitacoraSistema)
        .filter(BitacoraSistema.accion == "validacion_biometrica")
        .filter(BitacoraSistema.resultado == "rechazado")
    )

    # Non-auditors only see their own alerts
    rol_nombre = current_user.rol.nombre if current_user.rol else ""
    if rol_nombre != "auditor":
        query = query.filter(BitacoraSistema.id_user == current_user.id_users)

    entries = query.order_by(BitacoraSistema.ocurrido_en.desc()).limit(limit).all()

    result = []
    for e in entries:
        user = db.query(User).filter(User.id_users == e.id_user).first() if e.id_user else None
        rol = None
        if user:
            role = db.query(Role).filter(Role.id_roles == user.rol_id).first()
            rol = role.nombre if role else None

        result.append({
            "ocurrido_en": str(e.ocurrido_en),
            "usuario": f"{user.nombre} {user.apellido}" if user else "Desconocido",
            "rol": rol or "N/A",
            "ip_origen": str(e.ip_origen) if e.ip_origen else None,
            "detalle": e.detalle,
        })
    return result


@router.get("/integridad-global")
def global_integrity_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("auditor")),
):
    """Verificar integridad criptográfica de animales."""
    rol_nombre = current_user.rol.nombre if current_user.rol else ""

    if rol_nombre == "auditor":
        animales = db.query(Animal).filter(Animal.activo == True).all()
    else:
        # Non-auditors only see their own animals
        animales = db.query(Animal).filter(
            Animal.activo == True,
            Animal.propietario_id == current_user.id_users
        ).all()

    resultados = []
    total_ok = 0
    total_fail = 0

    for animal in animales:
        integridad = event_service.verify_animal_integrity(db, animal.id_animales)
        is_ok = integridad["cadena_completa_integra"]

        if is_ok:
            total_ok += 1
        else:
            total_fail += 1

        resultados.append({
            "animal_id": str(animal.id_animales),
            "codigo_unico": animal.codigo_unico,
            "nombre": animal.nombre,
            "total_eventos": integridad["total_eventos"],
            "cadena_integra": is_ok,
        })

    return {
        "total_animales": len(animales),
        "cadenas_integras": total_ok,
        "cadenas_con_error": total_fail,
        "detalle": resultados,
    }
