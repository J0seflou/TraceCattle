"""
Router de gestión biométrica: registro, actualización y verificación de plantillas.
"""
import base64
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import settings
from backend.models.models import User, PlantillaBiometrica
from backend.schemas.schemas import BiometricStatusResponse, BiometricVerifyRequest, BiometricValidationResponse
from backend.utils.security import get_current_user
from backend.services import biometric_signature, biometric_face, biometric_voice

router = APIRouter(prefix="/api/biometria", tags=["Biometría"])


@router.post("/registrar", status_code=status.HTTP_201_CREATED)
async def register_biometrics(
    firma: UploadFile = File(..., description="Imagen de firma manuscrita"),
    rostro: UploadFile = File(..., description="Foto del rostro"),
    voz: UploadFile = File(..., description="Audio de voz (WAV)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registrar plantillas biométricas de un usuario.
    Captura las 3 llaves: firma manuscrita, rostro y voz.
    """
    # Verificar que no tenga plantilla existente
    existing = db.query(PlantillaBiometrica).filter(
        PlantillaBiometrica.id_users == current_user.id_users
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Ya tiene plantillas biométricas registradas. Use /actualizar para modificarlas.",
        )

    # Procesar firma
    try:
        firma_bytes = await firma.read()
        firma_features = biometric_signature.extract_signature_features(firma_bytes)
        firma_template = biometric_signature.encode_template(firma_features)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error procesando firma: {str(e)}")

    # Procesar rostro
    try:
        rostro_bytes = await rostro.read()
        rostro_embedding = biometric_face.extract_face_embedding(rostro_bytes)
        rostro_template = biometric_face.encode_template(rostro_embedding)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error procesando rostro: {str(e)}")

    # Procesar voz
    try:
        voz_bytes = await voz.read()
        voz_features = biometric_voice.extract_voice_features(voz_bytes)
        voz_template = biometric_voice.encode_template(voz_features)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error procesando voz: {str(e)}")

    # Guardar plantilla
    plantilla = PlantillaBiometrica(
        id_users=current_user.id_users,
        firma_manuscrita=firma_template,
        vector_facial=rostro_template,
        patron_voz=voz_template,
    )
    db.add(plantilla)
    db.commit()
    db.refresh(plantilla)

    return {
        "mensaje": "Plantillas biométricas registradas exitosamente",
        "algoritmos": {
            "firma": plantilla.algoritmo_firma,
            "facial": plantilla.algoritmo_facial,
            "voz": plantilla.algoritmo_voz,
        },
    }


@router.put("/actualizar")
async def update_biometrics(
    firma: UploadFile = File(None, description="Nueva imagen de firma"),
    rostro: UploadFile = File(None, description="Nueva foto del rostro"),
    voz: UploadFile = File(None, description="Nuevo audio de voz (WAV)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar plantillas biométricas."""
    plantilla = db.query(PlantillaBiometrica).filter(
        PlantillaBiometrica.id_users == current_user.id_users
    ).first()
    if not plantilla:
        raise HTTPException(status_code=404, detail="No tiene plantillas biométricas registradas")

    updated = []

    if firma:
        firma_bytes = await firma.read()
        firma_features = biometric_signature.extract_signature_features(firma_bytes)
        plantilla.firma_manuscrita = biometric_signature.encode_template(firma_features)
        updated.append("firma")

    if rostro:
        rostro_bytes = await rostro.read()
        rostro_embedding = biometric_face.extract_face_embedding(rostro_bytes)
        plantilla.vector_facial = biometric_face.encode_template(rostro_embedding)
        updated.append("rostro")

    if voz:
        voz_bytes = await voz.read()
        voz_features = biometric_voice.extract_voice_features(voz_bytes)
        plantilla.patron_voz = biometric_voice.encode_template(voz_features)
        updated.append("voz")

    if not updated:
        raise HTTPException(status_code=400, detail="Debe enviar al menos un archivo para actualizar")

    db.commit()
    return {"mensaje": f"Plantillas actualizadas: {', '.join(updated)}"}


@router.post("/verificar", response_model=BiometricValidationResponse)
def verify_biometrics(
    data: BiometricVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verificar biometría sin registrar evento.
    Útil para probar que las 3 llaves funcionan correctamente.
    """
    plantilla = db.query(PlantillaBiometrica).filter(
        PlantillaBiometrica.id_users == current_user.id_users
    ).first()
    if not plantilla:
        raise HTTPException(status_code=404, detail="No tiene plantillas biométricas registradas")

    # Verificar firma
    try:
        firma_bytes = base64.b64decode(data.firma_imagen)
        firma_ok, score_firma = biometric_signature.compare_signatures(
            plantilla.firma_manuscrita, firma_bytes, settings.SIGNATURE_THRESHOLD
        )
    except Exception:
        firma_ok, score_firma = False, 0.0

    # Verificar rostro
    try:
        rostro_bytes = base64.b64decode(data.rostro_imagen)
        rostro_ok, score_rostro = biometric_face.compare_faces(
            plantilla.vector_facial, rostro_bytes, settings.FACE_THRESHOLD
        )
    except Exception:
        rostro_ok, score_rostro = False, 0.0

    # Verificar voz
    try:
        voz_bytes = base64.b64decode(data.audio_voz)
        voz_ok, score_voz = biometric_voice.compare_voices(
            plantilla.patron_voz, voz_bytes, settings.VOICE_THRESHOLD
        )
    except Exception:
        voz_ok, score_voz = False, 0.0

    return BiometricValidationResponse(
        firma_ok=firma_ok,
        rostro_ok=rostro_ok,
        voz_ok=voz_ok,
        score_firma=score_firma,
        score_rostro=score_rostro,
        score_voz=score_voz,
        aprobado=firma_ok and rostro_ok and voz_ok,
    )


@router.get("/estado/{user_id}", response_model=BiometricStatusResponse)
def biometric_status(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verificar si un usuario tiene plantillas biométricas registradas."""
    plantilla = db.query(PlantillaBiometrica).filter(
        PlantillaBiometrica.id_users == user_id
    ).first()

    if not plantilla:
        return BiometricStatusResponse(registrado=False)

    return BiometricStatusResponse(
        registrado=True,
        algoritmo_firma=plantilla.algoritmo_firma,
        algoritmo_facial=plantilla.algoritmo_facial,
        algoritmo_voz=plantilla.algoritmo_voz,
        registrado_en=plantilla.registrado_en,
    )
