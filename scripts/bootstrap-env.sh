#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

random_hex() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$1"
  else
    python3 - <<PY
import secrets
print(secrets.token_hex($1))
PY
  fi
}

if [ ! -f "$ENV_FILE" ]; then
  umask 077
  cat > "$ENV_FILE" <<EOF
POSTGRES_PASSWORD=$(random_hex 24)
STORCLOUD_SETUP_TOKEN=$(random_hex 24)
STORCLOUD_SESSION_DAYS=30
STORCLOUD_ALLOW_REGISTRATION=true
STORCLOUD_COOKIE_SECURE=false
STORCLOUD_MAX_ROM_BYTES=2147483648
STORCLOUD_STREAMING_ENABLED=false
STORCLOUD_STREAMING_PROVIDER=sunshine
STORCLOUD_STREAMING_HOST=
STORCLOUD_STREAMING_GATEWAY_TEMPLATE=
EOF
  echo "[StorCloud] Created .env with database credentials and first-admin setup token."
else
  touch "$ENV_FILE"
  grep -q '^POSTGRES_PASSWORD=' "$ENV_FILE" || echo "POSTGRES_PASSWORD=$(random_hex 24)" >> "$ENV_FILE"
  grep -q '^STORCLOUD_SETUP_TOKEN=' "$ENV_FILE" || echo "STORCLOUD_SETUP_TOKEN=$(random_hex 24)" >> "$ENV_FILE"
  grep -q '^STORCLOUD_SESSION_DAYS=' "$ENV_FILE" || echo 'STORCLOUD_SESSION_DAYS=30' >> "$ENV_FILE"
  grep -q '^STORCLOUD_ALLOW_REGISTRATION=' "$ENV_FILE" || echo 'STORCLOUD_ALLOW_REGISTRATION=true' >> "$ENV_FILE"
  grep -q '^STORCLOUD_COOKIE_SECURE=' "$ENV_FILE" || echo 'STORCLOUD_COOKIE_SECURE=false' >> "$ENV_FILE"
  grep -q '^STORCLOUD_MAX_ROM_BYTES=' "$ENV_FILE" || echo 'STORCLOUD_MAX_ROM_BYTES=2147483648' >> "$ENV_FILE"
  grep -q '^STORCLOUD_STREAMING_ENABLED=' "$ENV_FILE" || echo 'STORCLOUD_STREAMING_ENABLED=false' >> "$ENV_FILE"
  grep -q '^STORCLOUD_STREAMING_PROVIDER=' "$ENV_FILE" || echo 'STORCLOUD_STREAMING_PROVIDER=sunshine' >> "$ENV_FILE"
  grep -q '^STORCLOUD_STREAMING_HOST=' "$ENV_FILE" || echo 'STORCLOUD_STREAMING_HOST=' >> "$ENV_FILE"
  grep -q '^STORCLOUD_STREAMING_GATEWAY_TEMPLATE=' "$ENV_FILE" || echo 'STORCLOUD_STREAMING_GATEWAY_TEMPLATE=' >> "$ENV_FILE"
fi

chmod 600 "$ENV_FILE" 2>/dev/null || true
mkdir -p "$ROOT_DIR/storage/saves" "$ROOT_DIR/storage/roms" "$ROOT_DIR/storage/media"
