# eval

RAG の改善を体感ではなく数値で測る。**未実装。**
harness は promptfoo（ADR 0014）。runner は自作しない。

## 置き場所

```text
evals/
  promptfooconfig.yaml
  provider.py        # call_api -> AnswerService
  cases/
    nusfjord.yaml
```

`evals/` は `games/` と同じく `src/` の外。promptfoo は npm パッケージなので bot の実行環境には入らない。

## ケースの形

```yaml
question:
expected:
required_evidence:
traps:
```

`traps` に入れる観点（Rule Adjudicator Protocol が対処している失敗モードそのもの。ADR 0006）:

- setup とゲーム中 rule の混同
- 資源の支払いと配置の混同
- 例示からの誤一般化
- exception 見落とし
- 複数 page 横断

まず 20〜50 問。ただし最初は 1 ゲーム 3〜5 問で経路を通し、数値が出るところまでを 1 単位とする。

## Adjudication Eval

最終回答の質を採点する。promptfoo の assertion で見る:

- 出力フォーマット（【ルール引用】→【分析・検討】→【結論】の順）
- 裁定が `expected` と一致するか
- `required_evidence` が実際に引用されているか
- `traps` を踏んでいないか
- 記載がない場合に、記載が無い旨を答えているか

**着手前に片付けること:** 「記載なし」の表現が `adjudicator.md` 内で 3 通りある
（`資料から明確な記載はありません` / `記載が見つかりません` / `記載なし`）。
assertion を書く前に 1 つへ寄せる。

## Retrieval Eval

**現状では書けない。** `Answer.sources` が title / uri しか持たず file_id 単位で dedup されるため、
chunk / score / 順位が残らない（ADR 0010）。明示的な Retrieval API が入ってから。

見るもの: 正しい section を検索できたか / ranking / 無関係な chunk。

## モデル比較

Retrieval / Protocol / Context を改善したあとで、同一 eval を使ってモデルと reasoning effort を比較する。
**モデル差ではなく pipeline 改善の効果を測れる状態にしてから**やる。

## 受け入れ条件

```text
生 PDF のまま baseline の数値が出ている
Adjudicator Protocol の適用前後で差分が測れる
```

Retrieval Eval が入ったあと:

```text
retrieved chunk と score をアプリ側で確認できる
誤答を retrieval miss / reasoning miss に切り分けられる
数値が baseline から改善している
```
