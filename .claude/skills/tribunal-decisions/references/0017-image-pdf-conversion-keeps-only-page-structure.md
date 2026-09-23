# ADR 0017: 画像 PDF の変換はページ構造だけを保証し、中間生成物を temp に閉じる

- Status: Accepted
- Date: 2026-09-23

## Context

OCR処理前の画像だけの PDF は、そのままVector Store に載せても本文を検索できない。
Markdown へ変換する経路が要る。Rule 資料（スキャンされた rulebook など）にも同じ経路を使う予定。

変換に LLM を使うので、同じ入力から同じ本文は出ない。冪等性を本文の一致で定義できない。

## Decision

### 保証するのは構造だけ

出力 Markdown で保証するのは、ページマーカー `<!-- source_pdf_page: N -->` が
1 から総ページ数まで欠番・重複なしで並ぶことと、判読不能箇所を `[判読不能]` で残すこと。
本文の一致は保証しない。

ページマーカーは、誤答を原ページへ辿るための唯一の手がかりとして残す。

### 途中の経路は固定しない

OCR / レイアウト解析を挟むか、ページ画像を LLM に直接渡すかは spec に書かない。
OCR と Docling はコストのために挟む前提だが、処理時間と品質の差は検証で確かめる。
経路を入れ替えても入出力が変わらないようにしておく。

### 中間生成物は repo 直下の `temp/` に閉じる

`games/<game_id>/{rule,strategy}/` の下には置かない。将来 `games/` を sync の対象にしたとき、
中間生成物が ingest 対象として拾われる事故が起きうる。
当面、人が管理するのは `raw/` の原本と、Vector Store に載せる最終 Markdown だけにする。

`temp/` は `.gitignore` で丸ごと落とす。OCR 結果も著作物の派生物で、push してはいけない。

### 処理来歴を残さない

使ったツール、prompt の版、model を出力にも manifest にも残さない。
来歴が効くのは「複数資料を別々の prompt で処理していて、古いものだけ作り直す」場面で、
資料が 1 冊のうちは全部作り直せば済む。誤答を辿るのに要るのはページマーカーだけ。

### 再処理の単位はページ

ページごとの変換結果（`pages/page-NNNN.md`）があればそのページは変換し直さない。
やり直すときはファイルを消す。LLM の課金を二重にしないための最小の仕組みで、
入力 hash や prompt 版によるキャッシュ判定は作らない。

### Vector Store への登録は手動、管理台帳を作らない

[0016](0016-automate-ingest-only-past-a-threshold.md) の通り、sync CLI を作るまでは手で載せる。
旧ファイル ID を記録する台帳も作らない（[0015](0015-use-vector-store-not-direct-file-input.md)）。

登録時に file attribute `game_id` だけは手で付ける。front matter に書いても OpenAI は
attribute として解釈しない。retriever は `game_id` で絞り込めるので、GameResolver が入って
絞り込みが効き始めると、attribute の無いファイルは検索から外れる。

## Consequences

- 変換 1 回ごとの品質は人が原ページと照合して確かめるしかない
- 経路の比較検証をしても spec を直さずに済む
- prompt を変えて作り直すときは、`pages/` を消して全ページ作り直す
- 資料が増えて選択的な作り直しが要るようになったら、来歴とキャッシュ判定を足す必要がある
- 手で attribute を付け忘れると、絞り込みが効き始めた時点でそのファイルが静かに検索から漏れる
