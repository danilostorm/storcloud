#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PARTS="$ROOT/frontend/assets/mockups/.crf55"
OUT="$ROOT/frontend/assets/mockups/storcloud-plates.avif"
TMP="${OUT}.tmp"

shopt -s nullglob
parts=("$PARTS"/atlas.b64.*)
if [ "${#parts[@]}" -ne 6 ]; then
  echo "[StorCloud] ERROR: expected 6 pixel-plate chunks, found ${#parts[@]}" >&2
  exit 1
fi

: > "$TMP"
for part in "${parts[@]}"; do
  clean="${part}.clean.$$"
  sed 's#data:image/avif;base64,##g' "$part" | tr -d '\r\n\t ' > "$clean"
  if ! base64 --decode "$clean" >> "$TMP"; then
    rm -f "$clean" "$TMP"
    echo "[StorCloud] ERROR: invalid pixel-plate chunk: $(basename "$part")" >&2
    exit 1
  fi
  rm -f "$clean"
done

if [ ! -s "$TMP" ]; then
  echo "[StorCloud] ERROR: reconstructed pixel atlas is empty." >&2
  rm -f "$TMP"
  exit 1
fi

python3 - "$TMP" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
data=p.read_bytes()
if len(data) < 50000:
    raise SystemExit(f"pixel atlas unexpectedly small: {len(data)} bytes")
if b"ftypavif" not in data[:64]:
    raise SystemExit("pixel atlas is not an AVIF file")
print(f"[StorCloud] Pixel atlas validated: {len(data)} bytes")
PY

mv -f "$TMP" "$OUT"
chmod 0644 "$OUT"
echo "[StorCloud] Pixel plates ready: $OUT"
