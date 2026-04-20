"""
Router de gestión de usuarios.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import User, Role
from backend.schemas.schemas import UserResponse, UserUpdate
from backend.utils.security import get_current_user, require_role

router = APIRouter(prefix="/api/users", tags=["Usuarios"])


@router.get("/", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("auditor")),
):
    """Listar todos los usuarios (solo auditor)."""
    users = db.query(User).filter(User.activo == True).all()
    result = []
    for u in users:
        rol = db.query(Role).filter(Role.id_roles == u.rol_id).first()
        result.append(UserResponse(
            id_users=u.id_users,
            nombre=u.nombre,
            apellido=u.apellido,
            email=u.email,
            telefono=u.telefono,
            rol_nombre=rol.nombre if rol else "",
            activo=u.activo,
            creado_en=u.creado_en,
        ))
    return result


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener detalles de un usuario."""
    user = db.query(User).filter(User.id_users == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    rol = db.query(Role).filter(Role.id_roles == user.rol_id).first()
    return UserResponse(
        id_users=user.id_users,
        nombre=user.nombre,
        apellido=user.apellido,
        email=user.email,
        telefono=user.telefono,
        rol_nombre=rol.nombre if rol else "",
        activo=user.activo,
        creado_en=user.creado_en,
    )


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar información de un usuario (solo el propio usuario o admin)."""
    rol_nombre = current_user.rol.nombre if current_user.rol else ""

    # V-006: solo el propio usuario o admin pueden editar; auditores no pueden editar cuentas ajenas
    if current_user.id_users != user_id and rol_nombre != "admin":
        raise HTTPException(status_code=403, detail="No autorizado para editar este usuario")

    user = db.query(User).filter(User.id_users == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Whitelist explícita de campos modificables (evita mass assignment)
    _ALLOWED_FIELDS = {"nombre", "apellido", "telefono"}
    update_data = {
        k: v for k, v in data.model_dump(exclude_unset=True).items()
        if k in _ALLOWED_FIELDS
    }

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    rol = db.query(Role).filter(Role.id_roles == user.rol_id).first()

    return UserResponse(
        id_users=user.id_users,
        nombre=user.nombre,
        apellido=user.apellido,
        email=user.email,
        telefono=user.telefono,
        rol_nombre=rol.nombre if rol else "",
        activo=user.activo,
        creado_en=user.creado_en,
    )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("auditor")),
):
    """Desactivar un usuario (solo auditor)."""
    user = db.query(User).filter(User.id_users == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.activo = False
    db.commit()
    return {"message": "Usuario desactivado exitosamente"}
