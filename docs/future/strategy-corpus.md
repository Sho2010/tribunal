# Strategy corpus

Strategy 回答の資料をどう集め、どう持つか。**未実装。**
Strategy Store 自体は動くが（`TRIBUNAL_STRATEGY_VECTOR_STORE_ID` があれば有効）、資料がまだ無い。

## document の形式

1 document = 1 Markdown + YAML front matter。
Markdown は file 内に metadata を持てるので、front matter が唯一の置き場所になる（決定 0003）。
crawler が生成するファイルも必ず front matter を持つ。

## crawler

候補となる情報源: BGG / Reddit / wiki / ブログ / 自分のプレイ記録。

無差別に crawl せず、authority（community / personal）を明示して取り込む。
Rule 回答の根拠には使わない（決定 0004）。

正規化して Markdown + front matter にする。`raw/` に生データを残し、前処理をやり直せるようにする。

## ゲーム別の想定

**Dominion** — Supply からの engine / synergy 提案。
評価軸: trash / draw / actions / payload / gains / buys / attacks / defense / terminal collision / synergy。

**Agricola** — 職業カード・小進歩の評価、ドラフト pick。
統計や構造化データが要るかもしれない。

## fine-tuning

知識を入れるために fine-tuning しない。知識は RAG、fine-tuning は推論スタイルの調整に限る。
最後の選択肢として扱う。
