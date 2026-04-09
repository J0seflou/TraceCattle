"""
Router de búsqueda: búsqueda global de animales y eventos.
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.database import get_db
from backend.models.models import Animal, EventoGanadero, User
from backend.schemas.schemas import AnimalResponse, EventoResponse
from backend.utils.security import get_current_user

router = APIRouter(prefix="/api/busqueda", tags=["Búsqueda"])


@router.get("/animales")
def search_animals(
    q: Optional[str] = Query(None, description="Texto de búsqueda"),
    especie: Optional[str] = Query(None),
    raza: Optional[str] = Query(None),
    sexo: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Buscar animales por múltiples criterios."""
    query = db.query(Animal)

    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Animal.codigo_unico.ilike(search_term),
                Animal.nombre.ilike(search_term),
                Animal.especie.ilike(search_term),
                Animal.raza.ilike(search_term),
                Animal.color.ilike(search_term),
                Animal.marcas.ilike(search_term),
            )
        )
    if especie:
        query = query.filter(Animal.especie.ilike(f"%{especie}%"))
    if raza:
        query = query.filter(Animal.raza.ilike(f"%{raza}%"))
    if sexo:
        query = query.filter(Animal.sexo == sexo)
    if activo is not None:
        query = query.filter(Animal.activo == activo)

    animals = query.order_by(Animal.registrado_en.desc()).limit(50).all()

    result = []
    for a in animals:
        owner = db.query(User).filter(User.id_users == a.propietario_id).first()
        result.append({
            "id_animales": str(a.id_animales),
            "codigo_unico": a.codigo_unico,
            "especie": a.especie,
            "raza": a.raza,
            "nombre": a.nombre,
            "fecha_nacimiento": str(a.fecha_nacimiento) if a.fecha_nacimiento else None,
            "sexo": a.sexo,
            "peso_kg": float(a.peso_kg) if a.peso_kg else None,
            "color": a.color,
            "marcas": a.marcas,
            "propietario_nombre": f"{owner.nombre} {owner.apellido}" if owner else None,
            "activo": a.activo,
            "registrado_en": str(a.registrado_en),
        })
    return result


@router.get("/eventos")
def search_events(
    q: Optional[str] = Query(None, description="Texto de búsqueda"),
    tipo_evento: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Buscar eventos por múltiples criterios."""
    query = db.query(EventoGanadero)

    if tipo_evento:
        query = query.filter(EventoGanadero.tipo_evento == tipo_evento)

    if fecha_desde:
        try:
            fd = datetime.fromisoformat(fecha_desde)
            query = query.filter(EventoGanadero.registrado_en >= fd)
        except (ValueError, TypeError):
            pass

    if fecha_hasta:
        try:
            fh = datetime.fromisoformat(fecha_hasta)
            # Agregar 1 día para incluir todo el día
            query = query.filter(EventoGanadero.registrado_en <= fh)
        except (ValueError, TypeError):
            pass

    eventos = query.order_by(EventoGanadero.registrado_en.desc()).limit(50).all()

    result = []
    for e in eventos:
        actor = db.query(User).filter(User.id_users == e.id_actor).first()
        animal = db.query(Animal).filter(Animal.id_animales == e.id_animales).first()

        # Si hay búsqueda de texto, filtrar por nombre del animal o código
        if q:
            search_lower = q.lower()
            match = False
            if animal and (search_lower in (animal.codigo_unico or "").lower() or search_lower in (animal.nombre or "").lower()):
                match = True
            if actor and (search_lower in (actor.nombre or "").lower() or search_lower in (actor.apellido or "").lower()):
                match = True
            if e.ubicacion and search_lower in e.ubicacion.lower():
                match = True
            if not match:
                continue

        result.append({
            "id_eventos": str(e.id_eventos),
            "id_animales": str(e.id_animales),
            "animal_info": f"{animal.codigo_unico} - {animal.nombre or animal.especie}" if animal else "N/A",
            "tipo_evento": e.tipo_evento.value if hasattr(e.tipo_evento, 'value') else e.tipo_evento,
            "datos_evento": e.datos_evento,
            "ubicacion": e.ubicacion,
            "hash_evento": e.hash_evento,
            "actor_nombre": f"{actor.nombre} {actor.apellido}" if actor else None,
            "registrado_en": str(e.registrado_en),
        })
    return result
