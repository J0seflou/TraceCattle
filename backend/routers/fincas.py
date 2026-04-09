"""
Router de fincas: consultar información de la finca del usuario.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import User, Finca
from backend.schemas.schemas import FincaResponse, UserResponse
from backend.utils.security import get_current_user

router = APIRouter(prefix="/api/fincas", tags=["Fincas"])


@router.get("/mi-finca", response_model=FincaResponse)
def get_mi_finca(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Obtener la finca del usuario autenticado."""
    if not current_user.finca_id:
        raise HTTPException(status_code=404, detail="No tienes una finca asignada")

    finca = db.query(Finca).filter(Finca.id_finca == current_user.finca_id).first()
    if not finca:
        raise HTTPException(status_code=404, detail="Finca no encontrada")

    return FincaResponse(
        id_finca=finca.id_finca,
        nombre=finca.nombre,
        ubicacion=finca.ubicacion,
        descripcion=finca.descripcion,
        codigo_acceso=finca.codigo_acceso,
        activa=finca.activa,
        creado_en=finca.creado_en,
        total_usuarios=db.query(User).filter(User.finca_id == finca.id_finca).count(),
        total_animales=len(finca.animales) if finca.animales else 0,
    )


@router.get("/mi-finca/miembros")
def get_miembros_finca(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Obtener los miembros de la finca del usuario."""
    if not current_user.finca_id:
        raise HTTPException(status_code=404, detail="No tienes una finca asignada")

    miembros = db.query(User).filter(User.finca_id == current_user.finca_id).all()
    result = []
    for m in miembros:
        rol = m.rol
        result.append({
            "id_users": str(m.id_users),
            "nombre": m.nombre,
            "apellido": m.apellido,
            "email": m.email,
            "rol": rol.nombre if rol else "",
            "activo": m.activo,
            "creado_en": m.creado_en.isoformat(),
        })
    return result
