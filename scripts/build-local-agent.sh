#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[StorCloud][Agent] Building local agent..."
cargo build --release --manifest-path "$ROOT_DIR/local-agent/Cargo.toml"

echo "[StorCloud][Agent] Build complete."
if [ -f "$ROOT_DIR/local-agent/target/release/storcloud-local-agent" ]; then
  ls -lh "$ROOT_DIR/local-agent/target/release/storcloud-local-agent"
elif [ -f "$ROOT_DIR/local-agent/target/release/storcloud-local-agent.exe" ]; then
  ls -lh "$ROOT_DIR/local-agent/target/release/storcloud-local-agent.exe"
fi
