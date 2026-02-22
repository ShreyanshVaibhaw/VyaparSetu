#!/usr/bin/env bash
set -euo pipefail

APP_NAME="vyaparsetu"
PYTHON_BIN="${PYTHON_BIN:-python}"

echo "[${APP_NAME}] Starting local setup..."

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "[${APP_NAME}] Python executable '${PYTHON_BIN}' not found."
  exit 1
fi

if [ ! -d .venv ]; then
  echo "[${APP_NAME}] Creating virtual environment..."
  "${PYTHON_BIN}" -m venv .venv
fi

echo "[${APP_NAME}] Activating virtual environment..."
source .venv/bin/activate

echo "[${APP_NAME}] Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "[${APP_NAME}] Generating synthetic data..."
python scripts/generate_synthetic_data.py

echo "[${APP_NAME}] Seeding database (PostgreSQL if available, SQLite fallback otherwise)..."
python scripts/seed_database.py

echo "[${APP_NAME}] Launching Streamlit on http://localhost:8501"
exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0
