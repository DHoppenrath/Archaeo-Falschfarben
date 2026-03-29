"""
exporter.py – Export als PNG/TIFF und PDF-Report mit Legende und Parametern.
"""
import os
import math
import numpy as np
from PIL import Image
from datetime import datetime

# matplotlib wird lazy importiert (nur bei PDF-Export) – spart ~2-3s Startzeit


def save_image(image: np.ndarray, path: str) -> None:
    """Speichert uint8 RGB-Array als PNG oder TIFF."""
    img = Image.fromarray(image)
    img.save(path)


def export_pdf_report(original: np.ndarray,
                      result: np.ndarray,
                      params: dict,
                      output_path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    """
    Erstellt einen PDF-Report mit:
    - Originalbild (links)
    - Ergebnisbild (rechts)
    - Parameterübersicht
    - Zeitstempel und Legende
    params: dict mit allen angewendeten Einstellungen
    """
    fig = plt.figure(figsize=(16, 10), facecolor="#1a1a2e")

    gs = gridspec.GridSpec(2, 2,
                           height_ratios=[4, 1],
                           hspace=0.35,
                           wspace=0.15,
                           left=0.05, right=0.95,
                           top=0.88, bottom=0.05)

    # ── Titel ──────────────────────────────────────────────────────
    fig.text(0.5, 0.94,
             "ArchäoFalschfarben – Analysebericht",
             ha="center", va="top",
             fontsize=18, fontweight="bold",
             color="white", fontfamily="monospace")
    fig.text(0.5, 0.906,
             f"Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
             ha="center", va="top",
             fontsize=10, color="#aaaaaa")

    # ── Originalbild ───────────────────────────────────────────────
    ax_orig = fig.add_subplot(gs[0, 0])
    ax_orig.imshow(original)
    ax_orig.set_title("Original", color="white", fontsize=12, pad=6)
    ax_orig.axis("off")

    # ── Ergebnisbild ───────────────────────────────────────────────
    ax_res = fig.add_subplot(gs[0, 1])
    ax_res.imshow(result)
    colormap_name = params.get("colormap", "–")
    ax_res.set_title(f"Falschfarben: {colormap_name}", color="white", fontsize=12, pad=6)
    ax_res.axis("off")

    # ── Parameter-Tabelle ──────────────────────────────────────────
    ax_par = fig.add_subplot(gs[1, :])
    ax_par.axis("off")

    param_lines = _format_params(params)
    param_text = "\n".join(param_lines)
    ax_par.text(0.01, 0.95, param_text,
                transform=ax_par.transAxes,
                ha="left", va="top",
                fontsize=9, color="white",
                fontfamily="monospace",
                bbox=dict(boxstyle="round,pad=0.5",
                          facecolor="#0f3460",
                          edgecolor="#e94560",
                          linewidth=1.5))

    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)


def export_pdf_report_all(original: np.ndarray,
                          results_by_colormap: dict,
                          params: dict,
                          output_path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    """
    Erstellt einen PDF-Report mit Original vs. allen Colormaps in einem Raster.
    results_by_colormap: dict {colormap_name: uint8 RGB array}
    """
    items = list(results_by_colormap.items())  # [(name, img), ...]
    total = len(items) + 1                      # +1 fuer Original
    cols = 3
    img_rows = math.ceil(total / cols)

    fig_w = cols * 5.5
    fig_h = img_rows * 4.2 + 2.8              # Bildreihen + Params-Zeile + Titel
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="#1a1a2e")

    # ── Titel ──────────────────────────────────────────────────────
    fig.text(0.5, 0.99,
             "ArchaeoFalschfarben – Alle Colormaps",
             ha="center", va="top",
             fontsize=16, fontweight="bold",
             color="white", fontfamily="monospace")
    fig.text(0.5, 0.975,
             f"Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}   "
             f"| Quelle: {params.get('source_file', '–')}",
             ha="center", va="top",
             fontsize=9, color="#aaaaaa")

    title_frac = 0.055          # Titelbereich oben
    params_frac = 0.10          # Parameterbereich unten
    img_frac = 1.0 - title_frac - params_frac

    gs_imgs = gridspec.GridSpec(
        img_rows, cols,
        left=0.03, right=0.97,
        top=1.0 - title_frac,
        bottom=params_frac + 0.01,
        hspace=0.35, wspace=0.08,
    )
    gs_par = gridspec.GridSpec(
        1, 1,
        left=0.03, right=0.97,
        top=params_frac - 0.01,
        bottom=0.01,
    )

    # ── Original ───────────────────────────────────────────────────
    ax0 = fig.add_subplot(gs_imgs[0, 0])
    ax0.imshow(original)
    ax0.set_title("Original", color="white", fontsize=10, pad=4,
                  fontweight="bold")
    ax0.axis("off")
    # Rahmen hervorheben
    for spine in ax0.spines.values():
        spine.set_edgecolor("#e94560")
        spine.set_linewidth(2)
        spine.set_visible(True)

    # ── Colormaps ──────────────────────────────────────────────────
    for i, (name, img) in enumerate(items):
        idx = i + 1          # 0 = Original
        r, c = divmod(idx, cols)
        ax = fig.add_subplot(gs_imgs[r, c])
        ax.imshow(img)
        ax.set_title(name, color="#e0e0e0", fontsize=9, pad=4)
        ax.axis("off")

    # ── Leere Felder ausblenden ────────────────────────────────────
    for j in range(total, img_rows * cols):
        r, c = divmod(j, cols)
        fig.add_subplot(gs_imgs[r, c]).set_visible(False)

    # ── Parameter-Zeile ────────────────────────────────────────────
    ax_par = fig.add_subplot(gs_par[0, 0])
    ax_par.axis("off")
    param_lines = _format_params(params)
    ax_par.text(0.005, 0.98, "\n".join(param_lines),
                transform=ax_par.transAxes,
                ha="left", va="top",
                fontsize=7.5, color="white",
                fontfamily="monospace",
                bbox=dict(boxstyle="round,pad=0.4",
                          facecolor="#0f3460",
                          edgecolor="#e94560",
                          linewidth=1.2))

    plt.savefig(output_path, dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)


def _format_params(params: dict) -> list:
    """Formatiert Parameter-Dict als lesbare Zeilen."""
    lines = ["ANALYSE-PARAMETER", "─" * 60]
    labels = {
        "colormap":       "Colormap",
        "clahe":          "CLAHE aktiviert",
        "clahe_clip":     "CLAHE Clip-Limit",
        "clahe_tile":     "CLAHE Kachelgröße",
        "hist_stretch":   "Histogramm-Spreizung",
        "hist_low":       "Spreizung untere Grenze (%)",
        "hist_high":      "Spreizung obere Grenze (%)",
        "gamma":          "Gamma-Korrektur",
        "denoise":        "Entrauschung aktiviert",
        "denoise_str":    "Entrauschungs-Stärke",
        "edge_method":    "Kantendetektion",
        "edge_strength":  "Kantenstärke",
        "edge_low":       "Canny Low-Threshold",
        "edge_high":      "Canny High-Threshold",
        "remap_r":        "Kanal R ← Quelle",
        "remap_g":        "Kanal G ← Quelle",
        "remap_b":        "Kanal B ← Quelle",
        "source_file":    "Quelldatei",
    }
    for key, label in labels.items():
        if key in params:
            lines.append(f"  {label:<30} {params[key]}")
    return lines
