"""
main.py – Einstiegspunkt der ArchäoFalschfarben-Anwendung.
"""
import sys
import os

# Sicherstellen, dass das Projektverzeichnis im Python-Pfad ist
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow


def main():
    # High-DPI-Unterstützung (automatisch ab PyQt6)
    app = QApplication(sys.argv)
    app.setApplicationName("ArchäoFalschfarben")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ArchäoTools")

    window = MainWindow()
    window.show()

    # Wenn ein Bild als Kommandozeilenargument übergeben wurde
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        window._load_file(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
