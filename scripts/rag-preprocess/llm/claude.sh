#!/usr/bin/env bash
# Claude（Messages API）に指示・画像・本文を渡し、応答の本文を stdout に出す。
#
# usage:
#     ANTHROPIC_API_KEY=... scripts/rag-preprocess/llm/claude.sh <instructions.md> <image.png|jpg> < user.txt
#
# env:
#     ANTHROPIC_API_KEY        必須
#     TRIBUNAL_CLAUDE_MODEL    既定は claude-opus-5
#
# 応答が最後まで生成されなかった（上限到達 / 拒否）ときは非 0 で終わる。
set -euo pipefail

MODEL="${TRIBUNAL_CLAUDE_MODEL:-claude-opus-5}"

usage() { sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; }

[[ $# -eq 2 ]] || { usage >&2; exit 2; }
INSTRUCTIONS="$1"
IMAGE="$2"

for cmd in curl jq base64; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "$cmd not found" >&2; exit 1; }
done
: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY is not set}"
[[ -f "$INSTRUCTIONS" ]] || { echo "instructions not found: $INSTRUCTIONS" >&2; exit 1; }
[[ -f "$IMAGE" ]] || { echo "image not found: $IMAGE" >&2; exit 1; }

case "$IMAGE" in
    *.png) MEDIA_TYPE=image/png ;;
    *.jpg | *.jpeg) MEDIA_TYPE=image/jpeg ;;
    *) echo "image must be .png or .jpg: $IMAGE" >&2; exit 2 ;;
esac

# fallbacks: "default" は拒否されたときに API 側で別モデルに回す（beta ヘッダと対で指定する）
if ! RESPONSE="$(
    jq -n \
        --arg model "$MODEL" \
        --arg media_type "$MEDIA_TYPE" \
        --rawfile instructions "$INSTRUCTIONS" \
        --rawfile image <(base64 -w0 <"$IMAGE") \
        --rawfile text /dev/stdin \
        '{
            model: $model,
            max_tokens: 16000,
            fallbacks: "default",
            system: $instructions,
            messages: [{
                role: "user",
                content: [
                    {type: "image", source: {type: "base64", media_type: $media_type, data: $image}},
                    {type: "text", text: $text}
                ]
            }]
        }' |
        curl -sS --fail-with-body \
            --retry 5 \
            --max-time 600 \
            -H "x-api-key: $ANTHROPIC_API_KEY" \
            -H "anthropic-version: 2023-06-01" \
            -H "anthropic-beta: server-side-fallback-2026-07-01" \
            -H "Content-Type: application/json" \
            --data-binary @- \
            https://api.anthropic.com/v1/messages
)"; then
    echo "Claude API request failed" >&2
    jq -r '.error.message? // empty' <<<"$RESPONSE" >&2 2>/dev/null || true
    exit 1
fi

jq -r '"    \(.model) in: \(.usage.input_tokens) / out: \(.usage.output_tokens) tokens"' <<<"$RESPONSE" >&2

STOP_REASON="$(jq -r '.stop_reason' <<<"$RESPONSE")"
if [[ "$STOP_REASON" != "end_turn" ]]; then
    echo "response not completed: stop_reason=$STOP_REASON $(jq -c '.stop_details // empty' <<<"$RESPONSE")" >&2
    exit 1
fi

jq -j '[.content[] | select(.type == "text") | .text] | join("")' <<<"$RESPONSE"
