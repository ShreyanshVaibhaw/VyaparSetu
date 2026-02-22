Param(
    [string]$PythonBin = "python"
)

$ErrorActionPreference = "Stop"
$AppName = "vyaparsetu"

Write-Host "[$AppName] Starting local setup (Windows PowerShell)..."

if (-not (Get-Command $PythonBin -ErrorAction SilentlyContinue)) {
    throw "[$AppName] Python executable '$PythonBin' not found in PATH."
}

if (-not (Test-Path ".venv")) {
    Write-Host "[$AppName] Creating virtual environment..."
    & $PythonBin -m venv .venv
}

$VenvPython = Join-Path ".venv" "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "[$AppName] Virtual environment Python not found at '$VenvPython'."
}

Write-Host "[$AppName] Installing dependencies..."
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

Write-Host "[$AppName] Generating synthetic data..."
& $VenvPython scripts/generate_synthetic_data.py

Write-Host "[$AppName] Seeding database (PostgreSQL if available, SQLite fallback otherwise)..."
& $VenvPython scripts/seed_database.py

Write-Host "[$AppName] Launching Streamlit at http://localhost:8501"
& (Join-Path ".venv" "Scripts\streamlit.exe") run app.py --server.port=8501 --server.address=0.0.0.0

