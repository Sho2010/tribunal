#!/usr/bin/env python3
"""マーカー付きの Markdown の一部のページを、照合済みのページで差し替えて stdout に出す。"""

import argparse
import re
import sys
from pathlib import Path

MARKER = re.compile(r"<!-- source_pdf_page: ([1-9][0-9]*) -->")


def split_pages(path: Path) -> dict[int, str]:
    """base の Markdown をページ番号ごとの本文に分ける。"""
    pages: dict[int, list[str]] = {}
    current = 0
    for line in path.read_text().splitlines():
        m = MARKER.fullmatch(line)
        if m:
            n = int(m[1])
            if current == 0 and n != 1:
                sys.exit(f"first page is {n}, not 1, in {path}")
            if n != current + 1:
                sys.exit(f"page {n} follows page {current} in {path}")
            current = n
            pages[n] = []
        elif current == 0:
            if line:
                sys.exit(f"text before the first page marker in {path}")
        else:
            pages[current].append(line)
    if not pages:
        sys.exit(f"no page markers in {path}")
    return {n: "\n".join(lines) for n, lines in pages.items()}


def read_page(path: Path) -> tuple[int, str]:
    """1 ページ分の Markdown から、1 行目のマーカーのページ番号と本文を取る。"""
    first, _, body = path.read_text().partition("\n")
    m = MARKER.fullmatch(first)
    if not m:
        sys.exit(f"first line is not a page marker: {path}")
    return int(m[1]), body


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="マーカーが 1 から昇順に欠番・重複なく並ばないときは、何も出さずに止まる。",
    )
    parser.add_argument(
        "base", type=Path, help="全ページ分の Markdown（docling-markdown.sh の出力）"
    )
    parser.add_argument(
        "pages",
        type=Path,
        nargs="*",
        help="1 ページ分の Markdown（reconcile-page.sh の出力）。1 行目のマーカーでページを決める",
    )
    args = parser.parse_args()

    for path in [args.base, *args.pages]:
        if not path.is_file():
            sys.exit(f"file not found: {path}")

    base = split_pages(args.base)
    replaced: dict[int, Path] = {}
    for path in args.pages:
        n, body = read_page(path)
        if n in replaced:
            sys.exit(f"page {n} given twice: {path}")
        if n not in base:
            sys.exit(f"page {n} is not in the base Markdown: {path}")
        base[n] = body
        replaced[n] = path

    for n, path in sorted(replaced.items()):
        print(f"page {n}: {path}", file=sys.stderr)
    print(
        "\n\n".join(
            f"<!-- source_pdf_page: {n} -->\n{body}".rstrip("\n")
            for n, body in sorted(base.items())
        )
    )


if __name__ == "__main__":
    main()
