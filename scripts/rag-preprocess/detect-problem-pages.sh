#!/usr/bin/env bash
# Docling の JSON から、本文が落ちている / 崩れている疑いのあるページを挙げる。
#
# usage:
#     scripts/rag-preprocess/detect-problem-pages.sh <docling.json>
#
# 全ページを 1 行ずつ TSV で stdout に出す。problem 列が空でないページが問題ページ。
#     page           ページ番号（1 始まり）
#     chars          ページの文字数（空白を除く）
#     pic_chars_pct  そのうち図の中にある文字の割合。図の中の文字は Markdown に出ない
#     latin_pct      図の外の文字のうち英字の割合。OCR が化けると英字の羅列になる
#     problem        few_chars / text_in_picture / latin（カンマ区切り）
#
# 問題ページだけ欲しいときは: ... | awk -F'\t' 'NR > 1 && $5 != ""'
set -euo pipefail

MIN_CHARS=100
MAX_PIC_CHARS_PCT=5
MAX_LATIN_PCT=10

usage() { sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; }

[[ $# -eq 1 ]] || { usage >&2; exit 2; }
INPUT="$1"
command -v jq >/dev/null 2>&1 || { echo "jq not found" >&2; exit 1; }
[[ -f "$INPUT" ]] || { echo "JSON not found: $INPUT" >&2; exit 1; }

printf 'page\tchars\tpic_chars_pct\tlatin_pct\tproblem\n'
jq -r \
    --argjson min_chars "$MIN_CHARS" \
    --argjson max_pic "$MAX_PIC_CHARS_PCT" \
    --argjson max_latin "$MAX_LATIN_PCT" '
    def pct($a; $b): if $b > 0 then ($a * 100 / $b | floor) else 0 end;

    [ .texts[] | {
        page: .prov[0].page_no,
        in_picture: (.parent."$ref" | startswith("#/pictures")),
        chars: (.text | gsub("\\s"; "") | length),
        latin: (.text | [scan("[A-Za-z]")] | length)
    } ] as $texts
    | (.pages | keys | map(tonumber) | sort)[] as $page
    | [ $texts[] | select(.page == $page) ] as $t
    | ([ $t[].chars ] | add // 0) as $chars
    | pct([ $t[] | select(.in_picture) | .chars ] | add // 0; $chars) as $pic_pct
    | pct([ $t[] | select(.in_picture | not) | .latin ] | add // 0;
          [ $t[] | select(.in_picture | not) | .chars ] | add // 0) as $latin_pct
    | [ (if $chars < $min_chars then "few_chars" else empty end),
        (if $pic_pct >= $max_pic then "text_in_picture" else empty end),
        (if $latin_pct >= $max_latin then "latin" else empty end) ] as $problem
    | [ $page, $chars, $pic_pct, $latin_pct, ($problem | join(",")) ]
    | @tsv
' "$INPUT"
