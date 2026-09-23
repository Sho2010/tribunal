#!/usr/bin/env bash
# 画像 PDF を OCRmyPDF にかけて searchable PDF を作る。
#
# usage:
#     scripts/rag-preprocess/run-ocr.sh <input.pdf> <output.pdf> [pages]
#
#     <input.pdf>   原本の画像 PDF。変更しない
#     <output.pdf>  searchable PDF の出力先（temp/ の下に置く）。全ページを含む
#     [pages]       OCR するページ。N または A-B（1 始まり）。省略すると全ページ
#
# OCR テキストは <output>.txt に書く（OCRmyPDF の sidecar。ページは \f で区切られる）。
# テキスト層を持つ PDF（フォントが埋め込まれている）は OCR せずに止まる。
# <output.pdf> が既にあれば何もしない。
set -euo pipefail

usage() { sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; }

[[ $# -eq 2 || $# -eq 3 ]] || { usage >&2; exit 2; }
INPUT="$1"
OUTPUT="$2"
PAGES="${3:-}"
SIDECAR="${OUTPUT%.pdf}.txt"

for cmd in ocrmypdf qpdf pdffonts; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "$cmd not found" >&2; exit 1; }
done
[[ -f "$INPUT" ]] || { echo "PDF not found: $INPUT" >&2; exit 1; }
[[ "$OUTPUT" == *.pdf ]] || { echo "output must end with .pdf: $OUTPUT" >&2; exit 2; }

if [[ -e "$OUTPUT" ]]; then
    echo "skip: $OUTPUT already exists" >&2
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
if [[ "$(pdffonts -f "$FIRST" -l "$LAST" "$INPUT" | tail -n +3)" ]]; then
    echo "text layer found in pages $PAGES; not an image PDF. stopping" >&2
    exit 1
fi

echo "==> OCR pages $PAGES of $TOTAL  $INPUT -> $OUTPUT" >&2

# --remove-background / --clean-final は図版や網掛けを書き換えるので使わない
# --deskew はページ画像を描き直すので、Docling がページ全面を 1 枚の図と判定し本文が落ちる
ocrmypdf \
    --pages "$PAGES" \
    -l jpn+eng \
    --tesseract-oem 1 \
    --tesseract-pagesegmode 3 \
    --rotate-pages \
    --oversample 300 \
    --output-type pdf \
    --optimize 0 \
    --sidecar "$SIDECAR" \
    "$INPUT" \
    "$OUTPUT"

echo "    ok: $OUTPUT, $SIDECAR" >&2
