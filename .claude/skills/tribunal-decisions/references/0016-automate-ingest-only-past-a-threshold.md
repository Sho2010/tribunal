# ADR 0016: ingest の自動化は規模が閾値を超えてから

- Status: Accepted
- Date: 2026-09-23

## Context

[0005](0005-ingest-is-reconcile.md) で ingest を reconcile と決めたが、その sync CLI をいつ作るかは別の問題。
同じく、宣言漏れや orphan を検査する gc / doctor をいつ作るかも決めていなかった。

rulebook の規模で考えると:

- **rulebook の改訂は数年に一度**。1 ゲーム数件なら人が差し替えれば済む
- **宣言漏れは、数件のうちは bot が答えないことで気づく。**
  「この質問に答えられないのはおかしい」→ 宣言を忘れていた、と辿れる

つまり小さいうちは、自動化しなくても**人の記憶と bot の挙動が検査機構として働く**。

## Decision

ingest の自動化（sync CLI / gc / doctor）は、**規模が人の把握を超えてから**作る。
閾値は **strategy corpus の crawl を始める時点**。crawl で件数が増えると、
宣言漏れを bot の挙動から辿れなくなる。

それまでは手で Vector Store に載せる。R2 への配置は `scripts/r2.sh`（rclone ラッパー）で足りる。

gc / doctor は作ったあとも **人がたまに手で流すもの**とし、自動実行や CI に載せない。

### 差分判定に ETag を使えない

[0005](0005-ingest-is-reconcile.md) は diff の条件として「R2 の ETag が変わっている → 再 upload」と書いているが、
**この前提は実運用で成立しないことが分かっている。**

```text
ETag は multipart upload で MD5 にならないので checksum 比較に頼らない
```

`scripts/r2.sh` は既にこれを踏んでおり、`--size-only` で回避している。
sync CLI を実装する段では、ETag ではなく size + mtime か、自前の hash を使う。

## Consequences

- sync CLI が無い状態が続く。`meta.yaml` を書いても、Vector Store へは人が載せる
- 宣言漏れの検知が人の記憶に依存する期間がある。crawl を始めたら真っ先に gc が要る
- ETag を信じた実装を書かずに済む。[0005](0005-ingest-is-reconcile.md) の Decision にある
  「ETag が変わっている」は、**判定の意図**として読み、実装手段としては読まない
