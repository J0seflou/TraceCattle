"""
Router de gestión de animales.
"""
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import Animal, User, Role
from backend.schemas.schemas import AnimalCreate, AnimalResponse, AnimalUpdate
from backend.utils.security import get_current_user, require_role
from backend.services import event_service, crypto_service

router = APIRouter(prefix="/api/animales", tags=["Animales"])


@router.post("/", response_model=AnimalResponse, status_code=status.HTTP_201_CREATED)
def create_animal(
    data: AnimalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ganadero")),
):
    """Registrar un nuevo animal (solo ganadero)."""
    # Verificar código único
    existing = db.query(Animal).filter(Animal.codigo_unico == data.codigo_unico).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un animal con ese código único")

    animal = Animal(
        propietario_id=current_user.id_users,
        finca_id=current_user.finca_id,
        codigo_unico=data.codigo_unico,
        especie=data.especie,
        raza=data.raza,
        nombre=data.nombre,
        fecha_nacimiento=data.fecha_nacimiento,
        sexo=data.sexo,
        peso_kg=data.peso_kg,
        color=data.color,
        marcas=data.marcas,
        madre_id=data.madre_id,
        padre_id=data.padre_id,
        es_inseminada=data.es_inseminada or False,
    )
    db.add(animal)
    db.commit()
    db.refresh(animal)

    madre_nombre = None
    padre_nombre = None
    if animal.madre_id:
        madre = db.query(Animal).filter(Animal.id_animales == animal.madre_id).first()
        madre_nombre = madre.nombre or madre.codigo_unico if madre else None
    if animal.padre_id:
        padre = db.query(Animal).filter(Animal.id_animales == animal.padre_id).first()
        padre_nombre = padre.nombre or padre.codigo_unico if padre else None

    return AnimalResponse(
        id_animales=animal.id_animales,
        codigo_unico=animal.codigo_unico,
        especie=animal.especie,
        raza=animal.raza,
        nombre=animal.nombre,
        fecha_nacimiento=animal.fecha_nacimiento,
        sexo=animal.sexo,
        peso_kg=animal.peso_kg,
        color=animal.color,
        marcas=animal.marcas,
        madre_id=animal.madre_id,
        padre_id=animal.padre_id,
        madre_nombre=madre_nombre,
        padre_nombre=padre_nombre,
        es_inseminada=animal.es_inseminada,
        hermanos=None,
        propietario_nombre=f"{current_user.nombre} {current_user.apellido}",
        activo=animal.activo,
        registrado_en=animal.registrado_en,
    )


