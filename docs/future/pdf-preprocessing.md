# PDF 前処理と Vision

現在は生 PDF をそのまま Vector Store に載せ、parsing / chunking / embedding は OpenAI に任せている。
eval で実際の失敗パターンを観測してから改善する方針（決定 0010）。**以下はすべて未実装。**

## page-aware Markdown

PDF を page 番号を保った Markdown へ正規化する案。
検索の粒度と context の粒度は別物なので、chunk を細かくしつつ前後の page を context として渡せる形にしたい。

## Vision（ingest 時）

rulebook には図が多く、テキスト抽出だけでは落ちる情報がある。
PDF → page image → Vision → 構造化 Markdown という経路。

## Vision fallback（retrieval 時）

ingest 時の前処理とは別に、検索後の再確認経路。

```text
Vector Search → page 7 hit → R2 から該当ページ画像を取得 → Vision で再確認
```

そのため page 番号は可能な限り保持する。
