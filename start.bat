@echo off
echo Starte ArchaeoFalschfarben...
cd /d "%~dp0"

REM --- 1. venv erstellen falls nicht vorhanden ---
IF NOT EXIST "venv\Scripts\python.exe" (
    echo [INFO] Erstelle virtuelle Umgebung...
    py -3 -m venv venv
    IF NOT EXIST "venv\Scripts\python.exe" (
        echo [FEHLER] venv konnte nicht erstellt werden.
        echo Bitte Python 3.11+ installieren: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo [OK] Virtuelle Umgebung erstellt.
)

REM --- 2. Abhaengigkeiten installieren (einmalig, Marker-Datei als Flag) ---
IF NOT EXIST "venv\.deps_ok" (
    echo [INFO] Installiere Abhaengigkeiten...
    venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    venv\Scripts\python.exe -m pip install -r requirements.txt
    IF ERRORLEVEL 1 (
        echo [FEHLER] Installation fehlgeschlagen.
        pause
        exit /b 1
    )
    echo. > "venv\.deps_ok"
    echo [OK] Abhaengigkeiten installiert.
)

REM --- 3. Anwendung starten (wie debug_start.bat) ---
echo Python-Pfad: venv\Scripts\python.exe
echo Arbeitsverzeichnis: %CD%
echo.
venv\Scripts\python.exe main.py %*
echo.
echo Exit-Code: %ERRORLEVEL%
IF ERRORLEVEL 1 pause