#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/runtime"
RETRO_DIR="$RUNTIME_DIR/retro"
VENDOR_DIR="$RUNTIME_DIR/vendor"

LEGACY_IDS=(snes9x mgba blastem fbneo n64 ppsspp n64wasm)

echo "[StorCloud][Cleanup] Removing legacy separate retro engine artifacts..."

for id in "${LEGACY_IDS[@]}"; do
  if [ -e "$RETRO_DIR/$id" ]; then
    echo "[StorCloud][Cleanup] Removing runtime/retro/$id"
    rm -rf "$RETRO_DIR/$id"
  fi
  if [ -e "$VENDOR_DIR/$id" ]; then
    echo "[StorCloud][Cleanup] Removing runtime/vendor/$id"
    rm -rf "$VENDOR_DIR/$id"
  fi
done

# Old clone names used by previous bootstrap revisions.
for old in "$VENDOR_DIR/N64Wasm" "$VENDOR_DIR/n64-wasm" "$VENDOR_DIR/mGBA-wasm" "$VENDOR_DIR/snes9x-wasm" "$VENDOR_DIR/blastem-wasm" "$VENDOR_DIR/fbneo-wasm" "$VENDOR_DIR/ppsspp-wasm"; do
  if [ -e "$old" ]; then
    echo "[StorCloud][Cleanup] Removing $(basename "$old")"
    rm -rf "$old"
  fi
done

# Remove empty legacy retro directory. The unified player lives in frontend/retro.
if [ -d "$RETRO_DIR" ] && [ -z "$(find "$RETRO_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
  rmdir "$RETRO_DIR" || true
fi

# Preserve runtime/games (Doom/WASM packages) and any unrelated vendor data.
echo "[StorCloud][Cleanup] Legacy retro cleanup complete."
if [ -d "$RUNTIME_DIR" ]; then
  du -sh "$RUNTIME_DIR" 2>/dev/null | sed 's/^/[StorCloud][Cleanup] Runtime usage: /'
fi
