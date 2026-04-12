"""
Router de gestión biométrica: registro, actualización y verificación de plantillas.
Incluye endpoints para cambiar credenciales con verificación por correo.
"""
import base64
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import settings
from backend.models.models import User, PlantillaBiometrica, CodigoCambioBiometrico
from backend.schemas.schemas import (
    BiometricStatusResponse,
    BiometricVerifyRequest,
    BiometricValidationResponse,
    SolicitarCambioRequest,
    SolicitarCambioResponse,
)
from backend.utils.security import get_current_user
from backend.services import biometric_signature, biometric_face, biometric_voice
from backend.services.email_service import enviar_codigo_cambio_biometrico

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


# ─────────────────────────────────────────────────────────────────────────────
#  Cambio de credenciales biométricas con verificación por correo electrónico
# ─────────────────────────────────────────────────────────────────────────────

def _enmascarar_email(email: str) -> str:
    """Enmascara el email para mostrarlo sin revelar datos sensibles.
    Ejemplo: "jorge@gmail.com" → "jo***@gmail.com"
    """
    local, domain = email.split("@", 1)
    visible = local[:2] if len(local) >= 2 else local[:1]
    return f"{visible}***@{domain}"


@router.post(
    "/solicitar-cambio",
    response_model=SolicitarCambioResponse,
    summary="Solicitar código de verificación para cambiar una credencial biométrica",
)
def solicitar_cambio_biometrico(
    body: SolicitarCambioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Genera un código de 6 dígitos y lo envía al correo del usuario.
    El código es válido durante CODIGO_CAMBIO_EXPIRA_MINUTOS minutos.
    Solo se puede solicitar el cambio si ya existen plantillas biométricas.
    """
    # Verificar que el usuario tenga plantillas registradas
    plantilla = db.query(PlantillaBiometrica).filter(
        PlantillaBiometrica.id_users == current_user.id_users
    ).first()
    if not plantilla:
        raise HTTPException(
            status_code=404,
            detail="No tiene plantillas biométricas registradas. Use /registrar primero.",
        )

    # Invalidar códigos anteriores no usados para este usuario y tipo
    db.query(CodigoCambioBiometrico).filter(
        CodigoCambioBiometrico.id_users == current_user.id_users,
        CodigoCambioBiometrico.tipo_credencial == body.tipo_credencial,
        CodigoCambioBiometrico.usado == False,  # noqa: E712
    ).update({"usado": True})

    # Generar nuevo código
    codigo = "".join(secrets.choice("0123456789") for _ in range(6))
    expira = datetime.utcnow() + timedelta(minutes=settings.CODIGO_CAMBIO_EXPIRA_MINUTOS)

    nuevo_codigo = CodigoCambioBiometrico(
        id_users=current_user.id_users,
        codigo=codigo,
        tipo_credencial=body.tipo_credencial,
        expira_en=expira,
    )
    db.add(nuevo_codigo)
    db.commit()

    # Enviar correo de forma síncrona para detectar errores y reportarlos al usuario
    enviado = enviar_codigo_cambio_biometrico(
        destinatario_email=current_user.email,
        destinatario_nombre=f"{current_user.nombre} {current_user.apellido}",
        codigo=codigo,
        tipo_credencial=body.tipo_credencial,
    )

    if not enviado:
        # Revertir el código si el correo no se pudo enviar
        db.delete(nuevo_codigo)
        db.commit()
        raise HTTPException(
            status_code=503,
            detail=(
                "No se pudo enviar el correo de verificación. "
                "Verifica la configuración SMTP en el archivo .env "
                "(SMTP_USER, SMTP_PASSWORD, SMTP_FROM). "
                "Para Gmail necesitas una 'Contraseña de aplicación', no tu contraseña normal."
            ),
        )

    return SolicitarCambioResponse(
        mensaje="Código de verificación enviado. Revisa tu correo electrónico.",
        email_destino=_enmascarar_email(current_user.email),
        expira_minutos=settings.CODIGO_CAMBIO_EXPIRA_MINUTOS,
    )


@router.put(
    "/cambiar",
    summary="Cambiar una credencial biométrica con código de verificación",
)
async def cambiar_credencial_biometrica(
    tipo_credencial: str = Form(..., description="'firma', 'rostro' o 'voz'"),
    codigo: str = Form(..., min_length=6, max_length=6, description="Código de 6 dígitos recibido por correo"),
    nueva_firma: UploadFile = File(None, description="Nueva imagen de firma (si tipo_credencial='firma')"),
    nuevo_rostro: UploadFile = File(None, description="Nueva foto del rostro (si tipo_credencial='rostro')"),
    nueva_voz: UploadFile = File(None, description="Nuevo audio de voz (si tipo_credencial='voz')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cambia una credencial biométrica del usuario autenticado.
    Requiere el código de verificación previamente enviado al correo.
    """
    # Validar tipo
    tipos_validos = ("firma", "rostro", "voz")
    if tipo_credencial not in tipos_validos:
        raise HTTPException(status_code=400, detail="tipo_credencial debe ser 'firma', 'rostro' o 'voz'")

    # Buscar código válido
    registro_codigo = (
        db.query(CodigoCambioBiometrico)
        .filter(
            CodigoCambioBiometrico.id_users == current_user.id_users,
            CodigoCambioBiometrico.tipo_credencial == tipo_credencial,
            CodigoCambioBiometrico.usado == False,  # noqa: E712
            CodigoCambioBiometrico.expira_en > datetime.utcnow(),
        )
        .order_by(CodigoCambioBiometrico.creado_en.desc())
        .first()
    )

    if not registro_codigo:
        raise HTTPException(
            status_code=400,
            detail="No hay un código de verificación activo para esta credencial. Solicita uno nuevo.",
        )

    if registro_codigo.codigo != codigo:
        raise HTTPException(
            status_code=400,
            detail="Código de verificación incorrecto.",
        )

    # Verificar que el usuario tenga plantilla
    plantilla = db.query(PlantillaBiometrica).filter(
        PlantillaBiometrica.id_users == current_user.id_users
    ).first()
    if not plantilla:
        raise HTTPException(status_code=404, detail="No tiene plantillas biométricas registradas.")

    # Actualizar la credencial correspondiente
    if tipo_credencial == "firma":
        if not nueva_firma:
            raise HTTPException(status_code=400, detail="Debes enviar el archivo nueva_firma.")
        try:
            firma_bytes = await nueva_firma.read()
            firma_features = biometric_signature.extract_signature_features(firma_bytes)
            plantilla.firma_manuscrita = biometric_signature.encode_template(firma_features)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error procesando la nueva firma: {str(e)}")

    elif tipo_credencial == "rostro":
        if not nuevo_rostro:
            raise HTTPException(status_code=400, detail="Debes enviar el archivo nuevo_rostro.")
        try:
            rostro_bytes = await nuevo_rostro.read()
            rostro_embedding = biometric_face.extract_face_embedding(rostro_bytes)
            plantilla.vector_facial = biometric_face.encode_template(rostro_embedding)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error procesando el nuevo rostro: {str(e)}")

    elif tipo_credencial == "voz":
        if not nueva_voz:
            raise HTTPException(status_code=400, detail="Debes enviar el archivo nueva_voz.")
        try:
            voz_bytes = await nueva_voz.read()
            voz_features = biometric_voice.extract_voice_features(voz_bytes)
            plantilla.patron_voz = biometric_voice.encode_template(voz_features)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error procesando la nueva voz: {str(e)}")

    # Marcar el código como usado
    registro_codigo.usado = True
    db.commit()

    nombres_credencial = {"firma": "Firma Manuscrita", "rostro": "Reconocimiento Facial", "voz": "Verificación de Voz"}
    return {
        "mensaje": f"Credencial '{nombres_credencial[tipo_credencial]}' actualizada exitosamente.",
        "tipo_credencial": tipo_credencial,
    }