@router.get("/", response_model=list[AnimalResponse])
def list_animals(
    propietario_id: Optional[UUID] = Query(None),
    especie: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar animales con filtros opcionales (solo de la misma finca)."""
    query = db.query(Animal)

    # Filtrar por finca del usuario
    if current_user.finca_id:
        query = query.filter(Animal.finca_id == current_user.finca_id)

    if propietario_id:
        query = query.filter(Animal.propietario_id == propietario_id)
    if especie:
        query = query.filter(Animal.especie.ilike(f"%{especie}%"))
    if activo is not None:
        query = query.filter(Animal.activo == activo)

    animals = query.order_by(Animal.registrado_en.desc()).all()

    result = []
    for a in animals:
        owner = db.query(User).filter(User.id_users == a.propietario_id).first()
        madre_nombre = None
        padre_nombre = None
        if a.madre_id:
            madre = db.query(Animal).filter(Animal.id_animales == a.madre_id).first()
            madre_nombre = madre.nombre or madre.codigo_unico if madre else None
        if a.padre_id:
            padre = db.query(Animal).filter(Animal.id_animales == a.padre_id).first()
            padre_nombre = padre.nombre or padre.codigo_unico if padre else None
        result.append(AnimalResponse(
            id_animales=a.id_animales,
            codigo_unico=a.codigo_unico,
            especie=a.especie,
            raza=a.raza,
            nombre=a.nombre,
            fecha_nacimiento=a.fecha_nacimiento,
            sexo=a.sexo,
            peso_kg=a.peso_kg,
            color=a.color,
            marcas=a.marcas,
            madre_id=a.madre_id,
            padre_id=a.padre_id,
            madre_nombre=madre_nombre,
            padre_nombre=padre_nombre,
            es_inseminada=a.es_inseminada,
            hermanos=None,
            propietario_nombre=f"{owner.nombre} {owner.apellido}" if owner else None,
            activo=a.activo,
            registrado_en=a.registrado_en,
        ))
    return result


@router.get("/{animal_id}", response_model=AnimalResponse)
def get_animal(
    animal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener detalles de un animal."""
    animal = db.query(Animal).filter(Animal.id_animales == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal no encontrado")

    owner = db.query(User).filter(User.id_users == animal.propietario_id).first()

    madre_nombre = None
    padre_nombre = None
    if animal.madre_id:
        madre = db.query(Animal).filter(Animal.id_animales == animal.madre_id).first()
        madre_nombre = madre.nombre or madre.codigo_unico if madre else None
    if animal.padre_id:
        padre = db.query(Animal).filter(Animal.id_animales == animal.padre_id).first()
        padre_nombre = padre.nombre or padre.codigo_unico if padre else None

    # Compute hermanos (same madre or padre)
    hermanos = []
    if animal.madre_id:
        hermanos_madre = db.query(Animal).filter(
            Animal.madre_id == animal.madre_id,
            Animal.id_animales != animal.id_animales
        ).all()
        for h in hermanos_madre:
            hermanos.append({"id": str(h.id_animales), "nombre": h.nombre or h.codigo_unico, "relacion": "mismo madre"})
    if animal.padre_id:
        hermanos_padre = db.query(Animal).filter(
            Animal.padre_id == animal.padre_id,
            Animal.id_animales != animal.id_animales
        ).all()
        for h in hermanos_padre:
            if not any(hh["id"] == str(h.id_animales) for hh in hermanos):
                hermanos.append({"id": str(h.id_animales), "nombre": h.nombre or h.codigo_unico, "relacion": "mismo padre"})

    return AnimalResponse(
        id_animales=animal.id_animales,
        codigo_unico=animal.codigo_unico,
        especie=animal.especie,
        raza=animal.raza,
        nombre=animal.nombre,
        fecha_nacimiento=animal.fecha_nacimiento,
        sexo=animal.sexo,
        peso_kg=animal.peso_kg,
        color=animal.color,
        marcas=animal.marcas,
        madre_id=animal.madre_id,
        padre_id=animal.padre_id,
        madre_nombre=madre_nombre,
        padre_nombre=padre_nombre,
        es_inseminada=animal.es_inseminada,
        hermanos=hermanos if hermanos else None,
        propietario_nombre=f"{owner.nombre} {owner.apellido}" if owner else None,
        activo=animal.activo,
        registrado_en=animal.registrado_en,
    )


@router.put("/{animal_id}", response_model=AnimalResponse)
def update_animal(
    animal_id: UUID,
    data: AnimalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar información de un animal (solo propietario)."""
    animal = db.query(Animal).filter(Animal.id_animales == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal no encontrado")

    rol_nombre = current_user.rol.nombre if current_user.rol else ""
    if animal.propietario_id != current_user.id_users and rol_nombre != "auditor":
        raise HTTPException(status_code=403, detail="Solo el propietario puede editar este animal")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(animal, key, value)

    db.commit()
    db.refresh(animal)
    owner = db.query(User).filter(User.id_users == animal.propietario_id).first()

    madre_nombre = None
    padre_nombre = None
    if animal.madre_id:
        madre = db.query(Animal).filter(Animal.id_animales == animal.madre_id).first()
        madre_nombre = madre.nombre or madre.codigo_unico if madre else None
    if animal.padre_id:
        padre = db.query(Animal).filter(Animal.id_animales == animal.padre_id).first()
        padre_nombre = padre.nombre or padre.codigo_unico if padre else None

    # Compute hermanos (same madre or padre)
    hermanos = []
    if animal.madre_id:
        hermanos_madre = db.query(Animal).filter(
            Animal.madre_id == animal.madre_id,
            Animal.id_animales != animal.id_animales
        ).all()
        for h in hermanos_madre:
            hermanos.append({"id": str(h.id_animales), "nombre": h.nombre or h.codigo_unico, "relacion": "mismo madre"})
    if animal.padre_id:
        hermanos_padre = db.query(Animal).filter(
            Animal.padre_id == animal.padre_id,
            Animal.id_animales != animal.id_animales
        ).all()
        for h in hermanos_padre:
            if not any(hh["id"] == str(h.id_animales) for hh in hermanos):
                hermanos.append({"id": str(h.id_animales), "nombre": h.nombre or h.codigo_unico, "relacion": "mismo padre"})

    return AnimalResponse(
        id_animales=animal.id_animales,
        codigo_unico=animal.codigo_unico,
        especie=animal.especie,
        raza=animal.raza,
        nombre=animal.nombre,
        fecha_nacimiento=animal.fecha_nacimiento,
        sexo=animal.sexo,
        peso_kg=animal.peso_kg,
        color=animal.color,
        marcas=animal.marcas,
        madre_id=animal.madre_id,
        padre_id=animal.padre_id,
        madre_nombre=madre_nombre,
        padre_nombre=padre_nombre,
        es_inseminada=animal.es_inseminada,
        hermanos=hermanos if hermanos else None,
        propietario_nombre=f"{owner.nombre} {owner.apellido}" if owner else None,
        activo=animal.activo,
        registrado_en=animal.registrado_en,
    )


@router.get("/{animal_id}/historial")
def get_animal_history(
    animal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener historial completo de eventos de un animal."""
    animal = db.query(Animal).filter(Animal.id_animales == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal no encontrado")

    return event_service.get_animal_history(db, animal_id)


@router.get("/{animal_id}/integridad")
def verify_integrity(
    animal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verificar integridad criptográfica de la cadena de eventos de un animal."""
    animal = db.query(Animal).filter(Animal.id_animales == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal no encontrado")

    return event_service.verify_animal_integrity(db, animal_id)
