# Setup-Skript fuer ArchaeoFalschfarben
# Erstellt venv und installiert alle Abhaengigkeiten

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir  = Join-Path $ScriptDir "venv"

Write-Host ""
Write-Host " ============================================" -ForegroundColor Cyan
Write-Host "  ArchaeoFalschfarben - Setup / Start" -ForegroundColor Cyan
Write-Host " ============================================" -ForegroundColor Cyan
Write-Host ""

# Python pruefen
try {
    $pyVer = python --version 2>&1
    Write-Host "[OK] $pyVer gefunden." -ForegroundColor Green
} catch {
    Write-Host "[FEHLER] Python nicht gefunden. Bitte Python 3.11+ installieren." -ForegroundColor Red
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Enter druecken zum Beenden"
    exit 1
}

# venv erstellen falls nicht vorhanden
if (-not (Test-Path (Join-Path $VenvDir "Scripts\Activate.ps1"))) {
    Write-Host "[INFO] Erstelle virtuelle Umgebung..." -ForegroundColor Yellow
    python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FEHLER] venv-Erstellung fehlgeschlagen." -ForegroundColor Red
        Read-Host "Enter druecken zum Beenden"
        exit 1
    }
    Write-Host "[OK] Virtuelle Umgebung erstellt." -ForegroundColor Green
}

# venv aktivieren
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
& $ActivateScript

# PyQt6 als Installations-Indikator pruefen
$testPyQt = python -c "import PyQt6" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Installiere Abhaengigkeiten..." -ForegroundColor Yellow
    python -m pip install --upgrade pip --quiet
    python -m pip install -r (Join-Path $ScriptDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FEHLER] Installation fehlgeschlagen." -ForegroundColor Red
        Read-Host "Enter druecken zum Beenden"
        exit 1
    }
    Write-Host "[OK] Alle Abhaengigkeiten installiert." -ForegroundColor Green
} else {
    Write-Host "[OK] Abhaengigkeiten bereits vorhanden." -ForegroundColor Green
}

Write-Host ""
Write-Host "[START] Starte ArchaeoFalschfarben..." -ForegroundColor Cyan
Write-Host ""

Set-Location $ScriptDir
python main.py $args

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[FEHLER] Anwendung mit Fehlercode beendet." -ForegroundColor Red
    Read-Host "Enter druecken zum Beenden"
}
