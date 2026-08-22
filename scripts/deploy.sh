#!/usr/bin/env bash
# Sprite 上のコードを最新にして service を再起動する。
#
# usage:
#     scripts/deploy.sh [sprite_name]
set -euo pipefail

SPRITE="${1:-tribunal}"
SERVICE="tribunal"
APP_DIR="/home/sprite/tribunal"

sp() { sprite exec --sprite "$SPRITE" "$@"; }

echo "==> git pull"
sp --dir "$APP_DIR" -- git pull --ff-only

echo "==> uv sync"
sp --dir "$APP_DIR" -- /home/sprite/.local/bin/uv sync

echo "==> restart $SERVICE"
sp -- sprite-env services restart "$SERVICE"

echo "==> status"
sp -- sprite-env services list

echo "==> logs"
sp -- tail -n 20 "/.sprite/logs/services/$SERVICE.log"
