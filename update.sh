#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[StorCloud] Pulling latest code..."
git pull --ff-only

echo "[StorCloud] Preparing local browser games..."
bash scripts/bootstrap-games.sh

echo "[StorCloud] Building and starting services..."
docker compose up -d --build --remove-orphans

echo "[StorCloud] Services:"
docker compose ps

echo "[StorCloud] Done. Web: :8080 | API: :8000 | Docs: :8000/docs"
