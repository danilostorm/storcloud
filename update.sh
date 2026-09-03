#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[StorCloud] Pulling latest code..."
git pull --ff-only

echo "[StorCloud] Preparing persistent environment..."
bash scripts/bootstrap-env.sh

echo "[StorCloud] Cleaning legacy separate retro engines..."
bash scripts/cleanup-legacy-retro.sh

echo "[StorCloud] Preparing local browser games..."
bash scripts/bootstrap-games.sh

echo "[StorCloud] Unified Retro player + hybrid execution catalog enabled."

echo "[StorCloud] Building and starting services..."
docker compose up -d --build --remove-orphans

echo "[StorCloud] Services:"
docker compose ps

echo "[StorCloud] Health check:"
if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
  echo "[StorCloud] API + database online."
else
  echo "[StorCloud] WARN: API health check not ready yet. Check: docker compose logs api db"
fi

if curl -fsS http://127.0.0.1:8000/catalog >/dev/null 2>&1; then
  echo "[StorCloud] Hybrid catalog online."
else
  echo "[StorCloud] WARN: hybrid catalog endpoint unavailable."
fi

echo "[StorCloud] Done."
echo "  Home:         :8080/"
echo "  Catalog:      :8080/catalog/"
echo "  Library:      :8080/library/"
echo "  Retro:        :8080/retro/"
echo "  PC Local:     :8080/pc/"
echo "  Achievements: :8080/achievements/"
echo "  Account:      :8080/account/"
echo "  Admin:        :8080/admin/"
echo "  Streaming:    :8080/stream/"
echo "  API docs:     :8000/docs"
