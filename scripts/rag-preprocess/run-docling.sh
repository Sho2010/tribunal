#!/usr/bin/env bash
# searchable PDF を Docling にかけて Markdown と JSON を作る。
#
# usage:
#     scripts/rag-preprocess/run-docling.sh <input.pdf> <output_dir> [pages]
#
#     <input.pdf>   テキスト層を持つ PDF（run-ocr.sh の出力）。変更しない
#     <output_dir>  出力先（temp/ の下に置く）。無ければ作る
#     [pages]       変換するページ。N または A-B（1 始まり）。省略すると全ページ
#
# <output_dir>/<input の名前>.md と .json を書く。JSON のページ番号は原本と同じ 1 始まり。
# テキスト層の無い PDF は止まる（OCR はしない）。
# <output_dir>/<input の名前>.md が既にあれば何もしない。
set -euo pipefail

usage() { sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; }

[[ $# -eq 2 || $# -eq 3 ]] || { usage >&2; exit 2; }
INPUT="$1"
OUTPUT_DIR="$2"
PAGES="${3:-}"
NAME="$(basename "$INPUT" .pdf)"

for cmd in docling qpdf pdffonts; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "$cmd not found" >&2; exit 1; }
done
[[ -f "$INPUT" ]] || { echo "PDF not found: $INPUT" >&2; exit 1; }

if [[ -e "$OUTPUT_DIR/$NAME.md" ]]; then
    echo "skip: $OUTPUT_DIR/$NAME.md already exists" >&2
    exit 0
fi

TOTAL="$(qpdf --show-npages "$INPUT")"
if [[ -z "$PAGES" ]]; then
    PAGES="1-$TOTAL"
fi
if [[ ! "$PAGES" =~ ^([1-9][0-9]*)(-([1-9][0-9]*))?$ ]]; then
    echo "pages must be N or A-B: $PAGES" >&2
    exit 2
fi
FIRST="${BASH_REMATCH[1]}"
LAST="${BASH_REMATCH[3]:-$FIRST}"
if (( FIRST > LAST || LAST > TOTAL )); then
    echo "pages out of range: $PAGES (total $TOTAL)" >&2
    exit 2
fi

# pdffonts は 2 行のヘッダの後にフォントを 1 行ずつ出す
if [[ -z "$(pdffonts -f "$FIRST" -l "$LAST" "$INPUT" | tail -n +3)" ]]; then
    echo "no text layer in pages $PAGES; run run-ocr.sh first" >&2
    exit 1
fi

echo "==> Docling pages $PAGES of $TOTAL  $INPUT -> $OUTPUT_DIR/$NAME.{md,json}" >&2

mkdir -p "$OUTPUT_DIR"
docling convert "$INPUT" \
    --from pdf \
    --to md \
    --to json \
    --pipeline standard \
    --no-ocr \
    --tables \
    --table-mode accurate \
    --image-export-mode placeholder \
    --page-range "$FIRST-$LAST" \
    --output "$OUTPUT_DIR"

echo "    ok: $OUTPUT_DIR/$NAME.md, $OUTPUT_DIR/$NAME.json" >&2
