#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/runtime"
VENDOR_DIR="$RUNTIME_DIR/vendor"
RETRO_DIR="$RUNTIME_DIR/retro"

mkdir -p "$VENDOR_DIR" "$RETRO_DIR"

FAILED=()

build_contract_engine() {
  local id="$1"
  local repo="$2"
  local source_name="$3"
  local out="$RETRO_DIR/$id"
  local vendor="$VENDOR_DIR/$id"

  if [ -f "$out/index.html" ]; then
    echo "[StorCloud][Retro] $source_name already installed."
    return 0
  fi

  echo "[StorCloud][Retro] Installing $source_name..."
  rm -rf "$vendor" "$out"

  if ! git clone --depth 1 "$repo" "$vendor"; then
    echo "[StorCloud][Retro] WARN: clone failed for $source_name."
    return 1
  fi

  if ! (cd "$vendor" && make build); then
    echo "[StorCloud][Retro] WARN: build failed for $source_name."
    return 1
  fi

  if [ ! -f "$vendor/dist/index.html" ]; then
    echo "[StorCloud][Retro] WARN: $source_name build produced no dist/index.html."
    return 1
  fi

  mkdir -p "$out"
  cp -a "$vendor/dist/." "$out/"

  cat > "$out/storcloud.json" <<EOF
{
  "id": "$id",
  "runtime": "browser-wasm",
  "rendering": "client",
  "source": "$repo",
  "roms_included": false
}
EOF

  echo "[StorCloud][Retro] $source_name ready at /retro/engines/$id/."
}

install_n64() {
  local id="n64"
  local repo="https://github.com/nbarkhina/N64Wasm.git"
  local out="$RETRO_DIR/$id"
  local vendor="$VENDOR_DIR/n64wasm"

  if [ -f "$out/index.html" ]; then
    echo "[StorCloud][Retro] N64Wasm already installed."
    return 0
  fi

  echo "[StorCloud][Retro] Installing N64Wasm prebuilt browser distribution..."
  rm -rf "$vendor" "$out"

  if ! git clone --depth 1 --branch master "$repo" "$vendor"; then
    echo "[StorCloud][Retro] WARN: clone failed for N64Wasm."
    return 1
  fi

  if [ ! -f "$vendor/dist/index.html" ]; then
    echo "[StorCloud][Retro] WARN: N64Wasm dist/index.html not found."
    return 1
  fi

  mkdir -p "$out"
  cp -a "$vendor/dist/." "$out/"

  cat > "$out/storcloud.json" <<'EOF'
{
  "id": "n64",
  "runtime": "browser-wasm",
  "rendering": "client",
  "source": "https://github.com/nbarkhina/N64Wasm",
  "roms_included": false
}
EOF

  echo "[StorCloud][Retro] N64Wasm ready at /retro/engines/n64/."
}

run_engine() {
  local id="$1"
  shift
  if ! "$@"; then
    FAILED+=("$id")
  fi
}

run_engine "snes9x" build_contract_engine "snes9x" "https://github.com/wasm-gaming/snes9x-wasm.git" "SNES9x WASM"
run_engine "mgba" build_contract_engine "mgba" "https://github.com/wasm-gaming/mGBA-wasm.git" "mGBA WASM"
run_engine "blastem" build_contract_engine "blastem" "https://github.com/wasm-gaming/blastem-wasm.git" "BlastEm WASM"
run_engine "fbneo" build_contract_engine "fbneo" "https://github.com/wasm-gaming/fbneo-wasm.git" "FinalBurn Neo WASM"
run_engine "n64" install_n64

mkdir -p "$RETRO_DIR/ppsspp"
cat > "$RETRO_DIR/ppsspp/storcloud.json" <<'EOF'
{
  "id": "ppsspp",
  "runtime": "browser-wasm",
  "rendering": "client",
  "status": "experimental-runtime-pending",
  "contract_source": "https://github.com/wasm-gaming/ppsspp-wasm",
  "working_port_candidate": "https://github.com/root-hunter/ppsspp-wasm",
  "roms_included": false
}
EOF

if [ ${#FAILED[@]} -gt 0 ]; then
  echo "[StorCloud][Retro] Completed with warnings. Failed engines: ${FAILED[*]}"
else
  echo "[StorCloud][Retro] Core installation complete."
fi
