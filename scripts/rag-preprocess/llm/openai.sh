#!/usr/bin/env bash
# OpenAI（Responses API）に指示・画像・本文を渡し、応答の本文を stdout に出す。
#
# usage:
#     OPENAI_API_KEY=... scripts/rag-preprocess/llm/openai.sh <instructions.md> <image.png|jpg> < user.txt
#
# env:
#     OPENAI_API_KEY           必須
#     TRIBUNAL_OPENAI_MODEL    既定は gpt-5
#
# 応答が最後まで生成されなかったときは非 0 で終わる。
set -euo pipefail

MODEL="${TRIBUNAL_OPENAI_MODEL:-gpt-5}"

usage() { sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; }

[[ $# -eq 2 ]] || { usage >&2; exit 2; }
INSTRUCTIONS="$1"
IMAGE="$2"

for cmd in curl jq base64; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "$cmd not found" >&2; exit 1; }
done
: "${OPENAI_API_KEY:?OPENAI_API_KEY is not set}"
[[ -f "$INSTRUCTIONS" ]] || { echo "instructions not found: $INSTRUCTIONS" >&2; exit 1; }
[[ -f "$IMAGE" ]] || { echo "image not found: $IMAGE" >&2; exit 1; }

case "$IMAGE" in
    *.png) MEDIA_TYPE=image/png ;;
    *.jpg | *.jpeg) MEDIA_TYPE=image/jpeg ;;
    *) echo "image must be .png or .jpg: $IMAGE" >&2; exit 2 ;;
esac

# PDF を input_file で渡すとページが低解像度の画像にされるので、画像を直接 detail: high で渡す
if ! RESPONSE="$(
    jq -n \
        --arg model "$MODEL" \
        --arg media_type "$MEDIA_TYPE" \
        --rawfile instructions "$INSTRUCTIONS" \
        --rawfile image <(base64 -w0 <"$IMAGE") \
        --rawfile text /dev/stdin \
        '{
            model: $model,
            instructions: $instructions,
            input: [{
                role: "user",
                content: [
                    {type: "input_image", detail: "high",
                     image_url: ("data:" + $media_type + ";base64," + $image)},
                    {type: "input_text", text: $text}
                ]
            }]
        }' |
        curl -sS --fail-with-body \
            --retry 5 \
            --max-time 600 \
            -H "Authorization: Bearer $OPENAI_API_KEY" \
            -H "Content-Type: application/json" \
            --data-binary @- \
            https://api.openai.com/v1/responses
)"; then
    echo "OpenAI API request failed" >&2
    jq -r '.error.message? // empty' <<<"$RESPONSE" >&2 2>/dev/null || true
    exit 1
fi

jq -r '"    \(.model) in: \(.usage.input_tokens) / out: \(.usage.output_tokens) tokens"' <<<"$RESPONSE" >&2

STATUS="$(jq -r '.status' <<<"$RESPONSE")"
if [[ "$STATUS" != "completed" ]]; then
    echo "response not completed: status=$STATUS $(jq -c '.incomplete_details // empty' <<<"$RESPONSE")" >&2
    exit 1
fi

jq -j '[.output[] | select(.type == "message") | .content[]
        | select(.type == "output_text") | .text] | join("")' <<<"$RESPONSE"
