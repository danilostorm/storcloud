#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/frontend/assets/mockups/atlas-crf60.b64"
OUT="$ROOT/frontend/assets/mockups/storcloud-plates.avif"
TMP="${OUT}.tmp"
EXPECTED_SHA="045422b485ec246d17b3c790d7e415c0dfbc5564dbb5d456071ef62f353d76b8"

if [ ! -s "$SRC" ]; then
  echo "[StorCloud] ERROR: pixel-plate source is missing: $SRC" >&2
  exit 1
fi

tr -d '\r\n\t ' < "$SRC" | base64 --decode > "$TMP"

actual_sha="$(sha256sum "$TMP" | awk '{print $1}')"
if [ "$actual_sha" != "$EXPECTED_SHA" ]; then
  echo "[StorCloud] ERROR: pixel atlas checksum mismatch." >&2
  echo "[StorCloud] expected: $EXPECTED_SHA" >&2
  echo "[StorCloud] actual:   $actual_sha" >&2
  rm -f "$TMP"
  exit 1
fi

python3 - "$TMP" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
data=p.read_bytes()
if len(data) != 96668:
    raise SystemExit(f"pixel atlas unexpected size: {len(data)} bytes")
if b"ftypavif" not in data[:64]:
    raise SystemExit("pixel atlas is not an AVIF file")
print(f"[StorCloud] Pixel atlas validated: {len(data)} bytes · 8 plates × 1672x941")
PY

mv -f "$TMP" "$OUT"
chmod 0644 "$OUT"
echo "[StorCloud] Pixel plates ready: $OUT"
