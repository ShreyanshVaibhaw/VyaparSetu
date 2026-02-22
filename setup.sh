#!/usr/bin/env bash
set -euo pipefail

APP_NAME="vyaparsetu"
MODEL="${OLLAMA_MODEL:-llama3.1:8b}"

echo "[${APP_NAME}] Starting Docker setup..."

if ! command -v docker >/dev/null 2>&1; then
  echo "[${APP_NAME}] Docker is required but not found."
  exit 1
fi

if [ ! -f .env ]; then
  echo "[${APP_NAME}] Creating .env from .env.example"
  cp .env.example .env
fi

echo "[${APP_NAME}] Building and starting infrastructure services..."
docker compose up -d --build postgres qdrant redis ollama

echo "[${APP_NAME}] Waiting for service health checks..."
docker compose up -d --wait postgres qdrant redis ollama

echo "[${APP_NAME}] Pulling Ollama model: ${MODEL}"
docker compose exec -T ollama ollama pull "${MODEL}"

echo "[${APP_NAME}] Seeding database..."
docker compose run --rm vyaparsetu python scripts/seed_database.py

echo "[${APP_NAME}] Starting Streamlit app..."
docker compose up -d --wait vyaparsetu

echo "[${APP_NAME}] Setup complete."
echo "[${APP_NAME}] Open: http://localhost:8501"
