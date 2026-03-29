# ArchäoFalschfarben – Dokumentation

> **Falschfarbenanalyse für archäologische Bodenstrukturen**
> Erkennung von Bewuchsmerkmalen, Bodenverfärbungen und Mikrotopographie in Luftbildern und Drohnenaufnahmen.

---

## Inhaltsverzeichnis

1. [Schnellstart](#1-schnellstart)
2. [Systemvoraussetzungen](#2-systemvoraussetzungen)
3. [Installation](#3-installation)
4. [Bedienung der Oberfläche](#4-bedienung-der-oberfläche)
5. [Analysefunktionen im Detail](#5-analysefunktionen-im-detail)
6. [Preset-System](#6-preset-system)
7. [Export-Funktionen](#7-export-funktionen)
8. [Tipps für archäologische Bildanalyse](#8-tipps-für-archäologische-bildanalyse)
9. [Projektstruktur](#9-projektstruktur)
10. [Fehlerbehebung](#10-fehlerbehebung)

---

## 1. Schnellstart

### Windows (empfohlen)
```
start.bat
```
oder alternativ als PowerShell:
```powershell
.\start.ps1
```

Das Skript:
- Prüft ob Python 3.11+ vorhanden ist
- Erstellt automatisch eine virtuelle Umgebung (`venv/`)
- Installiert alle Abhängigkeiten (einmalig, ~150 MB)
- Startet die Anwendung

### Manuell
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python main.py
```

### Bild als Argument übergeben
```bash
python main.py C:\Pfad\zum\Bild.jpg
```

---

## 2. Systemvoraussetzungen

| Komponente | Minimum | Empfohlen |
|---|---|---|
| Betriebssystem | Windows 10 / macOS 12 / Linux | Windows 11 |
| Python | 3.11 | 3.12 |
| RAM | 4 GB | 8 GB+ |
| CPU | beliebig | Mehrkern (Threading) |
| Bildschirm | 1280×768 | 1920×1080+ |

---

## 3. Installation

### Abhängigkeiten (`requirements.txt`)

| Paket | Version | Zweck |
|---|---|---|
| `numpy` | ≥1.24 | Array-Mathematik, Kanaloperationen |
| `opencv-python` | ≥4.8 | Bildverarbeitung, Kantenfilter, CLAHE |
| `Pillow` | ≥10.0 | Bildladen (JPG/GIF/PNG/TIFF) |
| `scikit-image` | ≥0.21 | Erweiterte Bildanalyse-Algorithmen |
| `matplotlib` | ≥3.7 | PDF-Report mit Legende |
| `PyQt6` | ≥6.5 | Grafische Benutzeroberfläche |

---

## 4. Bedienung der Oberfläche

### Hauptfenster

```
┌──────────────────────────────────────────────────────────────┐
│  Toolbar: [📂 Öffnen] [💾 PNG] [📄 PDF-Report] [🔍 Zoom]   │
├────────────────────┬─────────────────────────────────────────┤
│                    │                                         │
│  STEUERUNGS-       │  BILDVORSCHAU                          │
│  PANEL             │                                         │
│  (scrollbar)       │  Links: Original  │  Rechts: Ergebnis  │
│                    │  ◄──── Split-Schieberegler ────►        │
│  • Colormap        │                                         │
│  • Kanal-Mapping   │                                         │
│  • Kontrast        │                                         │
│  • Kanten          │                                         │
│  • Spezialfilter   │                                         │
│                    │                                         │
├────────────────────┴─────────────────────────────────────────┤
│  Statusleiste: Dateiname, Bildgröße, Verarbeitungsstatus     │
└──────────────────────────────────────────────────────────────┘
```

### Bild öffnen
- **Menü** → Datei → Öffnen (Strg+O)
- **Toolbar** → 📂 Öffnen
- **Drag & Drop**: Bild direkt ins Fenster ziehen

Unterstützte Formate: `.jpg`, `.jpeg`, `.png`, `.gif`, `.tif`, `.tiff`

> Bei GIF-Dateien wird das erste Frame analysiert.

### Split-View
Der vertikale Schieberegler im Vorschau-Bereich teilt das Bild in Original (links) und Ergebnis (rechts). Per Klick+Ziehen verschiebbar.

### Navigation
| Aktion | Eingabe |
|---|---|
| Vergrößern/Verkleinern | Mausrad |
| Verschieben (Pan) | Linksklick + Ziehen |
| Zoom zurücksetzen | Strg+0 oder Toolbar |

---

## 5. Analysefunktionen im Detail

### 5.1 Falschfarben-Colormaps

| Name | Beschreibung | Ideal für |
|---|---|---|
| **Original** | Unverändertes Bild | Referenz |
| **Infrarot-Simulation** | R↔G-Tausch (CIR-ähnlich) | Bewuchsmerkmale, Vegetationsunterschiede |
| **Thermal-Jet** | Graustufen → Blau/Grün/Gelb/Rot | Allgemeine Strukturerkennung |
| **Thermal-Hot** | Graustufen → Schwarz/Rot/Gelb/Weiß | Kontrastreiche Anomalien |
| **Archäo-Profil** | Eigene Palette: Blau→Gelb→Rot | Optimiert für Bodenanalyse |
| **NDVI-Proxy** | `(R–G)/(R+G)` Vegetationsindex | Bewuchsdifferenzierung |
| **Graustufen-Spreizung** | Spreizter Grauwert | Subtile Helligkeitsunterschiede |
| **Falschfarbe-HSV** | Hue-Rotation im HSV-Raum | Farbcode-Variation |
| **Boden-Diff R–G** | Differenz Rot minus Grün | Rötliche Bodenverfärbungen |
| **Boden-Diff R–B** | Differenz Rot minus Blau | Tonige Bodenverfärbungen |

### 5.2 Kanal-Mapping

Jeder Ausgabekanal (R, G, B) kann frei einem Eingangskanal zugewiesen werden:
- Standard: R→R, G→G, B→B
- CIR: R→G, G→R, B→B
- Jede beliebige Kombination möglich

Zusätzlich kann jeder Kanal einzeln **invertiert** werden.

### 5.3 Kontrast & Aufbereitung

#### CLAHE
*Contrast Limited Adaptive Histogram Equalization*

- Verhindert Übersteuerung bei lokalen Kontrastverstärkungen
- **Clip-Limit**: 0.5 (sanft) bis 8.0 (stark) — Empfehlung: 2.0–4.0
- **Kachelgröße**: Größe der lokalen Bereiche (4px – 32px)

> CLAHE ist der **wichtigste** Vorverarbeitungsschritt bei Luftbildern mit ungleichmäßiger Belichtung.

#### Histogramm-Spreizung
- Streckt den Wertebereich eines Kanals zwischen Percentil-Grenzen
- Standard: 2%–98% (entfernt Ausreißer)
- Sinnvoll bei sehr flachen, wenig kontrastreichen Bodenbildern

#### Gamma-Korrektur
- **< 1.0**: Hellere Mitteltöne (gut für dunkle Schatten)
- **> 1.0**: Dunklere Mitteltöne (gut für überbelichtete Bilder)
- **= 1.0**: Keine Änderung

#### Entrauschung
- Reduziert Sensor-Rauschen vor der Analyse
- Stärke 3 (minimal) bis 15 (stark)
- Wird **vor** allen anderen Operationen angewendet

### 5.4 Kantendetektion

| Methode | Beschreibung | Anwendung |
|---|---|---|
| **Sobel** | Gradient-Magnitude | Grabenkanten, Mauerreste |
| **Scharr** | Verbesserter Sobel | Diagonale Strukturen |
| **Canny** | Zweistufige Detektion | Bewuchsmerkmale, empfohlen |
| **Laplacian** | 2. Ableitung | Gruben, Pfostenlöcher (rund) |
| **LoG** | Laplacian of Gaussian | Rauscharm, runde Strukturen |

**Kanten werden über das Falschfarbenbild gelegt** (orange-rote Linien).

> Die Canny-Schwellwerte (Low/High) bestimmen, welche Gradienten als Kanten erkannt werden. Bei Luftbildern Empfehlung: Low=30–60, High=100–180.

### 5.5 Archäo-Spezialfilter

#### Crop-Mark Enhancement
Optimiert für **Bewuchsmerkmale** auf sommerlichen Luftbildern.

- Analysiert den Grünkanal mit CLAHE
- Berechnet G–R-Differenz als Vegetation-Proxy
- Morphologischer Top-Hat-Filter hebt lineare Strukturen (Gräben) hervor

**Geeignet für:** Luftbilder bei Trockenheit, wenn sich eingetiefte Strukturen durch üppigeres Wachstum abzeichnen.

#### Soil-Mark Enhancement
Optimiert für **Bodenverfärbungen** nach Regen oder Pflügen.

- Konvertiert zu YCrCb-Farbraum
- CLAHE auf Farb-Kanälen Cr und Cb
- Berechnet Soil-Index: `Cr – Cb` (Rötlichkeit minus Bläulichkeit)

**Geeignet für:** Frisch gepflügte Felder, nasse Bodenoberflächen.

#### Schatten-Relief (Hillshade)
Simuliert **Schrägbeleuchtung** zur Mikrotopographie-Erkennung.

- Helligkeitswert dient als Pseudo-Höhenmodell
- Berechnet Hillshade nach Standard-Formel
- Beleuchtungswinkel: 315° (NW, Standard nach kartografischer Konvention)

**Geeignet für:** Luftbilder mit erkennbarer Mikrotopographie (Wälle, Gräben, Hügel).

---

## 6. Preset-System

Alle aktuellen Einstellungen können als benanntes Preset gespeichert und wiederverwendet werden.

**Speichern:** Menü → Presets → Aktuelles Preset speichern

**Laden:** Menü → Presets → Preset laden

Presets werden als JSON gespeichert in: `presets/profiles.json`

Beispiel-Preset manuell in `profiles.json` eintragen:
```json
{
  "Crop-Mark Standard": {
    "colormap": "Infrarot-Simulation",
    "clahe": true,
    "clahe_clip": 3.0,
    "clahe_tile": 8,
    "edges": true,
    "edge_method": "Canny",
    "edge_low": 30,
    "edge_high": 120,
    "special": "Keiner"
  }
}
```

---

## 7. Export-Funktionen

### PNG-Export
- Volle Auflösung (nicht nur Vorschau)
- Menü → Datei → Ergebnis speichern (PNG) oder Strg+S

### TIFF-Export
- Verlustfreies Format, ideal für GIS-Integration
- Menü → Datei → Ergebnis speichern (TIFF)

### PDF-Report
Erstellt einen zweiseitigen Analysebericht mit:
- Originalbild und Ergebnisbild nebeneinander
- Vollständige Parametertabelle aller verwendeten Einstellungen
- Zeitstempel

---

## 8. Tipps für archäologische Bildanalyse

### Allgemein
- Rohdaten (möglichst unkomprimiert) liefern bessere Ergebnisse als mehrfach komprimierte JPEGs
- Luftbilder am frühen Morgen oder späten Nachmittag haben günstigere Schrägbeleuchtung
- Bei Drohnenbildern: RAW → TIFF für beste Qualität

### Bewuchsmerkmale (Crop-Marks)
1. **Infrarot-Simulation** Colormap einschalten
2. CLAHE aktivieren (Clip 3.0, Kachel 8)
3. Additional: **Crop-Mark Enhancement** als Spezialfilter
4. Canny-Kantendetektion mit Low=30, High=100

### Bodenverfärbungen (Soil-Marks)
1. **Soil-Mark Enhancement** Spezialfilter
2. CLAHE + Histogramm-Spreizung kombinieren
3. **Boden-Diff R–G** oder **R–B** Colormap als Alternative

### Mikrotopographie
1. **Schatten-Relief** Spezialfilter bei Schrägbeleuchtungsfotos
2. Alternativ: **Thermal-Hot** + Sobel-Kanten
3. Gamma erhöhen (1.4–1.8) für dunkle Schattenbereiche

### GIS-Integration
- Export als TIFF
- Georeferenzierung in QGIS/ArcGIS mit bekannten Passpunkten
- Empfehlung: Vor Analyse Georeferenzierung durchführen

---

## 9. Projektstruktur

```
ArchäoFalschfarben/
│
├── main.py                    ← Einstiegspunkt
├── requirements.txt           ← Python-Abhängigkeiten
├── start.bat                  ← Windows Start-Skript (venv + install)
├── start.ps1                  ← PowerShell Start-Skript
│
├── core/
│   ├── __init__.py
│   ├── image_loader.py        ← Bildladen, Normalisierung
│   ├── colormap_engine.py     ← Alle Falschfarben-Algorithmen
│   ├── band_manipulator.py    ← Kanal-Remapping, Invertierung
│   ├── enhancement.py         ← CLAHE, Histogramm, Gamma, Denoise
│   ├── edge_detector.py       ← Sobel, Canny, Laplacian, LoG
│   ├── special_filters.py     ← Crop-Mark, Soil-Mark, Hillshade
│   └── exporter.py            ← PNG/TIFF Speichern, PDF-Report
│
├── gui/
│   ├── __init__.py
│   ├── main_window.py         ← Hauptfenster, Menü, Toolbar, Pipeline
│   ├── control_panel.py       ← Einstellungs-Sidebar
│   └── preview_canvas.py      ← Split-View, Zoom, Pan
│
└── presets/
    └── profiles.json          ← Gespeicherte Analyse-Profile
```

---

## 10. Fehlerbehebung

### `ModuleNotFoundError: No module named 'PyQt6'`
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### `error: Microsoft Visual C++ 14.0 is required` (Windows)
Installieren Sie die [Visual C++ Build Tools](https://visualstudio.microsoft.com/de/visual-cpp-build-tools/).

### Anwendung startet, aber Bild wird nicht angezeigt
- Prüfen Sie, ob das Format unterstützt wird (.jpg/.png/.gif/.tif)
- Bei GIF mit vielen Frames: nur Frame 0 wird geladen

### PDF-Export erzeugt leere Seiten
- Stellen Sie sicher, dass ein Ergebnis berechnet wurde (Einstellung ändern nach Bildladen)

### `cv2.error` bei Kantendetektion
- Low-Threshold muss kleiner als High-Threshold sein (Canny)
- Empfehlung: Low=50, High=150

### Träge Vorschau bei großen Bildern
- Vorschau verwendet automatisch auf max. 1200px skalierte Version
- Export verwendet immer die Vollauflösung
- Für sehr große Bilder (>50 MP) empfiehlt sich Vorskalierung

---

*ArchäoFalschfarben | Version 1.0.0 | Python · OpenCV · PyQt6*
