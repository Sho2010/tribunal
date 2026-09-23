# ADR 0002: metadata を path から導出せず、宣言する

- Status: Accepted
- Date: 2026-08-19

## Context

当初は path 自体を metadata schema にする案だった
（`games/<game>/official/rulebook/ja/rulebook.pdf` から 4 項目を導出する）。

## Decision

path を metadata schema の代わりに使わない。機械が参照するのは `meta.yaml` の宣言と
Markdown の front matter だけで、path を parse して `content_type` や `authority` を決めない。

理由:

- path がそのまま schema になる。typo しても構造上は valid なので、誤った attribute で静かに ingest される
- 次元（edition, expansion など）を後から足すと、全 path を move して再 ingest になる
- player_count / 複数言語 / faq と errata の両方に当たる文書は階層に収まらない。
  結局 path 以外の機構が必要になり、機構が 2 つに増える
- path は event routing や prefix filter にも使うため、metadata 都合で自由に再構成できない

ただし **`game_id` prefix と `rule` / `strategy` / `raw` の 3 区分は path に置く。**
これは metadata の導出元ではなく、人がディレクトリを開いて整理するための locator。
粒度も読み手も違う（機械は `meta.yaml` の `content_type: rulebook | faq | errata` を見る）。

## Consequences

- 同じ `rule/` の下から粒度の違う `content_type` が出る。path を見て分類してはいけない
- metadata の次元を足しても、ファイルを move せずに済む
- `meta.yaml` を書かないと ingest 対象にならない。宣言を忘れると静かに漏れる
- path の 3 区分を増やしたくなっても、それは metadata の次元追加ではない。3 つで足りなくなってから考える
