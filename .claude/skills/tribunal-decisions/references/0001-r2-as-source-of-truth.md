# ADR 0001: R2 を document の source of truth にし、SoT を役割で分ける

- Status: Accepted
- Date: 2026-08-19

## Context

rulebook / FAQ / errata の実体をどこに置き、何を authoritative とするかを決める必要があった。
OpenAI Vector Store をそのまま原本にすると、壊れたとき / 作り直したときに復元元が無い。
同じ情報を複数箇所で mutable に持つと不整合が起きる。

初期案では knowledge catalog を SQLite / RDBMS で持つことを検討していた。

## Decision

document の bytes の唯一の authoritative state は Cloudflare R2 とし、OpenAI Vector Store は
R2 から再生成可能な検索 index として扱う。Vector Store が壊れても R2 から再構築できることを前提にする。

SoT は 1 箇所ではなく、役割で 3 つに分ける。

```text
document bytes  → R2
desired catalog → git repo (meta.yaml / Markdown の front matter)
actual state    → OpenAI Vector Store (file attributes)
```

catalog を git に置くのは、review / 履歴 / CI での schema validation が効き、編集が容易なため。
SQLite / RDBMS は採らない。

**desired と actual を混ぜない。** 観測結果（`openai_file_id`、同期済み hash など）を catalog へ書き戻さない。

## Consequences

- Vector Store は捨てて作り直せる。ingest の失敗が原本を損なわない
- catalog の変更が PR に乗るので、何を ingest 対象と宣言したかが review できる
- 3 箇所あるので、どれが desired でどれが actual かを常に意識する必要がある
- catalog が git にあるため R2 の event では catalog 変更を検知できない（[0005](0005-ingest-is-reconcile.md) の前提）
