# ADR 0004: Rule corpus と Strategy corpus を分離する

- Status: Accepted
- Date: 2026-08-19

## Context

最初は metadata filtering だけで単一 Vector Store にまとめる案もあった。
検索性能の観点では単一で足りる。

しかし Rule 回答の根拠に community opinion や個人の分析が混ざると、
非公式な情報を公式ルールとして提示することになる。

## Decision

Rule Store と Strategy Store を分離する。**理由は検索性能ではなく trust boundary。**

```text
Rule Store     : rulebook / errata / official FAQ
Strategy Store : strategy article / card guide / community discussion / play log / personal analysis
```

この境界は複数の層で同じ線を引く。

- Vector Store が別（`TRIBUNAL_RULE_VECTOR_STORE_ID` / `TRIBUNAL_STRATEGY_VECTOR_STORE_ID`）
- ディレクトリが別（`games/<game_id>/rule/` と `strategy/`）
- protocol prompt が別（[0006](0006-rule-adjudicator-protocol.md) / [0007](0007-strategy-is-not-rule.md)）

**片方の Store が未設定のとき、もう片方へ fallback しない。** Store ID が無ければ `KeyError` で落とす。
fallback を許すと Rule 資料で strategy を答える（またはその逆）経路ができる。

情報の信頼レベルは 4 段階で扱い、Rule 回答の根拠に使えるのは `official` / `publisher` まで。

```text
official     公式ルールブック / 公式FAQ / errata
publisher    出版社・ローカライズ元の公式見解
community    BGG / Reddit / wiki など
personal     自分のプレイ知見・分析
```

## Consequences

- Rule 回答が community の記述を引くことが、構造上起こらない
- Strategy Store が未整備のとき、strategy 質問は Rule で代替されず「答えられない」と返る
- Store が 2 つあるので ingest も 2 系統になる
- 「ルールにも戦略にも跨る質問」を 1 回の検索で扱えない（[0008](0008-no-hybrid-intent.md) を参照）
