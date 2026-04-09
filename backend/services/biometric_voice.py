"""
Servicio de verificación de voz (Llave 3).
Extrae características MFCC del audio y compara con DTW / similitud coseno.
"""
import io
import struct
import pickle
import numpy as np
from scipy.fft import dct
from scipy.io import wavfile


# Parámetros MFCC
N_MFCC = 13
N_MELS = 26
FRAME_SIZE = 0.025  # 25ms
FRAME_STRIDE = 0.01  # 10ms


def extract_voice_features(audio_bytes: bytes) -> np.ndarray:
    """
    Extrae características MFCC de audio WAV.
    - Lee audio WAV
    - Aplica pre-énfasis
    - Divide en frames con ventana Hamming
    - Calcula FFT y filtros Mel
    - Aplica DCT para obtener MFCC
    - Retorna vector promedio de MFCC
    """
    # Leer WAV desde bytes
    buf = io.BytesIO(audio_bytes)
    try:
        sample_rate, signal = wavfile.read(buf)
    except Exception:
        raise ValueError("No se pudo leer el archivo de audio WAV")

    # Convertir a mono si es estéreo
    if len(signal.shape) > 1:
        signal = signal.mean(axis=1)

    # Normalizar a float
    signal = signal.astype(np.float64)
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal = signal / max_val

    # Pre-énfasis
    pre_emphasis = 0.97
    emphasized = np.append(signal[0], signal[1:] - pre_emphasis * signal[:-1])

    # Framing
    frame_length = int(round(FRAME_SIZE * sample_rate))
    frame_step = int(round(FRAME_STRIDE * sample_rate))
    signal_length = len(emphasized)
    num_frames = max(1, int(np.ceil((signal_length - frame_length) / frame_step)) + 1)

    # Pad signal
    pad_length = (num_frames - 1) * frame_step + frame_length
    padded = np.append(emphasized, np.zeros(pad_length - signal_length))

    # Crear frames
    indices = np.tile(np.arange(frame_length), (num_frames, 1)) + \
              np.tile(np.arange(0, num_frames * frame_step, frame_step), (frame_length, 1)).T
    frames = padded[indices.astype(np.int32)]

    # Ventana Hamming
    frames *= np.hamming(frame_length)

    # FFT
    nfft = 512
    mag_frames = np.absolute(np.fft.rfft(frames, nfft))
    pow_frames = (mag_frames ** 2) / nfft

    # Filtros Mel
    low_freq_mel = 0
    high_freq_mel = 2595 * np.log10(1 + (sample_rate / 2) / 700)
    mel_points = np.linspace(low_freq_mel, high_freq_mel, N_MELS + 2)
    hz_points = 700 * (10 ** (mel_points / 2595) - 1)
    bin_points = np.floor((nfft + 1) * hz_points / sample_rate).astype(int)

    fbank = np.zeros((N_MELS, int(np.floor(nfft / 2 + 1))))
    for m in range(1, N_MELS + 1):
        f_m_minus = bin_points[m - 1]
        f_m = bin_points[m]
        f_m_plus = bin_points[m + 1]

        for k in range(f_m_minus, f_m):
            if f_m != f_m_minus:
                fbank[m - 1, k] = (k - f_m_minus) / (f_m - f_m_minus)
        for k in range(f_m, f_m_plus):
            if f_m_plus != f_m:
                fbank[m - 1, k] = (f_m_plus - k) / (f_m_plus - f_m)

    filter_banks = np.dot(pow_frames, fbank.T)
    filter_banks = np.where(filter_banks == 0, np.finfo(float).eps, filter_banks)
    filter_banks = 20 * np.log10(filter_banks)

    # MFCC via DCT
    mfcc = dct(filter_banks, type=2, axis=1, norm="ortho")[:, :N_MFCC]

    # Normalización por media
    mfcc -= np.mean(mfcc, axis=0)

    # Retornar el promedio de todos los frames como vector característico
    return mfcc.mean(axis=0)


def compare_voices(stored_template: bytes, new_voice: bytes, threshold: float = 0.70) -> tuple[bool, float]:
    """
    Compara el patrón de voz almacenado con uno nuevo.
    Usa similitud coseno entre vectores MFCC promedio.
    Retorna (coincide, score).
    """
    try:
        stored_features = decode_template(stored_template)
        new_features = extract_voice_features(new_voice)

        # Similitud coseno
        dot = np.dot(stored_features, new_features)
        norm_a = np.linalg.norm(stored_features)
        norm_b = np.linalg.norm(new_features)

        if norm_a == 0 or norm_b == 0:
            return False, 0.0

        cosine_sim = dot / (norm_a * norm_b)
        # Mapear de [-1, 1] a [0, 1]
        score = float((cosine_sim + 1.0) / 2.0)
        score = max(0.0, min(1.0, score))

        return score >= threshold, score

    except Exception as e:
        print(f"Error comparando voces: {e}")
        return False, 0.0


def encode_template(features: np.ndarray) -> bytes:
    """Serializa características de voz a bytes."""
    return pickle.dumps(features)


def decode_template(data: bytes) -> np.ndarray:
    """Deserializa características de voz desde bytes."""
    return pickle.loads(data)
