"""
Trace Cattle - Sistema de Trazabilidad Ganadera con Seguridad Criptográfica y Biométrica.

Punto de entrada de la aplicación FastAPI.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import engine, Base
from backend.models.models import *  # noqa: F401,F403 - importar modelos para crear tablas
from backend.routers import auth, users, animals, events, biometrics, audit, search, fincas, senasa
from backend.config import settings

# Crear tablas automáticamente al iniciar (para despliegue en la nube)
Base.metadata.create_all(bind=engine)

# Migraciones incrementales: agregar columnas nuevas si no existen
from sqlalchemy import text as _sql_text
with engine.connect() as _conn:
    # origen_desconocido en animales
    _conn.execute(_sql_text("""
        ALTER TABLE animales
        ADD COLUMN IF NOT EXISTS origen_desconocido BOOLEAN NOT NULL DEFAULT FALSE
    """))
    # clave_publica_pem en eventos_ganaderos
    _conn.execute(_sql_text("""
        ALTER TABLE eventos_ganaderos
        ADD COLUMN IF NOT EXISTS clave_publica_pem TEXT
    """))
    # info_pajilla en animales
    _conn.execute(_sql_text("""
        ALTER TABLE animales
        ADD COLUMN IF NOT EXISTS info_pajilla TEXT
    """))
    _conn.commit()

# ── Seeding inicial: roles y usuario administrador ──
from backend.database import SessionLocal
from backend.models.models import Role, User, AuditorAutorizado
from backend.utils.security import hash_password

_db = SessionLocal()
try:
    # Insertar roles si no existen (uno a uno para no perder los existentes)
    for nombre, desc in [
        ("ganadero", "Propietario de animales."),
        ("veterinario", "Profesional de salud animal."),
        ("transportista", "Responsable de traslados."),
        ("auditor", "Auditor del sistema."),
        ("admin", "Administrador del sistema con acceso total."),
    ]:
        if not _db.query(Role).filter(Role.nombre == nombre).first():
            _db.add(Role(nombre=nombre, descripcion=desc))
    _db.commit()

    # Insertar auditores SENASA autorizados si no existen
    _auditores_senasa = [
        ("SENASA-AUD-001", "Jorge Ramírez"),
        ("SENASA-AUD-002", "Jose Flores"),
    ]
    for carnet, nombre in _auditores_senasa:
        if not _db.query(AuditorAutorizado).filter(AuditorAutorizado.carnet_senasa == carnet).first():
            _db.add(AuditorAutorizado(carnet_senasa=carnet, nombre_completo=nombre, activo=True))
    _db.commit()

    # Crear usuario administrador único si no existe
    if not _db.query(User).filter(User.email == settings.ADMIN_EMAIL).first():
        admin_role = _db.query(Role).filter(Role.nombre == "admin").first()
        if admin_role:
            _db.add(User(
                rol_id=admin_role.id_roles,
                finca_id=None,
                nombre="Administrador",
                apellido="Sistema",
                email=settings.ADMIN_EMAIL,
                contrasena_hash=hash_password(settings.ADMIN_PASSWORD),
                activo=True,
            ))
            _db.commit()
finally:
    _db.close()

app = FastAPI(
    title="Trace Cattle",
    description=(
        "Sistema de trazabilidad ganadera con integridad criptográfica "
        "y autenticación biométrica de triple llave (firma manuscrita, "
        "reconocimiento facial, verificación de voz)."
    ),
    version="1.0.0",
)

# CORS — solo origenes explícitamente permitidos (V-001)
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,https://tracecattle.netlify.app",
)
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Registrar routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(animals.router)
app.include_router(events.router)
app.include_router(biometrics.router)
app.include_router(audit.router)
app.include_router(search.router)
app.include_router(fincas.router)
app.include_router(senasa.router)

@app.get("/api/health")
def health_check():
    # V-011: no exponer arquitectura, versión ni módulos en endpoint público
    return {"status": "ok"}


# Servir frontend como archivos estáticos (debe ir al final)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
