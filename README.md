# 🐄 Trace Cattle

**Sistema de trazabilidad ganadera con integridad criptográfica y autenticación biométrica de triple llave.**

Cada evento en la vida de un animal (nacimiento, vacunación, traslado, venta...) queda registrado en una cadena de eventos encadenados por hash — al estilo blockchain — firmados digitalmente y protegidos por triple verificación biométrica del usuario que los registra.

## Seguridad

| Mecanismo | Tecnología |
|---|---|
| Integridad de la cadena de eventos | SHA-256 encadenado (cada evento incluye el hash del anterior) |
| Firma digital de eventos | ECDSA (curva P-256) |
| Cifrado de plantillas biométricas | AES-256 |
| Autenticación de usuarios | JWT + bcrypt |
| Triple llave biométrica | Firma manuscrita + reconocimiento facial + verificación de voz |

Ningún evento puede crearse sin superar las tres verificaciones biométricas. Cualquier alteración de un evento en la base de datos rompe la cadena de hashes y es detectada por el módulo de auditoría.

## Roles

- **Ganadero** — crea su finca, registra animales y eventos, gestiona miembros.
- **Veterinario** — registra eventos sanitarios (vacunación, desparasitación...).
- **Transportista** — registra traslados.
- **Auditor** — verificado contra el registro SENASA; consulta historial, integridad y bitácora.
- **Admin** — gestión global de fincas y usuarios.

## Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, PostgreSQL
- **Biometría:** OpenCV (rostro y firma), SciPy (voz)
- **Frontend:** HTML/CSS/JS vanilla (SPA servida por el propio backend)

## Ejecución local

```bash
# 1. PostgreSQL corriendo en localhost:5432 con la base de datos:
psql -U postgres -c 'CREATE DATABASE "PruebaTC";'

# 2. Configuración
cp .env.example .env
# → editar .env: genera SECRET_KEY con:
#   python -c "import secrets; print(secrets.token_hex(32))"

# 3. Dependencias
pip install -r requirements.txt

# 4. Arrancar (crea tablas y datos iniciales automáticamente)
uvicorn backend.main:app --reload
```

Abre **http://localhost:8000**. La documentación interactiva de la API está en **/docs**.

## Despliegue en línea

Ver [DESPLIEGUE_RAILWAY.md](DESPLIEGUE_RAILWAY.md) para publicarlo con un link compartible en ~10 minutos.

## Estructura

```
backend/
  main.py            # Punto de entrada, seeding y migraciones automáticas
  config.py          # Configuración por variables de entorno
  routers/           # auth, animales, eventos, biometría, auditoría, fincas, senasa...
  services/          # criptografía (hash + ECDSA), biometría, email
  models/ schemas/   # SQLAlchemy + Pydantic
frontend/            # SPA (index.html + js/ + css/)
```
