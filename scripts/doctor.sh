#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

fail=0
ok(){ printf '[OK] %s\n' "$1"; }
warn(){ printf '[WARN] %s\n' "$1"; fail=1; }

echo "StorCloud Doctor"
echo "================="

if docker info >/dev/null 2>&1; then ok "Docker daemon online"; else warn "Docker daemon unavailable"; fi

for service in db api web; do
  status="$(docker compose ps --status running --services 2>/dev/null | grep -x "$service" || true)"
  if [ "$status" = "$service" ]; then ok "service $service running"; else warn "service $service not running"; fi
done

if curl -fsS http://127.0.0.1:8000/healthz >/tmp/storcloud-health.json 2>/dev/null; then
  ok "API health endpoint reachable"
  cat /tmp/storcloud-health.json; echo
else
  warn "API health endpoint unavailable"
fi
rm -f /tmp/storcloud-health.json

if curl -fsS http://127.0.0.1:8080/api/healthz >/tmp/storcloud-web-health.json 2>/dev/null; then
  ok "web gateway -> API reachable"
else
  warn "web gateway -> API unavailable"
fi
rm -f /tmp/storcloud-web-health.json

if curl -fsS http://127.0.0.1:8000/catalog >/tmp/storcloud-catalog.json 2>/dev/null; then
  ok "hybrid catalog endpoint reachable"
  python3 - <<'PY' 2>/dev/null || true
import json
p='/tmp/storcloud-catalog.json'
d=json.load(open(p))
print(f"Catalog items: {d.get('count', 0)}")
PY
else
  warn "hybrid catalog endpoint unavailable"
fi
rm -f /tmp/storcloud-catalog.json

if curl -fsS http://127.0.0.1:8000/streaming/status >/tmp/storcloud-streaming.json 2>/dev/null; then
  ok "streaming fallback status endpoint reachable"
else
  warn "streaming fallback status endpoint unavailable"
fi
rm -f /tmp/storcloud-streaming.json

if docker compose exec -T db pg_isready -U storcloud -d storcloud >/dev/null 2>&1; then ok "PostgreSQL accepting connections"; else warn "PostgreSQL not ready"; fi

if [ -f .env ]; then ok ".env exists"; else warn ".env missing"; fi
if [ -f catalog/games.json ]; then ok "catalog/games.json exists"; else warn "catalog/games.json missing"; fi
if [ -d storage/saves ]; then ok "cloud save storage exists"; else warn "storage/saves missing"; fi
if [ -d storage/roms ]; then ok "private ROM library storage exists"; else warn "storage/roms missing"; fi
if [ -d storage/media ]; then ok "retro artwork cache exists"; else warn "storage/media missing"; fi
if [ -d runtime/games ]; then ok "browser game runtime exists"; else warn "runtime/games missing"; fi

legacy=0
for dir in runtime/retro runtime/vendor/mgba runtime/vendor/mGBA-wasm runtime/vendor/fbneo runtime/vendor/fbneo-wasm runtime/vendor/n64wasm runtime/vendor/N64Wasm runtime/vendor/snes9x runtime/vendor/blastem runtime/vendor/ppsspp; do
  [ -e "$dir" ] && { echo "[WARN] legacy payload remains: $dir"; legacy=1; }
done
[ "$legacy" -eq 0 ] && ok "no known legacy separate-emulator payloads"

echo
echo "Disk usage:"
du -sh runtime storage storage/saves storage/roms storage/media 2>/dev/null || true

echo
echo "Containers:"
docker compose ps 2>/dev/null || true

exit "$fail"
