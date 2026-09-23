"""Docling の JSON を、ページごとにマーカーを付けた Markdown にして stdout に出す。"""

import sys

from docling_core.types.doc import DoclingDocument

doc = DoclingDocument.load_from_json(sys.argv[1])
for n in sorted(doc.pages):
    body = doc.export_to_markdown(page_no=n).strip()
    print(f"<!-- source_pdf_page: {n} -->")
    print()
    if body:
        print(body)
        print()
