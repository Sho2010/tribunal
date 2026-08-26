#!/usr/bin/env bash
# games/ の bytes を R2 と同期する（rclone のラッパー）。
#
# usage:
#     R2_REMOTE=r2 R2_BUCKET=tribunal scripts/r2.sh <command> [game_id] [-- rclone options]
#
# commands:
#     diff [game_id]    ローカルと R2 の差分を一覧する（転送しない）
#     ls   [game_id]    R2 側の object を一覧する
#     push [game_id]    ローカル → R2 へ転送する。R2 側の余りは消さない
#     sync [game_id]    ローカル → R2 へ転送し、R2 側の余りを削除する
#                       既定は dry-run。実際に消すには --force を付ける
#
# game_id を省略すると games/ 全体が対象。
# rclone の remote は `rclone config` で作る（credential は ~/.config/rclone/rclone.conf）。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FILTER="$REPO_ROOT/scripts/r2-filter.txt"

usage() { sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; }

if ! command -v rclone >/dev/null 2>&1; then
    cat >&2 <<'EOS'
rclone が見つかりません。

    sudo -v ; curl https://rclone.org/install.sh | sudo bash

インストール後、R2 の remote を作ります（S3 互換 / provider は Cloudflare）:

    rclone config

Cloudflare dashboard の R2 → Manage API tokens で Access Key ID / Secret を発行し、
endpoint は https://<account_id>.r2.cloudflarestorage.com を指定します。
EOS
    exit 1
fi

: "${R2_REMOTE:?R2_REMOTE が未設定です（rclone listremotes で確認できる remote 名）}"
: "${R2_BUCKET:?R2_BUCKET が未設定です（R2 の bucket 名）}"

COMMAND="${1:-}"
[[ -n "$COMMAND" ]] || { usage >&2; exit 2; }
shift

FORCE=0
GAME_ID=""
EXTRA=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE=1 ;;
        --) shift; EXTRA+=("$@"); break ;;
        -*) EXTRA+=("$1") ;;
        *)
            [[ -z "$GAME_ID" ]] || { echo "game_id は 1 つだけ指定してください: $1" >&2; exit 2; }
            GAME_ID="$1"
            ;;
    esac
    shift
done

# key は games/ を含める。ローカルのツリーと R2 の姿を一致させる
if [[ -n "$GAME_ID" ]]; then
    LOCAL="$REPO_ROOT/games/$GAME_ID"
    REMOTE="$R2_REMOTE:$R2_BUCKET/games/$GAME_ID"
    [[ -d "$LOCAL" ]] || { echo "games/$GAME_ID がありません" >&2; exit 1; }
else
    LOCAL="$REPO_ROOT/games"
    REMOTE="$R2_REMOTE:$R2_BUCKET/games"
fi

# ETag は multipart upload で MD5 にならないので checksum 比較に頼らない
COMMON=(--filter-from "$FILTER" --size-only)

echo "==> $COMMAND  $LOCAL  <->  $REMOTE"

case "$COMMAND" in
    diff)
        # --combined の記号: = 一致 / + local のみ / - remote のみ / * 差異
        rclone check "$LOCAL" "$REMOTE" --combined - "${COMMON[@]}" "${EXTRA[@]}"
        ;;
    ls)
        rclone lsl "$REMOTE" "${EXTRA[@]}"
        ;;
    push)
        rclone copy "$LOCAL" "$REMOTE" --progress "${COMMON[@]}" "${EXTRA[@]}"
        ;;
    sync)
        if [[ "$FORCE" -eq 1 ]]; then
            echo "!!! R2 側の余分な object を削除します"
            rclone sync "$LOCAL" "$REMOTE" --progress "${COMMON[@]}" "${EXTRA[@]}"
        else
            echo "(dry-run。実際に適用するには --force)"
            rclone sync "$LOCAL" "$REMOTE" --dry-run "${COMMON[@]}" "${EXTRA[@]}"
        fi
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
