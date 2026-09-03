#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${1:-$ROOT_DIR/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

DB_OUT="$BACKUP_DIR/storcloud-db-$STAMP.sql.gz"
SAVES_OUT="$BACKUP_DIR/storcloud-saves-$STAMP.tar.gz"

echo "[StorCloud] Backing up PostgreSQL..."
docker compose exec -T db pg_dump -U storcloud -d storcloud | gzip -9 > "$DB_OUT"

echo "[StorCloud] Backing up save-state files..."
if [ -d storage/saves ]; then
  tar -czf "$SAVES_OUT" -C storage saves
else
  mkdir -p storage/saves
  tar -czf "$SAVES_OUT" -C storage saves
fi

sha256sum "$DB_OUT" "$SAVES_OUT" > "$BACKUP_DIR/storcloud-$STAMP.sha256"

echo "[StorCloud] Backup complete:"
ls -lh "$DB_OUT" "$SAVES_OUT" "$BACKUP_DIR/storcloud-$STAMP.sha256"
