"""
Trace Cattle - Sistema de Trazabilidad Ganadera con Seguridad Criptográfica y Biométrica.

Punto de entrada de la aplicación FastAPI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import engine, Base
from backend.models.models import *  # noqa: F401,F403 - importar modelos para crear tablas
from backend.routers import auth, users, animals, events, biometrics, audit, search, fincas

# Crear tablas automáticamente al iniciar (para despliegue en la nube)
Base.metadata.create_all(bind=engine)

# Migración: agregar columna numero_senasa si no existe
from sqlalchemy import text
try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS numero_senasa VARCHAR(50)"))
        _conn.commit()
except Exception:
    pass

# Insertar roles iniciales si no existen
from backend.database import SessionLocal
from backend.models.models import Role
_db = SessionLocal()
try:
    if _db.query(Role).count() == 0:
        for nombre, desc in [
            ("ganadero", "Propietario de animales."),
            ("veterinario", "Profesional de salud animal."),
            ("transportista", "Responsable de traslados."),
            ("auditor", "Auditor del sistema."),
        ]:
            _db.add(Role(nombre=nombre, descripcion=desc))
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

# CORS para permitir acceso desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Servir frontend como archivos estáticos
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "sistema": "Trace Cattle",
        "version": "1.0.0",
        "modulos": [
            "Autenticación JWT",
            "Gestión de usuarios y roles",
            "Identificación digital de animales",
            "Registro de eventos ganaderos",
            "Validación biométrica de triple llave",
            "Criptografía: SHA-256 + ECDSA + encadenamiento",
            "Auditoría e integridad",
        ],
    }
