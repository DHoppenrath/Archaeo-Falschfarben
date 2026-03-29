"""
colormap_engine.py – Falschfarben-Algorithmen für archäologische Bildanalyse.
"""
import numpy as np
import cv2
from core.image_loader import normalize_to_float, float_to_uint8


# ──────────────────────────────────────────────
# Verfügbare Colormaps (Name → Beschreibung)
# ──────────────────────────────────────────────
COLORMAPS = {
    "Original":             "Unverändertes Originalbild",
    "Infrarot-Simulation":  "R↔G-Tausch: Vegetation leuchtet rot (CIR-ähnlich)",
    "Thermal-Jet":          "Helligkeit → Jet-Farbskala (kalt=blau, warm=rot)",
    "Thermal-Hot":          "Helligkeit → Hot-Farbskala (schwarz→rot→gelb→weiß)",
    "Archäo-Profil":        "Eigene Palette: blau(tief/nass)→gelb→rot(anomal)",
    "NDVI-Proxy":           "(R–G)/(R+G) Vegetationsindex aus RGB",
    "Graustufen-Spreizung": "Kontrastverstärkter Grauwert",
    "Falschfarbe-HSV":      "RGB→HSV-Rotation für Strukturbetonung",
    "Boden-Diff RG":        "Differenz R–G: Bodenverfärbungen",
    "Boden-Diff RB":        "Differenz R–B: Bodenverfärbungen",
}


def apply_colormap(image: np.ndarray, name: str, params: dict = None) -> np.ndarray:
    """
    Wendet die gewählte Falschfarben-Transformation an.
    image: uint8 RGB (H×W×3)
    Gibt uint8 RGB zurück.
    """
    if params is None:
        params = {}

    if name == "Original":
        return image.copy()
    elif name == "Infrarot-Simulation":
        return _infrared_simulation(image)
    elif name == "Thermal-Jet":
        return _thermal(image, cv2.COLORMAP_JET)
    elif name == "Thermal-Hot":
        return _thermal(image, cv2.COLORMAP_HOT)
    elif name == "Archäo-Profil":
        return _archaeo_profile(image)
    elif name == "NDVI-Proxy":
        return _ndvi_proxy(image)
    elif name == "Graustufen-Spreizung":
        return _gray_stretch(image)
    elif name == "Falschfarbe-HSV":
        return _hsv_rotation(image, params.get("hue_shift", 90))
    elif name == "Boden-Diff RG":
        return _channel_diff(image, 0, 1)
    elif name == "Boden-Diff RB":
        return _channel_diff(image, 0, 2)
    else:
        return image.copy()


# ──────────────────────────────────────────────
# Interne Implementierungen
# ──────────────────────────────────────────────

def _infrared_simulation(img: np.ndarray) -> np.ndarray:
    """Tauscht R und G-Kanal – simuliert Color-Infrared (CIR) Luftbild."""
    result = img.copy()
    result[:, :, 0] = img[:, :, 1]  # R ← G
    result[:, :, 1] = img[:, :, 0]  # G ← R
    return result


def _thermal(img: np.ndarray, colormap_id: int) -> np.ndarray:
    """Konvertiert zu Graustufen und wendet OpenCV-Colormap an."""
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    colored_bgr = cv2.applyColorMap(gray, colormap_id)
    return cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2RGB)


def _archaeo_profile(img: np.ndarray) -> np.ndarray:
    """
    Eigene archäologische Palette:
    Dunkle Bereiche (nass/tief) → Blau
    Mittlere Bereiche           → Gelb/Grün
    Helle Bereiche (anomal)     → Rot
    """
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0

    # Eigene Lookup-Tabelle erstellen (256 Einträge, RGB)
    lut = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        t = i / 255.0
        if t < 0.25:
            # Schwarz → Blau
            s = t / 0.25
            lut[i] = [int(0),       int(0),       int(s * 200)]
        elif t < 0.5:
            # Blau → Cyan/Grün
            s = (t - 0.25) / 0.25
            lut[i] = [int(0),       int(s * 200), int(200 - s * 100)]
        elif t < 0.75:
            # Grün → Gelb
            s = (t - 0.5) / 0.25
            lut[i] = [int(s * 220), int(200),     int(0)]
        else:
            # Gelb → Rot/Weiß (Anomalie)
            s = (t - 0.75) / 0.25
            lut[i] = [255,          int(220 - s * 220), int(s * 80)]

    idx = (gray * 255).astype(np.uint8)
    result = lut[idx]
    return result


def _ndvi_proxy(img: np.ndarray) -> np.ndarray:
    """
    NDVI-ähnlicher Vegetationsindex: (R–G)/(R+G+ε)
    Normiert auf [0,255], dann Jet-Colormap.
    """
    r = img[:, :, 0].astype(np.float32)
    g = img[:, :, 1].astype(np.float32)
    ndvi = (r - g) / (r + g + 1e-6)
    # Normieren auf [0, 255]
    ndvi_norm = ((ndvi + 1.0) / 2.0 * 255).clip(0, 255).astype(np.uint8)
    colored_bgr = cv2.applyColorMap(ndvi_norm, cv2.COLORMAP_RdYlGn
                                    if hasattr(cv2, 'COLORMAP_RdYlGn')
                                    else cv2.COLORMAP_JET)
    return cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2RGB)


def _gray_stretch(img: np.ndarray) -> np.ndarray:
    """Histogramm-Spreizung auf Graustufen (p2–p98)."""
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    p2, p98 = np.percentile(gray, 2), np.percentile(gray, 98)
    stretched = np.clip((gray.astype(np.float32) - p2) / (p98 - p2 + 1e-6) * 255, 0, 255).astype(np.uint8)
    return cv2.cvtColor(stretched, cv2.COLOR_GRAY2RGB)


def _hsv_rotation(img: np.ndarray, hue_shift: int = 90) -> np.ndarray:
    """Rotiert den Hue-Kanal im HSV-Raum um hue_shift Grad."""
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.int32)
    hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 180
    hsv = hsv.astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def _channel_diff(img: np.ndarray, ch_a: int, ch_b: int) -> np.ndarray:
    """
    Differenzbild zweier Kanäle, normiert und mit Jet-Colormap.
    Hebt subtile Bodenfärbungsunterschiede hervor.
    """
    a = img[:, :, ch_a].astype(np.float32)
    b = img[:, :, ch_b].astype(np.float32)
    diff = a - b
    diff_norm = ((diff - diff.min()) / (diff.max() - diff.min() + 1e-6) * 255).astype(np.uint8)
    colored_bgr = cv2.applyColorMap(diff_norm, cv2.COLORMAP_JET)
    return cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2RGB)
