#!/usr/bin/env bash
# Docling の JSON を、ページごとにマーカーを付けた Markdown にする。
#
# usage:
#     scripts/rag-preprocess/docling-markdown.sh <docling.json>
#
# JSON にある全ページを、各ページの先頭に <!-- source_pdf_page: N --> を置いて stdout に出す。
# 本文のないページもマーカーは出す。
set -euo pipefail

usage() { sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; }

[[ $# -eq 1 ]] || { usage >&2; exit 2; }
INPUT="$1"
command -v docling >/dev/null 2>&1 || { echo "docling not found" >&2; exit 1; }
[[ -f "$INPUT" ]] || { echo "JSON not found: $INPUT" >&2; exit 1; }

# Docling の CLI はページ単位の Markdown を出せないので、docling と同じ環境の Python から API を呼ぶ
PYTHON="$(dirname "$(readlink -f "$(command -v docling)")")/python"
[[ -x "$PYTHON" ]] || { echo "python next to docling not found: $PYTHON" >&2; exit 1; }

"$PYTHON" "$(dirname "${BASH_SOURCE[0]}")/docling-markdown.py" "$INPUT"
