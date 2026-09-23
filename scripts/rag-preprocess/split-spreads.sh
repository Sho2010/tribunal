#!/usr/bin/env bash
# 見開きの PDF を、各ページ左右 2 ページに分けた PDF にする。
#
# usage:
#     scripts/rag-preprocess/split-spreads.sh <input.pdf> <output.pdf>
#
#     <input.pdf>   見開きの画像 PDF。変更しない
#     <output.pdf>  分けた PDF の出力先（temp/ の下に置く）
#
# 元の 1 ページが左、右の順に 2 ページになる。全ページを分ける。
# 画像は描き直さず、ページの表示範囲だけを左右に切る。
# <output.pdf> が既にあれば何もしない。
set -euo pipefail

usage() { sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; }

[[ $# -eq 2 ]] || { usage >&2; exit 2; }
INPUT="$1"
OUTPUT="$2"

for cmd in mutool qpdf; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "$cmd not found" >&2; exit 1; }
done
[[ -f "$INPUT" ]] || { echo "PDF not found: $INPUT" >&2; exit 1; }

if [[ -e "$OUTPUT" ]]; then
    echo "skip: $OUTPUT already exists" >&2
    exit 0
fi

echo "==> split spreads  $INPUT -> $OUTPUT" >&2

mkdir -p "$(dirname "$OUTPUT")"
mutool poster \
    -x 2 \
    "$INPUT" \
    "$OUTPUT"

echo "    ok: $(qpdf --show-npages "$INPUT") -> $(qpdf --show-npages "$OUTPUT") pages" >&2
