# ADR 0007: Strategy を Rule Adjudicator の拡張にしない

- Status: Accepted
- Date: 2026-08-26

## Context

Rule と Strategy はどちらも「ボードゲームの知識に答える」ので、
1 つの protocol を拡張して両方を賄う案があった。

しかし求められる推論が違う。

```text
Rule     : 正しい唯一の解釈へ近づける
Strategy : 複数の候補からより良いプレイを推論する
```

## Decision

Rule Adjudicator を拡張せず、別の Strategy Analyst Protocol を用意する。

Strategy は唯一の正解がないので、回答に **前提 / 評価軸 / 複数候補 / trade-off** を明示させる。
候補は必ず複数（最低 2 つ）挙げ、それぞれの opportunity cost と risk を書かせる。

Strategy 側には Rule との境界も明示する。

- 戦略資料は非公式。**戦略資料の記述をルールとして提示しない**
- ルールの可否・裁定を問う質問には、この場で裁定を下さず、ルール資料での確認が必要だと伝える
- 戦略の前提としてルールに触れるときは「戦略資料上ではこう扱われている」と情報源の性質を明示する

prompt は `src/tribunal/application/strategy/prompts/analyst.md`。

## Consequences

- protocol が 2 つあるので、質問をどちらに振るかの判定が必要になる（[0008](0008-no-hybrid-intent.md)）
- Strategy 回答が「断定しない」ため、歯切れが悪く感じられる。これは意図した挙動
- Rule と Strategy の両方に跨る質問を 1 回で扱えない
