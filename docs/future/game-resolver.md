# GameResolver

ユーザーが毎回ゲーム名を書くとは期待しない。質問からどのゲームの話かを解決する。

```text
User Question → GameResolver → Standalone Question → Retrieval
```

優先順位の案:

1. thread context に既知の `game_id`
2. question 中の game name
3. alias
4. identifying terms
5. LLM による推定
6. confidence が低ければユーザーへ確認

高 confidence なら確認を挟まず回答してよい。

catalog は `games/games.yaml` の `name` / `aliases` / `identifying_terms`。

## 現状との差

2〜4 は入っている（name と alias は同じ段で扱い、当たれば identifying terms は見ない）。
候補が 2 つ以上なら候補名を添えて「特定できない」と返すので、6 の聞き返しは
「ゲーム名を添えて質問し直してもらう」形で代替している。

まだ無いもの:

- 1（thread context）。Slack adapter は `game_id` を渡していない
- 5（LLM 推定）と confidence。候補 0 のときは、Rule Store を持つゲームが 1 つだけならそれに決める
- edition の解決（`editions` は読んでいない）
- 部分一致なので、短い identifying term（`株` など）は無関係な質問にも当たる

## 受け入れ条件

```text
ゲーム名を書かずに質問して、意図したゲームとして解決される
特定が曖昧なときは聞き返す
```

※ ここでの「曖昧」はゲームの特定の話。intent（ルールか戦略か）が曖昧なときは
聞き返さず Rule に倒す（決定 0008）。別の話なので混同しない。
