"""
Servicio de reconocimiento facial (Llave 2).
Usa OpenCV con Haar Cascade para detectar rostros y comparar por similitud de histograma/embedding.
"""
import io
import pickle
import numpy as np
import cv2


# Dimensiones del embedding facial
FACE_SIZE = (128, 128)


def extract_face_embedding(image_bytes: bytes) -> np.ndarray:
    """
    Extrae un embedding del rostro en la imagen.
    - Detecta rostro con Haar Cascade
    - Recorta y redimensiona a 128x128
    - Normaliza y genera vector de características con histograma LBP simplificado
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen facial")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detectar rostros
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

    if len(faces) == 0:
        raise ValueError("No se detectó ningún rostro en la imagen")

    # Tomar el rostro más grande
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_roi = gray[y:y+h, x:x+w]

    # Redimensionar
    face_resized = cv2.resize(face_roi, FACE_SIZE)

    # Normalizar
    face_normalized = face_resized.astype(np.float32) / 255.0

    # Calcular histograma LBP simplificado como embedding
    embedding = _compute_lbp_histogram(face_normalized)

    return embedding


def _compute_lbp_histogram(image: np.ndarray) -> np.ndarray:
    """
    Calcula un histograma LBP (Local Binary Pattern) simplificado.
    Divide la imagen en regiones y calcula histogramas locales.
    """
    h, w = image.shape
    lbp = np.zeros_like(image, dtype=np.uint8)

    # Calcular LBP para cada pixel (excepto bordes)
    for i in range(1, h - 1):
        for j in range(1, w - 1):
            center = image[i, j]
            code = 0
            code |= (image[i-1, j-1] >= center) << 7
            code |= (image[i-1, j] >= center) << 6
            code |= (image[i-1, j+1] >= center) << 5
            code |= (image[i, j+1] >= center) << 4
            code |= (image[i+1, j+1] >= center) << 3
            code |= (image[i+1, j] >= center) << 2
            code |= (image[i+1, j-1] >= center) << 1
            code |= (image[i, j-1] >= center) << 0
            lbp[i, j] = code

    # Dividir en 4x4 = 16 regiones y calcular histograma por región
    grid_h, grid_w = 4, 4
    cell_h, cell_w = h // grid_h, w // grid_w
    histograms = []

    for gi in range(grid_h):
        for gj in range(grid_w):
            cell = lbp[gi*cell_h:(gi+1)*cell_h, gj*cell_w:(gj+1)*cell_w]
            hist, _ = np.histogram(cell, bins=32, range=(0, 256))
            hist = hist.astype(np.float32)
            total = hist.sum()
            if total > 0:
                hist /= total
            histograms.append(hist)

    return np.concatenate(histograms)


def compare_faces(stored_template: bytes, new_face: bytes, threshold: float = 0.70) -> tuple[bool, float]:
    """
    Compara el embedding facial almacenado con uno nuevo.
    Usa similitud coseno entre los histogramas LBP.
    Retorna (coincide, score).
    """
    try:
        stored_embedding = decode_template(stored_template)
        new_embedding = extract_face_embedding(new_face)

        # Similitud coseno
        dot = np.dot(stored_embedding, new_embedding)
        norm_a = np.linalg.norm(stored_embedding)
        norm_b = np.linalg.norm(new_embedding)

        if norm_a == 0 or norm_b == 0:
            return False, 0.0

        cosine_sim = dot / (norm_a * norm_b)
        score = float(max(0.0, min(1.0, cosine_sim)))

        return score >= threshold, score

    except Exception as e:
        print(f"Error comparando rostros: {e}")
        return False, 0.0


def encode_template(embedding: np.ndarray) -> bytes:
    """Serializa embedding facial a bytes."""
    return pickle.dumps(embedding)


def decode_template(data: bytes) -> np.ndarray:
    """Deserializa embedding facial desde bytes."""
    return pickle.loads(data)
