"""
preview_canvas.py – Bild-Anzeige mit Split-View, Zoom und Pan.
"""
import numpy as np
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QCursor


class PreviewCanvas(QWidget):
    """
    Zeigt Original und Ergebnis-Bild nebeneinander mit vertikalem Split-Schieberegler.
    Unterstützt Zoom (Mausrad) und Pan (Linksklick + Drag).
    """

    split_changed = pyqtSignal(float)  # 0.0–1.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

        self._original: np.ndarray | None = None
        self._result: np.ndarray | None = None
        self._px_original: QPixmap | None = None
        self._px_result: QPixmap | None = None

        self._split_pos: float = 0.5      # 0.0–1.0 relativ zur Breite
        self._dragging_split: bool = False

        self._zoom: float = 1.0
        self._offset: QPoint = QPoint(0, 0)
        self._pan_start: QPoint | None = None
        self._pan_offset_start: QPoint | None = None

        self.setStyleSheet("background-color: #1a1a2e;")

    # ──────────────────────────────────────────────
    # Öffentliche API
    # ──────────────────────────────────────────────

    def set_images(self, original: np.ndarray, result: np.ndarray) -> None:
        self._original = original
        self._result = result
        self._px_original = self._to_pixmap(original)
        self._px_result = self._to_pixmap(result)
        self._fit_to_canvas()
        self.update()

    def set_result(self, result: np.ndarray) -> None:
        self._result = result
        self._px_result = self._to_pixmap(result)
        self.update()

    def reset_zoom(self) -> None:
        self._fit_to_canvas()
        self.update()

    # ──────────────────────────────────────────────
    # Events
    # ──────────────────────────────────────────────

    def paintEvent(self, event):
        if self._px_original is None:
            self._draw_placeholder()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        split_x = int(w * self._split_pos)

        # Gesamtbildgröße skaliert
        img_w = int(self._px_original.width() * self._zoom)
        img_h = int(self._px_original.height() * self._zoom)
        ox = self._offset.x()
        oy = self._offset.y()

        # ── Linke Seite: Original ──────────────────
        painter.setClipRect(QRect(0, 0, split_x, h))
        painter.drawPixmap(ox, oy, img_w, img_h, self._px_original)

        # ── Rechte Seite: Ergebnis ─────────────────
        painter.setClipRect(QRect(split_x, 0, w - split_x, h))
        if self._px_result:
            painter.drawPixmap(ox, oy, img_w, img_h, self._px_result)

        # ── Split-Linie ────────────────────────────
        painter.setClipping(False)
        pen = QPen(QColor("#e94560"), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawLine(split_x, 0, split_x, h)

        # ── Labels ─────────────────────────────────
        painter.setPen(QColor("white"))
        painter.drawText(10, 20, "Original")
        painter.drawText(split_x + 10, 20, "Falschfarben")

        painter.end()

    def mousePressEvent(self, event):
        split_x = int(self.width() * self._split_pos)
        if abs(event.position().x() - split_x) < 8:
            self._dragging_split = True
            self.setCursor(QCursor(Qt.CursorShape.SplitHCursor))
        elif event.button() == Qt.MouseButton.LeftButton:
            self._pan_start = event.position().toPoint()
            self._pan_offset_start = QPoint(self._offset)
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

    def mouseMoveEvent(self, event):
        if self._dragging_split:
            self._split_pos = max(0.05, min(0.95,
                event.position().x() / self.width()))
            self.split_changed.emit(self._split_pos)
            self.update()
        elif self._pan_start is not None:
            delta = event.position().toPoint() - self._pan_start
            self._offset = self._pan_offset_start + delta
            self.update()
        else:
            split_x = int(self.width() * self._split_pos)
            if abs(event.position().x() - split_x) < 8:
                self.setCursor(QCursor(Qt.CursorShape.SplitHCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def mouseReleaseEvent(self, event):
        self._dragging_split = False
        self._pan_start = None
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        new_zoom = max(0.1, min(20.0, self._zoom * factor))

        # Bildpunkt unter dem Mauszeiger vor und nach Zoom identisch halten
        mx = event.position().x()
        my = event.position().y()
        # Bildkoordinate unter Maus (unabhaengig vom Zoom)
        img_x = (mx - self._offset.x()) / self._zoom
        img_y = (my - self._offset.y()) / self._zoom
        # Neuen Offset berechnen, sodass derselbe Bildpunkt unter der Maus bleibt
        self._zoom = new_zoom
        self._offset = QPoint(
            int(mx - img_x * self._zoom),
            int(my - img_y * self._zoom),
        )
        self.update()

    # ──────────────────────────────────────────────
    # Hilfsmethoden
    # ──────────────────────────────────────────────

    def _to_pixmap(self, arr: np.ndarray) -> QPixmap:
        h, w, ch = arr.shape
        bytes_per_line = ch * w
        qimg = QImage(arr.tobytes(), w, h, bytes_per_line,
                      QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg)

    def _fit_to_canvas(self):
        if self._px_original is None:
            self._zoom = 1.0
            self._offset = QPoint(0, 0)
            return
        img_w = self._px_original.width()
        img_h = self._px_original.height()
        cw = self.width()
        ch = self.height()
        if img_w == 0 or img_h == 0 or cw == 0 or ch == 0:
            return
        self._zoom = min(cw / img_w, ch / img_h)
        self._offset = QPoint(
            int((cw - img_w * self._zoom) / 2),
            int((ch - img_h * self._zoom) / 2),
        )

    def _draw_placeholder(self):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1a1a2e"))
        painter.setPen(QColor("#555577"))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                         "Bild öffnen\n(Datei → Öffnen oder Drag & Drop)")
        painter.end()
