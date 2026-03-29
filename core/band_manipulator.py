"""
band_manipulator.py – Freie RGB-Kanal-Umsortierung und Invertierung.
"""
import numpy as np


CHANNEL_NAMES = ["R", "G", "B"]


def remap_channels(image: np.ndarray,
                   r_src: int = 0,
                   g_src: int = 1,
                   b_src: int = 2) -> np.ndarray:
    """
    Ordnet die RGB-Kanäle frei neu zu.
    r_src, g_src, b_src: Index des Quellkanals (0=R, 1=G, 2=B)
    Gibt uint8 RGB zurück.
    """
    result = np.stack([
        image[:, :, r_src],
        image[:, :, g_src],
        image[:, :, b_src],
    ], axis=2)
    return result.astype(np.uint8)


def invert_channels(image: np.ndarray,
                    invert_r: bool = False,
                    invert_g: bool = False,
                    invert_b: bool = False) -> np.ndarray:
    """
    Invertiert einzelne Kanäle selektiv.
    """
    result = image.copy()
    if invert_r:
        result[:, :, 0] = 255 - result[:, :, 0]
    if invert_g:
        result[:, :, 1] = 255 - result[:, :, 1]
    if invert_b:
        result[:, :, 2] = 255 - result[:, :, 2]
    return result


def channel_weight_blend(image: np.ndarray,
                          w_r: float = 1.0,
                          w_g: float = 1.0,
                          w_b: float = 1.0) -> np.ndarray:
    """
    Multipliziert jeden Kanal mit einem Gewichtsfaktor [0.0 – 2.0].
    Nützlich zum Abschwächen oder Betonen einzelner Spektralbereiche.
    """
    result = image.astype(np.float32)
    result[:, :, 0] = np.clip(result[:, :, 0] * w_r, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] * w_g, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] * w_b, 0, 255)
    return result.astype(np.uint8)
