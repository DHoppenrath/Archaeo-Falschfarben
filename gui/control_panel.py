"""
control_panel.py – Einstellungs-Sidebar mit allen Analyseparametern.
"""
import base64
import os
import tempfile
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSlider, QCheckBox, QPushButton, QGroupBox, QDoubleSpinBox,
    QSpinBox, QSizePolicy, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.colormap_engine import COLORMAPS
from core.edge_detector import EDGE_METHODS


SPECIAL_FILTERS = {
    "Keiner":               "Kein Spezialfilter",
    "Crop-Mark":            "Bewuchsmerkmale auf Luftbildern",
    "Soil-Mark":            "Bodenverfärbungen nach Regen",
    "Schatten-Relief":      "Mikrotopographie (Hillshade)",
}

CHANNEL_OPTIONS = ["R", "G", "B"]


class ControlPanel(QWidget):
    """Sidebar mit allen Steuerelementen. Sendet settings_changed wenn etwas geändert wird."""

    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        # SVG-Haken in ASCII-Temp-Pfad schreiben (Qt url() versteht keine data: URIs)
        _svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 14"><polyline points="2,8 6,12 12,2" stroke="#e94560" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        _check_path = os.path.join(tempfile.gettempdir(), "archao_check.svg").replace("\\", "/")
        with open(_check_path, "wb") as _f:
            _f.write(_svg)
        self._check_path = _check_path
        self.setStyleSheet("""
            QWidget { background-color: #16213e; color: #e0e0e0; }
            QGroupBox {
                border: 1px solid #0f3460;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 6px;
                font-weight: bold;
                color: #e94560;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #0f3460;
                color: white;
                border: 1px solid #e94560;
                border-radius: 3px;
                padding: 2px 6px;
            }
            QSlider::groove:horizontal {
                background: #0f3460; height: 4px; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #e94560; width: 14px; height: 14px;
                margin: -5px 0; border-radius: 7px;
            }
            QPushButton {
                background-color: #0f3460;
                color: white;
                border: 1px solid #e94560;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover { background-color: #e94560; }
            QCheckBox { color: #e0e0e0; spacing: 6px; }
            QCheckBox::indicator {
                width: 15px; height: 15px;
                border: 2px solid #e94560;
                border-radius: 3px;
                background-color: #0f3460;
            }
            QCheckBox::indicator:hover { border-color: #ff6b81; }
        """)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; }
            QScrollBar:vertical {
                background: #0a1628;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #e94560;
                min-height: 24px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover { background: #ff6b81; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Colormap ───────────────────────────────────────────────
        grp_cm = QGroupBox("Falschfarben-Colormap")
        v_cm = QVBoxLayout(grp_cm)
        self.cb_colormap = QComboBox()
        for name, desc in COLORMAPS.items():
            self.cb_colormap.addItem(name)
        self.lbl_cm_desc = QLabel()
        self.lbl_cm_desc.setWordWrap(True)
        self.lbl_cm_desc.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        v_cm.addWidget(self.cb_colormap)
        v_cm.addWidget(self.lbl_cm_desc)
        self.cb_colormap.currentTextChanged.connect(self._on_colormap_changed)
        layout.addWidget(grp_cm)

        # ── Kanal-Mapping ──────────────────────────────────────────
        grp_ch = QGroupBox("Kanal-Mapping")
        grid_ch = QVBoxLayout(grp_ch)
        self.ch_r = self._make_channel_row("R ←", grid_ch, 0)
        self.ch_g = self._make_channel_row("G ←", grid_ch, 1)
        self.ch_b = self._make_channel_row("B ←", grid_ch, 2)
        self.chk_inv_r = QCheckBox("R invertieren")
        self.chk_inv_g = QCheckBox("G invertieren")
        self.chk_inv_b = QCheckBox("B invertieren")
        for chk in [self.chk_inv_r, self.chk_inv_g, self.chk_inv_b]:
            grid_ch.addWidget(chk)
            chk.toggled.connect(self._emit)
        layout.addWidget(grp_ch)

        # ── Kontrast ───────────────────────────────────────────────
        grp_con = QGroupBox("Kontrast & Helligkeit")
        v_con = QVBoxLayout(grp_con)

        self.chk_clahe = QCheckBox("CLAHE aktivieren")
        self.chk_clahe.setChecked(False)
        v_con.addWidget(self.chk_clahe)
        self.chk_clahe.toggled.connect(self._emit)

        v_con.addWidget(QLabel("CLAHE Clip-Limit:"))
        self.spin_clahe_clip = QDoubleSpinBox()
        self.spin_clahe_clip.setRange(0.5, 8.0)
        self.spin_clahe_clip.setSingleStep(0.5)
        self.spin_clahe_clip.setValue(2.0)
        v_con.addWidget(self.spin_clahe_clip)
        self.spin_clahe_clip.valueChanged.connect(self._emit)

        v_con.addWidget(QLabel("Kachelgröße:"))
        self.spin_clahe_tile = QSpinBox()
        self.spin_clahe_tile.setRange(4, 32)
        self.spin_clahe_tile.setSingleStep(4)
        self.spin_clahe_tile.setValue(8)
        v_con.addWidget(self.spin_clahe_tile)
        self.spin_clahe_tile.valueChanged.connect(self._emit)

        self.chk_hist = QCheckBox("Histogramm-Spreizung")
        v_con.addWidget(self.chk_hist)
        self.chk_hist.toggled.connect(self._emit)

        v_con.addWidget(QLabel("Untere Grenze (%):"))
        self.spin_hist_low = QDoubleSpinBox()
        self.spin_hist_low.setRange(0.0, 20.0)
        self.spin_hist_low.setValue(2.0)
        v_con.addWidget(self.spin_hist_low)
        self.spin_hist_low.valueChanged.connect(self._emit)

        v_con.addWidget(QLabel("Obere Grenze (%):"))
        self.spin_hist_high = QDoubleSpinBox()
        self.spin_hist_high.setRange(80.0, 100.0)
        self.spin_hist_high.setValue(98.0)
        v_con.addWidget(self.spin_hist_high)
        self.spin_hist_high.valueChanged.connect(self._emit)

        v_con.addWidget(QLabel("Gamma:"))
        self.spin_gamma = QDoubleSpinBox()
        self.spin_gamma.setRange(0.1, 5.0)
        self.spin_gamma.setSingleStep(0.1)
        self.spin_gamma.setValue(1.0)
        v_con.addWidget(self.spin_gamma)
        self.spin_gamma.valueChanged.connect(self._emit)

        self.chk_denoise = QCheckBox("Entrauschung")
        v_con.addWidget(self.chk_denoise)
        self.chk_denoise.toggled.connect(self._emit)

        v_con.addWidget(QLabel("Entrauschungs-Stärke:"))
        self.sld_denoise = QSlider(Qt.Orientation.Horizontal)
        self.sld_denoise.setRange(3, 15)
        self.sld_denoise.setValue(7)
        v_con.addWidget(self.sld_denoise)
        self.sld_denoise.valueChanged.connect(self._emit)

        layout.addWidget(grp_con)

        # ── Kantendetektion ────────────────────────────────────────
        grp_edge = QGroupBox("Kantendetektion")
        v_edge = QVBoxLayout(grp_edge)

        self.chk_edges = QCheckBox("Kanten anzeigen")
        v_edge.addWidget(self.chk_edges)
        self.chk_edges.toggled.connect(self._emit)

        v_edge.addWidget(QLabel("Methode:"))
        self.cb_edge_method = QComboBox()
        for name in EDGE_METHODS:
            self.cb_edge_method.addItem(name)
        v_edge.addWidget(self.cb_edge_method)
        self.cb_edge_method.currentTextChanged.connect(self._emit)

        v_edge.addWidget(QLabel("Stärke:"))
        self.sld_edge_str = QSlider(Qt.Orientation.Horizontal)
        self.sld_edge_str.setRange(1, 30)
        self.sld_edge_str.setValue(10)
        v_edge.addWidget(self.sld_edge_str)
        self.sld_edge_str.valueChanged.connect(self._emit)

        v_edge.addWidget(QLabel("Canny Low-Threshold:"))
        self.spin_canny_low = QSpinBox()
        self.spin_canny_low.setRange(1, 254)
        self.spin_canny_low.setValue(50)
        v_edge.addWidget(self.spin_canny_low)
        self.spin_canny_low.valueChanged.connect(self._emit)

        v_edge.addWidget(QLabel("Canny High-Threshold:"))
        self.spin_canny_high = QSpinBox()
        self.spin_canny_high.setRange(2, 255)
        self.spin_canny_high.setValue(150)
        v_edge.addWidget(self.spin_canny_high)
        self.spin_canny_high.valueChanged.connect(self._emit)

        layout.addWidget(grp_edge)

        # ── Spezialfilter ──────────────────────────────────────────
        grp_spec = QGroupBox("Archäo-Spezialfilter")
        v_spec = QVBoxLayout(grp_spec)
        self.cb_special = QComboBox()
        for name in SPECIAL_FILTERS:
            self.cb_special.addItem(name)
        self.lbl_spec_desc = QLabel()
        self.lbl_spec_desc.setWordWrap(True)
        self.lbl_spec_desc.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        v_spec.addWidget(self.cb_special)
        v_spec.addWidget(self.lbl_spec_desc)
        self.cb_special.currentTextChanged.connect(self._on_special_changed)
        layout.addWidget(grp_spec)

        layout.addStretch()

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # Checked-Stil mit Haken-SVG aus Temp-Pfad
        _chk_style = (
            "QCheckBox::indicator:checked {"
            f" background-color: #0f3460; border: 2px solid #e94560;"
            f" border-radius: 3px; image: url({self._check_path}); }}"
        )
        for chk in (self.chk_inv_r, self.chk_inv_g, self.chk_inv_b,
                    self.chk_clahe, self.chk_hist, self.chk_denoise, self.chk_edges):
            chk.setStyleSheet(_chk_style)

        # Initialbeschreibung setzen
        self._on_colormap_changed(self.cb_colormap.currentText())
        self._on_special_changed(self.cb_special.currentText())

    # ──────────────────────────────────────────────
    # Öffentliche API
    # ──────────────────────────────────────────────

    def get_settings(self) -> dict:
        return {
            "colormap":     self.cb_colormap.currentText(),
            "remap_r":      self.ch_r.currentIndex(),
            "remap_g":      self.ch_g.currentIndex(),
            "remap_b":      self.ch_b.currentIndex(),
            "invert_r":     self.chk_inv_r.isChecked(),
            "invert_g":     self.chk_inv_g.isChecked(),
            "invert_b":     self.chk_inv_b.isChecked(),
            "clahe":        self.chk_clahe.isChecked(),
            "clahe_clip":   self.spin_clahe_clip.value(),
            "clahe_tile":   self.spin_clahe_tile.value(),
            "hist_stretch": self.chk_hist.isChecked(),
            "hist_low":     self.spin_hist_low.value(),
            "hist_high":    self.spin_hist_high.value(),
            "gamma":        self.spin_gamma.value(),
            "denoise":      self.chk_denoise.isChecked(),
            "denoise_str":  self.sld_denoise.value(),
            "edges":        self.chk_edges.isChecked(),
            "edge_method":  self.cb_edge_method.currentText(),
            "edge_strength":self.sld_edge_str.value() / 10.0,
            "edge_low":     self.spin_canny_low.value(),
            "edge_high":    self.spin_canny_high.value(),
            "special":      self.cb_special.currentText(),
        }

    def apply_settings(self, s: dict) -> None:
        """Füllt alle Controls aus einem gespeicherten Settings-Dict."""
        self.cb_colormap.setCurrentText(s.get("colormap", "Original"))
        self.ch_r.setCurrentIndex(s.get("remap_r", 0))
        self.ch_g.setCurrentIndex(s.get("remap_g", 1))
        self.ch_b.setCurrentIndex(s.get("remap_b", 2))
        self.chk_inv_r.setChecked(s.get("invert_r", False))
        self.chk_inv_g.setChecked(s.get("invert_g", False))
        self.chk_inv_b.setChecked(s.get("invert_b", False))
        self.chk_clahe.setChecked(s.get("clahe", False))
        self.spin_clahe_clip.setValue(s.get("clahe_clip", 2.0))
        self.spin_clahe_tile.setValue(s.get("clahe_tile", 8))
        self.chk_hist.setChecked(s.get("hist_stretch", False))
        self.spin_hist_low.setValue(s.get("hist_low", 2.0))
        self.spin_hist_high.setValue(s.get("hist_high", 98.0))
        self.spin_gamma.setValue(s.get("gamma", 1.0))
        self.chk_denoise.setChecked(s.get("denoise", False))
        self.sld_denoise.setValue(s.get("denoise_str", 7))
        self.chk_edges.setChecked(s.get("edges", False))
        self.cb_edge_method.setCurrentText(s.get("edge_method", "Canny"))
        self.sld_edge_str.setValue(int(s.get("edge_strength", 1.0) * 10))
        self.spin_canny_low.setValue(s.get("edge_low", 50))
        self.spin_canny_high.setValue(s.get("edge_high", 150))
        self.cb_special.setCurrentText(s.get("special", "Keiner"))

    # ──────────────────────────────────────────────
    # Private Slots
    # ──────────────────────────────────────────────

    def _on_colormap_changed(self, name: str):
        self.lbl_cm_desc.setText(COLORMAPS.get(name, ""))
        self._emit()

    def _on_special_changed(self, name: str):
        self.lbl_spec_desc.setText(SPECIAL_FILTERS.get(name, ""))
        self._emit()

    def _emit(self, *_):
        self.settings_changed.emit(self.get_settings())

    def _make_channel_row(self, label: str, layout: QVBoxLayout, default: int) -> QComboBox:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(40)
        cb = QComboBox()
        for ch in CHANNEL_OPTIONS:
            cb.addItem(ch)
        cb.setCurrentIndex(default)
        cb.currentIndexChanged.connect(self._emit)
        row.addWidget(lbl)
        row.addWidget(cb)
        layout.addLayout(row)
        return cb
