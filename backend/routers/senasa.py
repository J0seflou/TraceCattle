"""
Router de administración de auditores autorizados SENASA.

Solo el administrador puede agregar, desactivar o consultar el catálogo.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import AuditorAutorizado, User
from backend.schemas.schemas import AuditorAutorizadoCreate, AuditorAutorizadoResponse
from backend.utils.security import require_role

router = APIRouter(prefix="/api/senasa", tags=["SENASA – Auditores autorizados"])


@router.get("/auditores", response_model=list[AuditorAutorizadoResponse])
def listar_auditores(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Listar todos los carnés SENASA registrados (solo admin)."""
    auditores = db.query(AuditorAutorizado).order_by(AuditorAutorizado.registrado_en.desc()).all()
    result = []
    for a in auditores:
        result.append(AuditorAutorizadoResponse(
            id=a.id,
            carnet_senasa=a.carnet_senasa,
            nombre_completo=a.nombre_completo,
            activo=a.activo,
            disponible=a.id_user_registrado is None,
            registrado_en=a.registrado_en,
        ))
    return result


@router.post("/auditores", response_model=AuditorAutorizadoResponse, status_code=status.HTTP_201_CREATED)
def agregar_auditor(
    data: AuditorAutorizadoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Agregar un carné SENASA al catálogo de auditores autorizados (solo admin)."""
    carnet_normalizado = data.carnet_senasa.strip().upper()
    existente = db.query(AuditorAutorizado).filter(
        AuditorAutorizado.carnet_senasa == carnet_normalizado
    ).first()
    if existente:
        raise HTTPException(
            status_code=409,
            detail=f"El carné '{carnet_normalizado}' ya existe en el catálogo"
        )

    nuevo = AuditorAutorizado(
        carnet_senasa=carnet_normalizado,
        nombre_completo=data.nombre_completo.strip(),
        activo=True,
        agregado_por=current_user.id_users,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return AuditorAutorizadoResponse(
        id=nuevo.id,
        carnet_senasa=nuevo.carnet_senasa,
        nombre_completo=nuevo.nombre_completo,
        activo=nuevo.activo,
        disponible=nuevo.id_user_registrado is None,
        registrado_en=nuevo.registrado_en,
    )


@router.put("/auditores/{auditor_id}/desactivar", response_model=AuditorAutorizadoResponse)
def desactivar_auditor(
    auditor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Desactivar un carné SENASA (el auditor ya no podrá registrarse con él — solo admin)."""
    auditor = db.query(AuditorAutorizado).filter(AuditorAutorizado.id == auditor_id).first()
    if not auditor:
        raise HTTPException(status_code=404, detail="Carné no encontrado")

    auditor.activo = False
    db.commit()
    db.refresh(auditor)

    return AuditorAutorizadoResponse(
        id=auditor.id,
        carnet_senasa=auditor.carnet_senasa,
        nombre_completo=auditor.nombre_completo,
        activo=auditor.activo,
        disponible=auditor.id_user_registrado is None,
        registrado_en=auditor.registrado_en,
    )


@router.put("/auditores/{auditor_id}/activar", response_model=AuditorAutorizadoResponse)
def activar_auditor(
    auditor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Reactivar un carné SENASA previamente desactivado (solo admin)."""
    auditor = db.query(AuditorAutorizado).filter(AuditorAutorizado.id == auditor_id).first()
    if not auditor:
        raise HTTPException(status_code=404, detail="Carné no encontrado")

    auditor.activo = True
    db.commit()
    db.refresh(auditor)

    return AuditorAutorizadoResponse(
        id=auditor.id,
        carnet_senasa=auditor.carnet_senasa,
        nombre_completo=auditor.nombre_completo,
        activo=auditor.activo,
        disponible=auditor.id_user_registrado is None,
        registrado_en=auditor.registrado_en,
    )


@router.delete("/auditores/{auditor_id}", status_code=status.HTTP_200_OK)
def eliminar_auditor(
    auditor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    Eliminar permanentemente un carné SENASA del catálogo (solo admin).
    Solo se permite si el carné aún no tiene usuario registrado.
    """
    auditor = db.query(AuditorAutorizado).filter(AuditorAutorizado.id == auditor_id).first()
    if not auditor:
        raise HTTPException(status_code=404, detail="Carné no encontrado")
    if auditor.id_user_registrado is not None:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar un carné que ya tiene un auditor registrado. Use desactivar en su lugar."
        )

    db.delete(auditor)
    db.commit()
    return {"message": f"Carné '{auditor.carnet_senasa}' eliminado del catálogo"}


@router.get("/auditores/verificar/{carnet}", response_model=dict)
def verificar_carnet(
    carnet: str,
    db: Session = Depends(get_db),
):
    """
    Verificar si un carné SENASA es válido y está disponible.
    Este endpoint es público para que el formulario de registro pueda validar antes de enviar.
    """
    carnet_normalizado = carnet.strip().upper()
    auditor = db.query(AuditorAutorizado).filter(
        AuditorAutorizado.carnet_senasa == carnet_normalizado,
        AuditorAutorizado.activo == True,
    ).first()

    if not auditor:
        return {"valido": False, "disponible": False, "mensaje": "La identificación no pertenece a un auditor autorizado por SENASA"}

    if auditor.id_user_registrado is not None:
        return {"valido": True, "disponible": False, "mensaje": "Este carné ya tiene una cuenta registrada"}

    return {
        "valido": True,
        "disponible": True,
        "nombre_auditor": auditor.nombre_completo,
        "mensaje": f"Carné válido — Auditor: {auditor.nombre_completo}",
    }
