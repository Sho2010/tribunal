#!/usr/bin/env bash

# usage:
#     scripts/create-game-dir.sh <game_id>
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $0 <game_id>" >&2
  exit 1
fi

GAME_ID="$1"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/games/$GAME_ID"

mkdir -p "$BASE_DIR/rule" "$BASE_DIR/strategy" "$BASE_DIR/raw"
