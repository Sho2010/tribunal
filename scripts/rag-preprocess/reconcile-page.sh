#!/usr/bin/env bash
# 1 ページ分の原ページ画像と候補テキスト（OCR / Docling）を LLM に照合させ、Markdown を書く。
#
# usage:
#     TRIBUNAL_LLM=claude|openai scripts/rag-preprocess/reconcile-page.sh \
#         <page.png> <ocr.txt> <docling.txt> <N> <output.md>
#
#     <page.png>     原本（OCR 前）のページ画像
#     <ocr.txt>      そのページの OCR テキスト
#     <docling.txt>  そのページの Docling のテキスト
#     <N>            原本 PDF 上のページ番号（1 始まり）
#     <output.md>    出力先（temp/ の下に置く）
#
# env:
#     TRIBUNAL_LLM   必須。claude または openai（llm/<名前>.sh を使う。API key などはそちらの usage）
#
# 入力の作り方（N=21 の例）:
#     pdftoppm -f 21 -l 21 -r 200 -png -singlefile raw.pdf temp/p21
#     pdftotext -f 21 -l 21 -layout searchable.pdf temp/p21.ocr.txt
#     jq -r '.texts[] | select(.prov[0].page_no == 21) | .text' docling.json >temp/p21.docling.txt
#
# 出力が次を満たすときだけ <output.md> を書き、満たさなければ何も書かず非 0 で終わる。
#     - 先頭行が <!-- source_pdf_page: N -->
#     - 全体がコードフェンスや JSON で包まれていない
# <output.md> が既にあれば何もしない。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT="$SCRIPT_DIR/prompts/reconcile.md"

usage() { sed -n '2,26p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; }

[[ $# -eq 5 ]] || { usage >&2; exit 2; }
IMAGE="$1"
OCR="$2"
DOCLING="$3"
PAGE_NO="$4"
OUTPUT="$5"

: "${TRIBUNAL_LLM:?TRIBUNAL_LLM is not set (claude or openai)}"
LLM="$SCRIPT_DIR/llm/$TRIBUNAL_LLM.sh"
[[ -x "$LLM" ]] || { echo "unknown TRIBUNAL_LLM: $TRIBUNAL_LLM" >&2; exit 2; }
[[ "$PAGE_NO" =~ ^[1-9][0-9]*$ ]] || { echo "N must be a positive integer: $PAGE_NO" >&2; exit 2; }
for f in "$IMAGE" "$OCR" "$DOCLING"; do
    [[ -f "$f" ]] || { echo "not found: $f" >&2; exit 1; }
done

if [[ -e "$OUTPUT" ]]; then
    echo "skip: $OUTPUT already exists" >&2
    exit 0
fi

MARKER="<!-- source_pdf_page: $PAGE_NO -->"

echo "==> reconcile page $PAGE_NO with $TRIBUNAL_LLM -> $OUTPUT" >&2
SECONDS=0

RESULT="$(
    {
        echo "この画像は原本の $PAGE_NO ページ目です。1 行目は $MARKER としてください。"
        echo
        echo "## OCR 候補"
        echo
        cat "$OCR"
        echo
        echo "## Docling 候補"
        echo
        cat "$DOCLING"
    } | "$LLM" "$PROMPT" "$IMAGE"
)"

echo "    response received (${SECONDS}s). validating..." >&2

fail() { echo "validation failed: page $PAGE_NO: $1" >&2; exit 1; }

[[ "$(head -n 1 <<<"$RESULT")" == "$MARKER" ]] || fail "first line is not $MARKER"

BODY="$(tail -n +2 <<<"$RESULT")"
FIRST="$(grep -m 1 -v '^[[:space:]]*$' <<<"$BODY" || true)"
LAST="$(grep -v '^[[:space:]]*$' <<<"$BODY" | tail -n 1 || true)"
if [[ "$FIRST" =~ ^[[:space:]]*(\`\`\`|~~~) && "$LAST" =~ ^[[:space:]]*(\`\`\`|~~~)[[:space:]]*$ ]]; then
    fail "body is wrapped in a code fence"
fi
# 本文が "[判読不能]" で始まることもあるので、先頭文字ではなく JSON として読めるかで判定する
if jq -e 'type == "object" or type == "array"' <<<"$BODY" >/dev/null 2>&1; then
    fail "body is JSON"
fi

printf '%s\n' "$RESULT" >"$OUTPUT"
echo "    ok: $OUTPUT" >&2
