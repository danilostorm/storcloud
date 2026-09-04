#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[StorCloud] Pulling latest code..."
git pull --ff-only

echo "[StorCloud] Reconstructing approved pixel-perfect visual plates..."
bash scripts/build-pixel-plates.sh

echo "[StorCloud] Preparing persistent environment..."
bash scripts/bootstrap-env.sh

echo "[StorCloud] Cleaning legacy separate retro engines..."
bash scripts/cleanup-legacy-retro.sh

echo "[StorCloud] Preparing local browser games..."
bash scripts/bootstrap-games.sh

echo "[StorCloud] Unified Retro player + hybrid execution catalog enabled."

echo "[StorCloud] Building and starting services..."
docker compose up -d --build --remove-orphans

echo "[StorCloud] Waiting for API + database readiness..."
api_ready=0
for attempt in $(seq 1 45); do
  if curl -fsS --max-time 3 http://127.0.0.1:8000/healthz >/tmp/storcloud-health.json 2>/dev/null; then
    api_ready=1
    break
  fi
  sleep 1
done

if [ "$api_ready" -eq 1 ]; then
  echo "[StorCloud] API + database online."
  cat /tmp/storcloud-health.json || true
  echo
else
  echo "[StorCloud] ERROR: API did not become ready."
  docker compose logs --tail=80 api || true
  docker compose logs --tail=40 db || true
  rm -f /tmp/storcloud-health.json
  exit 1
fi
rm -f /tmp/storcloud-health.json

echo "[StorCloud] Reloading web gateway..."
docker compose restart web >/dev/null

web_ready=0
for attempt in $(seq 1 20); do
  if curl -fsS --max-time 3 http://127.0.0.1:8080/api/healthz >/tmp/storcloud-web-health.json 2>/dev/null; then
    web_ready=1
    break
  fi
  sleep 1
done

if [ "$web_ready" -eq 1 ]; then
  echo "[StorCloud] Web gateway -> API online."
  cat /tmp/storcloud-web-health.json || true
  echo
else
  echo "[StorCloud] ERROR: web gateway cannot reach API."
  docker compose logs --tail=80 web api || true
  rm -f /tmp/storcloud-web-health.json
  exit 1
fi
rm -f /tmp/storcloud-web-health.json

echo "[StorCloud] Checking hybrid catalog through web gateway..."
if curl -fsS --max-time 5 http://127.0.0.1:8080/api/catalog >/tmp/storcloud-catalog.json 2>/dev/null; then
  echo "[StorCloud] Hybrid catalog online through Nginx."
else
  echo "[StorCloud] ERROR: hybrid catalog unavailable through web gateway."
  docker compose logs --tail=80 web api || true
  rm -f /tmp/storcloud-catalog.json
  exit 1
fi
rm -f /tmp/storcloud-catalog.json

echo "[StorCloud] Services:"
docker compose ps

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
