#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/runtime"
VENDOR_DIR="$RUNTIME_DIR/vendor"
GAMES_DIR="$RUNTIME_DIR/games"
DOOM_VENDOR="$VENDOR_DIR/doom-wasm"
DOOM_OUT="$GAMES_DIR/doom-wasm"

mkdir -p "$VENDOR_DIR" "$GAMES_DIR"

install_doom() {
  if [ -f "$DOOM_OUT/index.html" ]; then
    echo "[StorCloud] Doom WASM already installed."
    return
  fi

  echo "[StorCloud] Installing first local WASM game: Doom/FreeDoom..."
  rm -rf "$DOOM_VENDOR" "$DOOM_OUT"
  git clone --depth 1 https://github.com/gabrielbotandev/doom-wasm.git "$DOOM_VENDOR"

  cd "$DOOM_VENDOR"
  npm install
  npm --workspace web run build -- --base=/games/doom-wasm/

  mkdir -p "$DOOM_OUT"
  cp -a web/dist/. "$DOOM_OUT/"

  cat > "$DOOM_OUT/storcloud.json" <<'EOF'
{
  "id": "doom-wasm",
  "name": "Doom / FreeDoom WASM",
  "runtime": "browser-wasm",
  "rendering": "client",
  "source": "gabrielbotandev/doom-wasm",
  "assets": "FreeDoom 0.13.0",
  "proprietary_game_data_included": false
}
EOF

  echo "[StorCloud] Doom WASM installed at /games/doom-wasm/."
}

install_doom
