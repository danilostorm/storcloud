#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${1:-$ROOT_DIR/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR" storage/saves storage/roms

DB_OUT="$BACKUP_DIR/storcloud-db-$STAMP.sql.gz"
STORAGE_OUT="$BACKUP_DIR/storcloud-storage-$STAMP.tar.gz"
CHECKSUM_OUT="$BACKUP_DIR/storcloud-$STAMP.sha256"

echo "[StorCloud] Backing up PostgreSQL..."
docker compose exec -T db pg_dump -U storcloud -d storcloud | gzip -9 > "$DB_OUT"

echo "[StorCloud] Backing up cloud saves and private ROM library..."
tar -czf "$STORAGE_OUT" -C storage saves roms

sha256sum "$DB_OUT" "$STORAGE_OUT" > "$CHECKSUM_OUT"

echo "[StorCloud] Backup complete:"
ls -lh "$DB_OUT" "$STORAGE_OUT" "$CHECKSUM_OUT"
