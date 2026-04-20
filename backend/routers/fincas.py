"""
Router de fincas: consultar información de la finca del usuario.
"""
from uuid import UUID
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import User, Finca, Animal
from backend.schemas.schemas import FincaResponse, UserResponse
from backend.utils.security import get_current_user, require_role

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

    finca = db.query(Finca).filter(Finca.id_finca == current_user.finca_id).first()
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
            "es_propietario": finca is not None and str(finca.propietario_id) == str(m.id_users),
            "creado_en": m.creado_en.isoformat(),
        })
    return result


@router.post("/unirse", status_code=200)
def unirse_a_finca(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unirse a una finca usando un código de acceso."""
    if current_user.finca_id:
        raise HTTPException(status_code=400, detail="Ya perteneces a una finca. Debes ser expulsado antes de unirte a otra.")

    codigo = payload.get("codigo_acceso", "").strip().upper()
    if not codigo:
        raise HTTPException(status_code=400, detail="El código de acceso es requerido")

    finca = db.query(Finca).filter(Finca.codigo_acceso == codigo).first()
    if not finca:
        raise HTTPException(status_code=404, detail="Código de acceso inválido. Verifique con el administrador de la finca.")
    if not finca.activa:
        raise HTTPException(status_code=400, detail="La finca está desactivada")

    current_user.finca_id = finca.id_finca
    db.commit()

    return {"mensaje": f"Te has unido a la finca '{finca.nombre}' exitosamente"}


@router.delete("/mi-finca/miembros/{user_id}", status_code=200)
def expulsar_miembro(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Expulsar a un miembro de la finca.
    Solo puede hacerlo el propietario de la finca o un administrador.
    """
    rol_nombre = current_user.rol.nombre if current_user.rol else ""

    # Determinar si el usuario actual tiene permiso para expulsar
    es_admin = rol_nombre == "admin"
    es_propietario = False

    if current_user.finca_id:
        finca = db.query(Finca).filter(Finca.id_finca == current_user.finca_id).first()
        es_propietario = finca is not None and str(finca.propietario_id) == str(current_user.id_users)

    if not es_admin and not es_propietario:
        raise HTTPException(status_code=403, detail="Solo el propietario de la finca o un administrador puede expulsar miembros")

    # Buscar al miembro a expulsar
    miembro = db.query(User).filter(User.id_users == user_id).first()
    if not miembro:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificar que el miembro pertenece a la misma finca (o admin puede expulsar de cualquier finca)
    if not es_admin and str(miembro.finca_id) != str(current_user.finca_id):
        raise HTTPException(status_code=403, detail="El usuario no pertenece a tu finca")

    # No se puede expulsar al propietario de la finca
    if miembro.finca_id:
        finca_del_miembro = db.query(Finca).filter(Finca.id_finca == miembro.finca_id).first()
        if finca_del_miembro and str(finca_del_miembro.propietario_id) == str(miembro.id_users):
            raise HTTPException(status_code=400, detail="No se puede expulsar al propietario de la finca")

    # No se puede expulsar a uno mismo
    if str(miembro.id_users) == str(current_user.id_users):
        raise HTTPException(status_code=400, detail="No puedes expulsarte a ti mismo")

    miembro.finca_id = None
    db.commit()

    return {
        "mensaje": f"{miembro.nombre} {miembro.apellido} ha sido removido de la finca exitosamente"
    }


@router.get("/admin/{finca_id}/usuarios")
def listar_usuarios_finca(
    finca_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Listar todos los usuarios de una finca específica (solo admin)."""
    finca = db.query(Finca).filter(Finca.id_finca == finca_id).first()
    if not finca:
        raise HTTPException(status_code=404, detail="Finca no encontrada")

    miembros = db.query(User).filter(User.finca_id == finca_id).all()
    result = []
    for m in miembros:
        result.append({
            "id_users": str(m.id_users),
            "nombre": m.nombre,
            "apellido": m.apellido,
            "email": m.email,
            "rol": m.rol.nombre if m.rol else "",
            "activo": m.activo,
            "es_propietario": str(finca.propietario_id) == str(m.id_users) if finca.propietario_id else False,
            "creado_en": m.creado_en.isoformat() if m.creado_en else None,
        })
    return result


@router.get("/admin/todas")
def listar_todas_fincas(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Listar todas las fincas del sistema con su dueño y estadísticas (solo admin)."""
    fincas = db.query(Finca).filter(Finca.activa == True).order_by(Finca.creado_en.desc()).all()
    result = []
    for f in fincas:
        propietario = db.query(User).filter(User.id_users == f.propietario_id).first() if f.propietario_id else None
        total_animales = db.query(Animal).filter(Animal.finca_id == f.id_finca).count()
        total_miembros = db.query(User).filter(User.finca_id == f.id_finca).count()
        result.append({
            "id_finca": str(f.id_finca),
            "nombre": f.nombre,
            "ubicacion": f.ubicacion or "Sin ubicación",
            "codigo_acceso": f.codigo_acceso,
            "propietario_nombre": f"{propietario.nombre} {propietario.apellido}" if propietario else "Sin propietario",
            "propietario_email": propietario.email if propietario else None,
            "total_animales": total_animales,
            "total_miembros": total_miembros,
            "creado_en": f.creado_en.isoformat(),
        })
    return result
