"""
special_filters.py – Archäologie-spezifische Spezialfilter.
Optimiert für Crop-Marks, Soil-Marks und Mikrotopographie.
"""
import numpy as np
import cv2


def crop_mark_enhancement(image: np.ndarray) -> np.ndarray:
    """
    Crop-Mark Enhancement: Optimiert für Bewuchsmerkmale auf Luftbildern.
    Strategie:
    1. CLAHE auf Grünkanal (Vegetation reagiert stärker)
    2. Differenz G–R als Vegetation-Proxy
    3. Morphologischer Top-Hat für lineare Strukturen
    """
    g = image[:, :, 1].copy()
    r = image[:, :, 0].copy()

    # Grünkanal CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    g_clahe = clahe.apply(g)

    # Differenz
    diff = cv2.subtract(g_clahe, r)

    # Top-Hat: lineare Strukturen (Gräben) hervorheben
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
    top_hat_h = cv2.morphologyEx(diff, cv2.MORPH_TOPHAT, kernel)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
    top_hat_v = cv2.morphologyEx(diff, cv2.MORPH_TOPHAT, kernel)
    top_hat = cv2.add(top_hat_h, top_hat_v)

    # Normieren und auf Jet-Colormap mappen
    norm = cv2.normalize(top_hat, None, 0, 255, cv2.NORM_MINMAX)
    colored_bgr = cv2.applyColorMap(norm.astype(np.uint8), cv2.COLORMAP_JET)
    return cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2RGB)


def soil_mark_enhancement(image: np.ndarray) -> np.ndarray:
    """
    Soil-Mark Enhancement: Bodenverfärbungen nach Regen oder Pflügen.
    Strategie:
    1. RGB → YCrCb
    2. Cr-Kanal (Rötlichkeit) CLAHE
    3. Cb-Kanal (Bläulichkeit) invertieren
    4. Kombination auf Custom-Colormap
    """
    ycrcb = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(16, 16))

    ycrcb[:, :, 1] = clahe.apply(ycrcb[:, :, 1])  # Cr
    ycrcb[:, :, 2] = clahe.apply(ycrcb[:, :, 2])  # Cb

    # Soil-Index: Cr – Cb (Rötlichkeit minus Bläulichkeit)
    cr = ycrcb[:, :, 1].astype(np.int16)
    cb = ycrcb[:, :, 2].astype(np.int16)
    soil_idx = np.clip(cr - cb + 128, 0, 255).astype(np.uint8)

    colored_bgr = cv2.applyColorMap(soil_idx, cv2.COLORMAP_INFERNO
                                    if hasattr(cv2, 'COLORMAP_INFERNO')
                                    else cv2.COLORMAP_HOT)
    return cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2RGB)


def shadow_enhancement(image: np.ndarray,
                        angle_deg: float = 315.0,
                        z_factor: float = 3.0) -> np.ndarray:
    """
    Shadow/Hillshade Enhancement: Mikrotopographie durch simuliertes Schrägbeleuchten.
    Nutzt den Helligkeitswert als Höhenmodell-Proxy.
    angle_deg: Beleuchtungswinkel (0°=N, 90°=E, 270°=W, 315°=NW – Standard)
    z_factor:  Überhöhungsfaktor [1–10], höher = dramatischere Schatteneffekte
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)

    # Auf 0-1 normieren als Pseudo-DEM
    dem = gray / 255.0

    # Sonnenpositon berechnen
    az_rad = np.radians(angle_deg)
    alt_rad = np.radians(45.0)

    # Gradient
    dz_dx = cv2.Sobel(dem, cv2.CV_32F, 1, 0, ksize=3)
    dz_dy = cv2.Sobel(dem, cv2.CV_32F, 0, 1, ksize=3)

    dz_dx *= z_factor
    dz_dy *= z_factor

    # Hillshade-Formel
    slope = np.sqrt(dz_dx**2 + dz_dy**2)
    aspect = np.arctan2(-dz_dy, dz_dx)

    hillshade = (
        np.cos(alt_rad) * np.cos(np.arctan(slope))
        + np.sin(alt_rad) * np.sin(np.arctan(slope))
        * np.cos(az_rad - aspect)
    )

    hillshade = np.clip(hillshade, 0, 1)
    hs_uint8 = (hillshade * 255).astype(np.uint8)

    # Kombination: Hillshade × Original für Details
    orig_f = image.astype(np.float32) / 255.0
    hs_rgb = np.stack([hillshade, hillshade, hillshade], axis=2)
    combined = np.clip(orig_f * hs_rgb * 1.8, 0, 1)
    return (combined * 255).astype(np.uint8)
