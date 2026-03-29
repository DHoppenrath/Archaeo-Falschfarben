"""
enhancement.py – Kontrastverbesserung, CLAHE, Histogramm-Spreizung, Gamma.
"""
import numpy as np
import cv2


def apply_clahe(image: np.ndarray,
                clip_limit: float = 2.0,
                tile_size: int = 8) -> np.ndarray:
    """
    CLAHE (Contrast Limited Adaptive Histogram Equalization) auf Luminanz-Kanal.
    Arbeitsbereich: LAB-Farbraum – Farben bleiben erhalten, Kontrast steigt lokal.
    clip_limit: Kontrastbegrenzung (1.0–8.0, Standard 2.0)
    tile_size:  Kachelgröße in Pixeln (4–32, Standard 8)
    """
    lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip_limit,
                             tileGridSize=(tile_size, tile_size))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def histogram_stretch(image: np.ndarray,
                       low_pct: float = 2.0,
                       high_pct: float = 98.0) -> np.ndarray:
    """
    Lineare Histogramm-Spreizung pro Kanal zwischen Percentil-Grenzen.
    Hebt subtile Farbunterschiede in monotonen Bodenbildern stark hervor.
    """
    result = np.zeros_like(image, dtype=np.uint8)
    for ch in range(3):
        channel = image[:, :, ch].astype(np.float32)
        p_low = np.percentile(channel, low_pct)
        p_high = np.percentile(channel, high_pct)
        stretched = (channel - p_low) / (p_high - p_low + 1e-6) * 255.0
        result[:, :, ch] = np.clip(stretched, 0, 255).astype(np.uint8)
    return result


def gamma_correction(image: np.ndarray, gamma: float = 1.0) -> np.ndarray:
    """
    Gamma-Korrektur: gamma < 1.0 hellt auf, gamma > 1.0 verdunkelt.
    Nützlich für über-/unterbelichtete Luftbilder.
    """
    if abs(gamma - 1.0) < 1e-4:
        return image.copy()
    lut = np.array([
        min(255, int((i / 255.0) ** (1.0 / gamma) * 255))
        for i in range(256)
    ], dtype=np.uint8)
    return lut[image]


def denoise(image: np.ndarray, strength: int = 7) -> np.ndarray:
    """
    Leichte Entrauschung mit fastNlMeansDenoisingColored.
    strength: Filtertstärke (3–15). Höhere Werte = mehr Glättung.
    """
    strength = max(3, min(15, int(strength)))
    return cv2.fastNlMeansDenoisingColored(image,
                                           None,
                                           h=strength,
                                           hColor=strength,
                                           templateWindowSize=7,
                                           searchWindowSize=21)
