"""
edge_detector.py – Kantenfilter für archäologische Strukturerkennung.
Detektiert Grabenkanten, Hausgrundrisse, Gruben und Pfosten.
"""
import numpy as np
import cv2


EDGE_METHODS = {
    "Sobel":    "Gradient-Magnitude (Graben-/Mauerreste)",
    "Scharr":   "Verbesserter Sobel, präziser bei diagonalen Strukturen",
    "Canny":    "Zweistufige Kantendetektion (empfohlen für Bewuchsmerkmale)",
    "Laplacian":"Zweite Ableitung (runde Strukturen: Gruben, Pfosten)",
    "LoG":      "Laplacian of Gaussian (Rauschunterdrückung + Runderkennung)",
}


def detect_edges(image: np.ndarray,
                 method: str = "Canny",
                 strength: float = 1.0,
                 low_thresh: int = 50,
                 high_thresh: int = 150) -> np.ndarray:
    """
    Führt Kantendetektion auf dem Bild durch.
    Gibt ein uint8 Graustufenbild (H×W) mit Kanten zurück.

    image:       uint8 RGB
    method:      Name des Algorithmus (aus EDGE_METHODS)
    strength:    Skalierungsfaktor [0.1–3.0]
    low_thresh:  Unterer Schwellwert (Canny)
    high_thresh: Oberer Schwellwert (Canny)
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    if method == "Sobel":
        sx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag = np.sqrt(sx**2 + sy**2)
        edges = _normalize(mag, strength)

    elif method == "Scharr":
        sx = cv2.Scharr(gray, cv2.CV_32F, 1, 0)
        sy = cv2.Scharr(gray, cv2.CV_32F, 0, 1)
        mag = np.sqrt(sx**2 + sy**2)
        edges = _normalize(mag, strength)

    elif method == "Canny":
        lo = max(1, int(low_thresh))
        hi = max(lo + 1, int(high_thresh))
        edges = cv2.Canny(gray, lo, hi)
        if strength != 1.0:
            edges = np.clip(edges.astype(np.float32) * strength, 0, 255).astype(np.uint8)

    elif method == "Laplacian":
        lap = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
        lap_abs = np.abs(lap)
        edges = _normalize(lap_abs, strength)

    elif method == "LoG":
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        lap = cv2.Laplacian(blurred, cv2.CV_32F, ksize=3)
        lap_abs = np.abs(lap)
        edges = _normalize(lap_abs, strength)

    else:
        edges = np.zeros_like(gray)

    return edges


def overlay_edges(base_image: np.ndarray,
                  edges: np.ndarray,
                  color: tuple = (255, 50, 0),
                  opacity: float = 0.7) -> np.ndarray:
    """
    Legt die Kantenkarte farbig über das Basisimage.
    color:   RGB-Farbe der Kantenlinien (Standard: Orange-Rot)
    opacity: Deckkraft der Kanten [0.0–1.0]
    """
    result = base_image.copy().astype(np.float32)
    edge_mask = edges.astype(np.float32) / 255.0

    for ch, c_val in enumerate(color):
        result[:, :, ch] = (
            result[:, :, ch] * (1.0 - edge_mask * opacity)
            + c_val * edge_mask * opacity
        )

    return np.clip(result, 0, 255).astype(np.uint8)


def _normalize(arr: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Normiert ein float32-Array auf [0,255] uint8."""
    mn, mx = arr.min(), arr.max()
    if mx - mn < 1e-6:
        return np.zeros_like(arr, dtype=np.uint8)
    norm = (arr - mn) / (mx - mn) * 255.0 * strength
    return np.clip(norm, 0, 255).astype(np.uint8)
