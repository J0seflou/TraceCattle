"""
Servicio de verificación de firma manuscrita digital (Llave 1).
Usa OpenCV para extraer características y comparar firmas por similitud estructural.
"""
import io
import pickle
import numpy as np
import cv2


def extract_signature_features(image_bytes: bytes) -> np.ndarray:
    """
    Extrae características de una imagen de firma manuscrita.
    - Convierte a escala de grises
    - Aplica umbralización
    - Detecta contornos
    - Extrae momentos Hu como vector de características
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen de firma")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Binarizar
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Encontrar contornos
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        # Retornar vector de ceros si no hay contornos
        return np.zeros(7, dtype=np.float64)

    # Combinar todos los contornos
    all_contours = np.vstack(contours)

    # Calcular momentos Hu (invariantes a escala, rotación y traslación)
    moments = cv2.moments(all_contours)
    hu_moments = cv2.HuMoments(moments).flatten()

    # Aplicar log transform para normalizar
    hu_log = -np.sign(hu_moments) * np.log10(np.abs(hu_moments) + 1e-10)

    return hu_log


def compare_signatures(stored_template: bytes, new_signature: bytes, threshold: float = 0.75) -> tuple[bool, float]:
    """
    Compara firma almacenada con nueva firma.
    Retorna (coincide, score).
    """
    try:
        stored_features = decode_template(stored_template)
        new_features = extract_signature_features(new_signature)

        # Similitud por correlación de momentos Hu
        if np.linalg.norm(stored_features) == 0 or np.linalg.norm(new_features) == 0:
            return False, 0.0

        # Distancia euclidiana normalizada como score de similitud
        distance = np.linalg.norm(stored_features - new_features)
        max_distance = np.linalg.norm(stored_features) + np.linalg.norm(new_features)

        if max_distance == 0:
            score = 0.0
        else:
            score = 1.0 - (distance / max_distance)

        score = max(0.0, min(1.0, score))
        return score >= threshold, float(score)

    except Exception as e:
        print(f"Error comparando firmas: {e}")
        return False, 0.0


def encode_template(features: np.ndarray) -> bytes:
    """Serializa características de firma a bytes."""
    return pickle.dumps(features)


def decode_template(data: bytes) -> np.ndarray:
    """Deserializa características de firma desde bytes."""
    return pickle.loads(data)
