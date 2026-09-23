# ADR 0005: ingest を reconcile にし、event driven ingest を見送る

- Status: Accepted
- Date: 2026-08-19

## Context

当初は R2 の object create/delete を trigger に、Cloudflare Queue 経由で自動 ingest する構成を検討した。
Queue を挟む理由は OpenAI API の一時障害 / rate limit / retry / DLQ / 疎結合化だった。

しかし [0001](0001-r2-as-source-of-truth.md) で catalog を git に置いたため、
catalog の変更は R2 の event では検知できない。

## Decision

ingest は **desired と actual の diff を取って適用する reconcile** を主経路にする。

```text
catalog (desired) + R2 (bytes) → diff & apply → Vector Store (actual)
```

- desired にあって actual に無い → upload + attach + attributes 設定
- actual にあって desired に無い → detach / delete
- 両方にあるが R2 の ETag が変わっている → 再 upload
- orphan な OpenAI File → delete

diff を取って適用するだけなので **冪等**。何度実行しても安全で、実行漏れ・重複・順序に依存しない。

event driven ingest は v1 では作らない。catalog が git 上にある構成では、この経路が担当できるのは
「R2 へ直接ファイルを置いた場合の自動取り込み」だけになり、人の手間は reconcile とほぼ変わらない。

## Consequences

- ingest の実行タイミングを人（または CI）が決める。自動では走らない
- 冪等なので、失敗しても同じコマンドを再実行すればよい
- R2 へのドラッグ&ドロップ運用が不便になった段階で event 経路を足せる。
  reconcile が冪等なので後から足しても共存する
- 扱う document が数件のうちは、reconcile 自体を作らず手で Vector Store に載せても回る
