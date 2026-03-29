"""
main_window.py – Hauptfenster der ArchäoFalschfarben-Anwendung.
"""
import os
import re
import json
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox, QStatusBar, QToolBar,
    QLabel, QProgressBar, QProgressDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QDragEnterEvent, QDropEvent

from core.image_loader import load_image, resize_for_preview, SUPPORTED_FORMATS
from core.colormap_engine import apply_colormap
from core.band_manipulator import remap_channels, invert_channels
from core.enhancement import apply_clahe, histogram_stretch, gamma_correction, denoise
from core.edge_detector import detect_edges, overlay_edges
from core.special_filters import (
    crop_mark_enhancement, soil_mark_enhancement, shadow_enhancement
)
from core.exporter import save_image
from gui.preview_canvas import PreviewCanvas
from gui.control_panel import ControlPanel

PRESETS_FILE = os.path.join(os.path.dirname(__file__), "..", "presets", "profiles.json")


class PdfWorker(QObject):
    """PDF-Erzeugung im Hintergrundthread."""
    progress = pyqtSignal(int, str)   # (aktueller Schritt, Beschreibung)
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, original, result, settings, path, include_all):
        super().__init__()
        self._original    = original
        self._result      = result
        self._settings    = settings
        self._path        = path
        self._include_all = include_all

    def run(self):
        try:
            from core.colormap_engine import COLORMAPS
            if self._include_all:
                # Schritt 1..N: Colormaps berechnen
                colormap_names = [n for n in COLORMAPS if n != "Original"]
                total = len(colormap_names) + 1   # +1 fuer PDF-Render
                results = {}
                for i, name in enumerate(colormap_names):
                    self.progress.emit(i, f"Berechne: {name}")
                    s = dict(self._settings)
                    s["colormap"] = name
                    s["special"]  = "Keiner"
                    results[name] = _process_pipeline(self._original.copy(), s)
                self.progress.emit(len(colormap_names), "Erstelle PDF...")
                from core.exporter import export_pdf_report_all
                export_pdf_report_all(self._original, results, self._settings, self._path)
                self.progress.emit(total, "Fertig")
            else:
                self.progress.emit(0, "Erstelle PDF...")
                from core.exporter import export_pdf_report
                export_pdf_report(self._original, self._result, self._settings, self._path)
                self.progress.emit(1, "Fertig")
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class ProcessWorker(QObject):
    """Verarbeitung in eigenem Thread, damit die GUI nicht einfriert."""
    finished = pyqtSignal(np.ndarray)
    error = pyqtSignal(str)

    def __init__(self, image: np.ndarray, settings: dict):
        super().__init__()
        self._image = image
        self._settings = settings

    def run(self):
        try:
            result = _process_pipeline(self._image, self._settings)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArchäoFalschfarben – Archäologische Bildanalyse")
        self.setMinimumSize(1024, 680)
        self.resize(1280, 800)
        self.setAcceptDrops(True)

        self._original: np.ndarray | None = None
        self._current_file: str = ""
        self._worker_thread: QThread | None = None
        self._first_result_for_file: bool = True

        self._build_ui()
        self._build_menu()
        self._build_toolbar()

        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; }
            QMenuBar { background-color: #0f3460; color: white; }
            QMenuBar::item:selected { background-color: #e94560; }
            QMenu { background-color: #0f3460; color: white; }
            QMenu::item:selected { background-color: #e94560; }
            QStatusBar { background-color: #0f3460; color: #e0e0e0; }
            QStatusBar QLabel { color: #e0e0e0; }
            QToolBar { background-color: #0f3460; border: none; spacing: 4px; }
            QToolButton { color: white; padding: 4px 8px; }
            QToolButton:hover { background-color: #e94560; border-radius: 3px; }
        """)

    # ──────────────────────────────────────────────
    # UI-Aufbau
    # ──────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Control Panel links
        self.control_panel = ControlPanel()
        self.control_panel.settings_changed.connect(self._on_settings_changed)
        main_layout.addWidget(self.control_panel)

        # Canvas rechts
        self.canvas = PreviewCanvas()
        main_layout.addWidget(self.canvas, stretch=1)

        # Statusbar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._lbl_status = QLabel("Bereit. Bild öffnen oder Drag & Drop.")
        self._lbl_status.setStyleSheet("color: #e0e0e0;")
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMaximumWidth(150)
        self._progress.setRange(0, 0)  # indeterminate
        self.status_bar.addWidget(self._lbl_status, 1)
        self.status_bar.addPermanentWidget(self._progress)

    def _build_menu(self):
        mb = self.menuBar()

        # Datei
        m_file = mb.addMenu("&Datei")
        act_open = QAction("&Öffnen…", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self.open_image)
        m_file.addAction(act_open)

        m_file.addSeparator()

        act_save = QAction("Ergebnis speichern (PNG)…", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self.save_result_png)
        m_file.addAction(act_save)

        act_save_tiff = QAction("Ergebnis speichern (TIFF)…", self)
        act_save_tiff.triggered.connect(self.save_result_tiff)
        m_file.addAction(act_save_tiff)

        act_pdf = QAction("PDF-Report exportieren…", self)
        act_pdf.triggered.connect(self.export_pdf)
        m_file.addAction(act_pdf)

        m_file.addSeparator()
        act_quit = QAction("&Beenden", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

        # Presets
        m_pre = mb.addMenu("&Presets")
        act_save_pre = QAction("Aktuelles Preset speichern…", self)
        act_save_pre.triggered.connect(self.save_preset)
        m_pre.addAction(act_save_pre)

        act_load_pre = QAction("Preset laden…", self)
        act_load_pre.triggered.connect(self.load_preset)
        m_pre.addAction(act_load_pre)

        # Ansicht
        m_view = mb.addMenu("&Ansicht")
        act_reset = QAction("Zoom zurücksetzen", self)
        act_reset.setShortcut("Ctrl+0")
        act_reset.triggered.connect(self.canvas.reset_zoom)
        m_view.addAction(act_reset)

        # Hilfe
        m_help = mb.addMenu("&Hilfe")
        act_about = QAction("Über ArchäoFalschfarben", self)
        act_about.triggered.connect(self._show_about)
        m_help.addAction(act_about)

    def _build_toolbar(self):
        tb = QToolBar("Werkzeuge")
        tb.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        act_open = QAction("📂 Öffnen", self)
        act_open.triggered.connect(self.open_image)
        tb.addAction(act_open)

        act_save = QAction("💾 PNG", self)
        act_save.triggered.connect(self.save_result_png)
        tb.addAction(act_save)

        act_pdf = QAction("📄 PDF-Report", self)
        act_pdf.triggered.connect(self.export_pdf)
        tb.addAction(act_pdf)

        tb.addSeparator()

        act_reset = QAction("🔍 Zoom Reset", self)
        act_reset.triggered.connect(self.canvas.reset_zoom)
        tb.addAction(act_reset)

    # ──────────────────────────────────────────────
    # Aktionen
    # ──────────────────────────────────────────────

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Bild öffnen", "",
            "Bilder (*.jpg *.jpeg *.png *.gif *.tif *.tiff);;Alle Dateien (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        try:
            self._original = load_image(path)
            self._current_file = path
            self._first_result_for_file = True
            fname = os.path.basename(path)
            h, w = self._original.shape[:2]
            self._lbl_status.setText(f"{fname}  ({w}×{h} px)")
            self._trigger_processing()
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Laden", str(e))

    def save_result_png(self):
        self._save_result("PNG-Bild (*.png)", ".png")

    def save_result_tiff(self):
        self._save_result("TIFF-Bild (*.tif *.tiff)", ".tif")

    def _make_save_suggestion(self, ext: str) -> str:
        """Schlägt einen Dateinamen vor: originalname_ColormapName.ext"""
        if not self._current_file:
            return ""
        base, _ = os.path.splitext(self._current_file)
        settings = self.control_panel.get_settings()
        special = settings.get("special", "Keiner")
        label = special if special != "Keiner" else settings.get("colormap", "")
        suffix = re.sub(r'[^\w]', '_', label)
        suffix = re.sub(r'_+', '_', suffix).strip('_')
        return f"{base}_{suffix}{ext}" if suffix else f"{base}{ext}"

    def _save_result(self, filter_str: str, default_ext: str):
        if self._original is None or self.canvas._result is None:
            QMessageBox.warning(self, "Kein Ergebnis", "Zuerst ein Bild laden.")
            return
        suggestion = self._make_save_suggestion(default_ext)
        path, _ = QFileDialog.getSaveFileName(self, "Ergebnis speichern", suggestion, filter_str)
        if path:
            if not any(path.endswith(e) for e in [".png", ".tif", ".tiff"]):
                path += default_ext
            save_image(self.canvas._result, path)
            self._lbl_status.setText(f"Gespeichert: {os.path.basename(path)}")

    def export_pdf(self):
        if self._original is None or self.canvas._result is None:
            QMessageBox.warning(self, "Kein Ergebnis", "Zuerst ein Bild laden.")
            return

        # Dialog: aktuelle Colormap oder alle
        msg = QMessageBox(self)
        msg.setWindowTitle("PDF-Report")
        msg.setText("Welche Colormaps sollen in den Report?")
        btn_current = msg.addButton("Aktuelle Colormap", QMessageBox.ButtonRole.AcceptRole)
        btn_all     = msg.addButton("Alle Colormaps",    QMessageBox.ButtonRole.AcceptRole)
        btn_cancel  = msg.addButton("Abbrechen",         QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked is btn_cancel or clicked is None:
            return
        include_all = (clicked is btn_all)

        base = os.path.splitext(self._current_file)[0] if self._current_file else ""
        suggestion = f"{base}_{'alle_colormaps' if include_all else 'report'}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "PDF-Report speichern", suggestion, "PDF (*.pdf)"
        )
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"

        settings = self.control_panel.get_settings()
        settings["source_file"] = os.path.basename(self._current_file)

        from core.colormap_engine import COLORMAPS
        total_steps = (len(COLORMAPS) - 1 + 1) if include_all else 1  # +1 fuer PDF-Render

        # Fortschrittsdialog (modal, nicht abbrechbar)
        dlg = QProgressDialog("PDF wird erstellt...", None, 0, total_steps, self)
        dlg.setWindowTitle("PDF-Export")
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.setMinimumDuration(0)
        dlg.setAutoClose(True)
        dlg.setStyleSheet("""
            QProgressDialog { background-color: #16213e; color: white; }
            QLabel           { color: white; font-size: 11px; }
            QProgressBar {
                background: #0f3460; border: 1px solid #e94560;
                border-radius: 4px; text-align: center; color: white;
            }
            QProgressBar::chunk { background-color: #e94560; border-radius: 3px; }
        """)
        dlg.setValue(0)

        # Worker-Thread
        self._pdf_worker = PdfWorker(
            self._original.copy(),
            self.canvas._result.copy() if self.canvas._result is not None else None,
            settings, path, include_all
        )
        self._pdf_thread = QThread()
        self._pdf_worker.moveToThread(self._pdf_thread)
        self._pdf_thread.started.connect(self._pdf_worker.run)
        self._pdf_worker.progress.connect(
            lambda step, label: (dlg.setValue(step), dlg.setLabelText(label))
        )
        self._pdf_worker.finished.connect(self._pdf_thread.quit)
        self._pdf_worker.error.connect(self._pdf_thread.quit)
        self._pdf_worker.finished.connect(
            lambda: self._lbl_status.setText(f"PDF exportiert: {os.path.basename(path)}")
        )
        self._pdf_worker.error.connect(
            lambda msg: QMessageBox.critical(self, "Export-Fehler", msg)
        )
        self._pdf_worker.finished.connect(dlg.close)
        self._pdf_worker.error.connect(dlg.close)
        self._pdf_thread.start()
        dlg.exec()    # blockiert GUI-Eventloop (zeigt Dialog), aber nicht den Render-Thread

    def save_preset(self):
        os.makedirs(os.path.dirname(PRESETS_FILE), exist_ok=True)
        settings = self.control_panel.get_settings()
        name, ok = self._ask_text("Preset-Name", "Name für das Preset:")
        if not ok or not name:
            return
        presets = self._load_presets_file()
        presets[name] = settings
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
        self._lbl_status.setText(f"Preset '{name}' gespeichert.")

    def load_preset(self):
        presets = self._load_presets_file()
        if not presets:
            QMessageBox.information(self, "Keine Presets", "Noch keine Presets gespeichert.")
            return
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(
            self, "Preset laden", "Preset auswählen:",
            list(presets.keys()), 0, False
        )
        if ok and name in presets:
            self.control_panel.apply_settings(presets[name])
            self._lbl_status.setText(f"Preset '{name}' geladen.")

    # ──────────────────────────────────────────────
    # Verarbeitung
    # ──────────────────────────────────────────────

    def _on_settings_changed(self, settings: dict):
        if self._original is not None:
            self._trigger_processing()

    def _trigger_processing(self):
        if self._original is None:
            return
        if self._worker_thread and self._worker_thread.isRunning():
            return  # Abbruch: läuft noch

        settings = self.control_panel.get_settings()
        self._progress.setVisible(True)

        self._worker = ProcessWorker(self._original.copy(), settings)
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_processing_done)
        self._worker.error.connect(self._on_processing_error)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker_thread.start()

    def _on_processing_done(self, result: np.ndarray):
        self._progress.setVisible(False)
        preview_res = resize_for_preview(result)
        if self._first_result_for_file:
            # Erstes Ergebnis nach Datei-Laden: Originalvorschau setzen + Zoom reset
            preview_orig = resize_for_preview(self._original)
            self.canvas.set_images(preview_orig, preview_res)
            self._first_result_for_file = False
        else:
            # Einstellungsänderung: nur Ergebnis aktualisieren, Zoom/Pan erhalten
            self.canvas.set_result(preview_res)
        # Vollauflösung für Export merken
        self.canvas._result = result

    def _on_processing_error(self, msg: str):
        self._progress.setVisible(False)
        self._lbl_status.setText(f"Fehler: {msg}")

    # ──────────────────────────────────────────────
    # Drag & Drop
    # ──────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and any(
                urls[0].toLocalFile().lower().endswith(ext)
                for ext in SUPPORTED_FORMATS
            ):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            self._load_file(urls[0].toLocalFile())

    # ──────────────────────────────────────────────
    # Hilfsmethoden
    # ──────────────────────────────────────────────

    def _show_about(self):
        QMessageBox.about(
            self,
            "Über ArchäoFalschfarben",
            "<h3>ArchäoFalschfarben</h3>"
            "<p>Falschfarbenanalyse für archäologische Bodenstrukturen.</p>"
            "<p>Erkennung von Bewuchsmerkmalen, Bodenverfärbungen "
            "und Mikrotopographie in Luftbildern.</p>"
            "<p><b>Stack:</b> Python · OpenCV · PyQt6 · scikit-image</p>"
        )

    def _ask_text(self, title: str, label: str):
        from PyQt6.QtWidgets import QInputDialog
        return QInputDialog.getText(self, title, label)

    def _load_presets_file(self) -> dict:
        if os.path.exists(PRESETS_FILE):
            try:
                with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline-Funktion (außerhalb der Klasse, läuft im Worker-Thread)
# ──────────────────────────────────────────────────────────────────────────────

def _process_pipeline(image: np.ndarray, s: dict) -> np.ndarray:
    """
    Führt die komplette Verarbeitungs-Pipeline in der richtigen Reihenfolge aus:
    1. Entrauschung
    2. Kanal-Remapping
    3. Kanal-Invertierung
    4. Histogramm-Spreizung
    5. CLAHE
    6. Gamma-Korrektur
    7. Spezialfilter ODER Colormap
    8. Kantendetektion + Overlay
    """
    img = image.copy()

    # 1. Entrauschung
    if s.get("denoise"):
        img = denoise(img, s.get("denoise_str", 7))

    # 2. Kanal-Remapping
    r_src = s.get("remap_r", 0)
    g_src = s.get("remap_g", 1)
    b_src = s.get("remap_b", 2)
    if (r_src, g_src, b_src) != (0, 1, 2):
        img = remap_channels(img, r_src, g_src, b_src)

    # 3. Kanal-Invertierung
    if s.get("invert_r") or s.get("invert_g") or s.get("invert_b"):
        img = invert_channels(img,
                              s.get("invert_r", False),
                              s.get("invert_g", False),
                              s.get("invert_b", False))

    # 4. Histogramm-Spreizung
    if s.get("hist_stretch"):
        img = histogram_stretch(img, s.get("hist_low", 2.0), s.get("hist_high", 98.0))

    # 5. CLAHE
    if s.get("clahe"):
        img = apply_clahe(img, s.get("clahe_clip", 2.0), s.get("clahe_tile", 8))

    # 6. Gamma
    gamma = s.get("gamma", 1.0)
    if abs(gamma - 1.0) > 1e-3:
        img = gamma_correction(img, gamma)

    # 7. Spezialfilter oder Colormap
    special = s.get("special", "Keiner")
    if special == "Crop-Mark":
        img = crop_mark_enhancement(img)
    elif special == "Soil-Mark":
        img = soil_mark_enhancement(img)
    elif special == "Schatten-Relief":
        img = shadow_enhancement(img)
    else:
        img = apply_colormap(img, s.get("colormap", "Original"))

    # 8. Kantendetektion
    if s.get("edges"):
        edges = detect_edges(
            image,  # Kanten auf Original, nicht auf Falschfarbe
            method=s.get("edge_method", "Canny"),
            strength=s.get("edge_strength", 1.0),
            low_thresh=s.get("edge_low", 50),
            high_thresh=s.get("edge_high", 150),
        )
        img = overlay_edges(img, edges)

    return img
