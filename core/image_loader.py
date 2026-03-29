"""
image_loader.py – Lädt Bilder (JPG, GIF, PNG) und normalisiert sie für die Verarbeitung.
"""
import numpy as np
from PIL import Image
import cv2


SUPPORTED_FORMATS = (".jpg", ".jpeg", ".gif", ".png", ".tif", ".tiff")


def load_image(path: str) -> np.ndarray:
    """
    Lädt ein Bild von Disk und gibt es als uint8-RGB-NumPy-Array zurück.
    GIF: erstes Frame wird verwendet.
    """
    img = Image.open(path)

    # GIF: erstes Frame extrahieren
    if hasattr(img, "n_frames") and img.n_frames > 1:
        img.seek(0)

    # RGBA → RGB
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    return np.array(img, dtype=np.uint8)


def normalize_to_float(image: np.ndarray) -> np.ndarray:
    """Gibt float32-Array mit Werten [0.0, 1.0] zurück."""
    return image.astype(np.float32) / 255.0


def float_to_uint8(image: np.ndarray) -> np.ndarray:
    """Konvertiert float32 [0,1] zurück zu uint8 [0,255]."""
    return np.clip(image * 255.0, 0, 255).astype(np.uint8)


def resize_for_preview(image: np.ndarray, max_size: int = 1200) -> np.ndarray:
    """Skaliert das Bild für die GUI-Vorschau herunter, behält Seitenverhältnis."""
    h, w = image.shape[:2]
    if max(h, w) <= max_size:
        return image
    scale = max_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
