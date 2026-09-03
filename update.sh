#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[StorCloud] Pulling latest code..."
git pull --ff-only

echo "[StorCloud] Cleaning legacy separate retro engines..."
bash scripts/cleanup-legacy-retro.sh

echo "[StorCloud] Preparing local browser games..."
bash scripts/bootstrap-games.sh

echo "[StorCloud] Retro Library uses the unified Nostalgist/RetroArch WASM player."
echo "[StorCloud] Separate emulator pages are no longer built or served."

echo "[StorCloud] Building and starting services..."
docker compose up -d --build --remove-orphans

echo "[StorCloud] Services:"
docker compose ps

echo "[StorCloud] Done. Web: :8080 | Retro: :8080/retro/ | PC Local: :8080/pc/ | API: :8000 | Docs: :8000/docs"
