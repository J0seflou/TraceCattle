"""
Router de autenticación: registro, login y perfil.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import User, Role, Finca, AuditorAutorizado
from backend.schemas.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse, FincaResponse,
)
from backend.utils.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


def _build_finca_response(finca, db):
    """Construir respuesta de finca con conteos."""
    if not finca:
        return None
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


def _build_user_response(user, rol, db):
    """Construir respuesta de usuario con finca."""
    finca_resp = _build_finca_response(user.finca, db) if user.finca_id else None
    return UserResponse(
        id_users=user.id_users,
        nombre=user.nombre,
        apellido=user.apellido,
        email=user.email,
        telefono=user.telefono,
        rol_nombre=rol.nombre if rol else "",
        activo=user.activo,
        creado_en=user.creado_en,
        finca=finca_resp,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Registrar un nuevo usuario con su rol y finca."""
    # Verificar que el email no exista
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # El rol admin está reservado: no se puede registrar mediante este endpoint
    if user_data.rol_nombre == "admin":
        raise HTTPException(status_code=403, detail="No se puede registrar con ese rol")

    # Buscar rol
    rol = db.query(Role).filter(Role.nombre == user_data.rol_nombre).first()
    if not rol:
        raise HTTPException(status_code=400, detail=f"Rol '{user_data.rol_nombre}' no existe")

    # Validar carné SENASA si el rol es auditor
    if user_data.rol_nombre == "auditor":
        if not user_data.carnet_senasa or not user_data.carnet_senasa.strip():
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar su número de carné SENASA para registrarse como auditor"
            )
        carnet_normalizado = user_data.carnet_senasa.strip().upper()
        auditor_autorizado = db.query(AuditorAutorizado).filter(
            AuditorAutorizado.carnet_senasa == carnet_normalizado,
            AuditorAutorizado.activo == True,
        ).first()
        if not auditor_autorizado:
            raise HTTPException(
                status_code=403,
                detail="La identificación no pertenece a un auditor autorizado por SENASA"
            )
        if auditor_autorizado.id_user_registrado is not None:
            raise HTTPException(
                status_code=409,
                detail="Este carné SENASA ya tiene una cuenta registrada. Contacte al administrador si cree que es un error"
            )

    finca = None

    # Si es ganadero, debe crear una finca nueva
    if user_data.rol_nombre == "ganadero":
        if not user_data.finca_nombre:
            raise HTTPException(
                status_code=400,
                detail="El ganadero debe proporcionar el nombre de la finca"
            )
        finca = Finca(
            nombre=user_data.finca_nombre,
            ubicacion=user_data.finca_ubicacion,
        )
        db.add(finca)
        db.flush()  # obtener el ID sin commit

    # Si es otro rol, debe unirse a una finca existente
    else:
        if not user_data.codigo_finca:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar el código de acceso de una finca"
            )
        finca = db.query(Finca).filter(
            Finca.codigo_acceso == user_data.codigo_finca.upper()
        ).first()
        if not finca:
            raise HTTPException(
                status_code=400,
                detail="Código de finca inválido. Verifique con el ganadero."
            )
        if not finca.activa:
            raise HTTPException(status_code=400, detail="La finca está desactivada")

    # Crear usuario
    new_user = User(
        rol_id=rol.id_roles,
        finca_id=finca.id_finca if finca else None,
        nombre=user_data.nombre,
        apellido=user_data.apellido,
        email=user_data.email,
        contrasena_hash=hash_password(user_data.contrasena),
        telefono=user_data.telefono,
    )
    db.add(new_user)
    db.flush()

    # Si es ganadero, asignar como propietario de la finca
    if user_data.rol_nombre == "ganadero" and finca:
        finca.propietario_id = new_user.id_users

    db.commit()
    db.refresh(new_user)
    if finca:
        db.refresh(finca)

    # Marcar el carné SENASA como usado por este usuario
    if user_data.rol_nombre == "auditor":
        carnet_normalizado = user_data.carnet_senasa.strip().upper()
        auditor_autorizado = db.query(AuditorAutorizado).filter(
            AuditorAutorizado.carnet_senasa == carnet_normalizado
        ).first()
        if auditor_autorizado:
            auditor_autorizado.id_user_registrado = new_user.id_users
            db.commit()

    # Generar token
    token = create_access_token({"sub": str(new_user.id_users)})

    return TokenResponse(
        access_token=token,
        user=_build_user_response(new_user, rol, db),
    )


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Iniciar sesión y obtener token JWT."""
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.contrasena, user.contrasena_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not user.activo:
        raise HTTPException(status_code=403, detail="Usuario desactivado")

    rol = db.query(Role).filter(Role.id_roles == user.rol_id).first()
    token = create_access_token({"sub": str(user.id_users)})

    return TokenResponse(
        access_token=token,
        user=_build_user_response(user, rol, db),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Obtener perfil del usuario autenticado."""
    rol = current_user.rol
    return _build_user_response(current_user, rol, db)
