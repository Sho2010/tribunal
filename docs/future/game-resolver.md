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

catalog は `games/games.yaml`（実在するが、まだ読むコードが無い）。
`aliases` と `identifying_terms` がこの解決のために置いてある。

## 現状との差

`AnswerService.ask(question, game_id=None)` の `game_id` は配線済みだが、
**Slack adapter が渡していないので常に `None`**。結果、Vector Store は全ゲームを無フィルタで検索している。
`games/` に複数ゲームの資料があるため、混線しうる。

## 受け入れ条件

```text
ゲーム名を書かずに質問して、意図したゲームとして解決される
特定が曖昧なときは聞き返す
```

※ ここでの「曖昧」はゲームの特定の話。intent（ルールか戦略か）が曖昧なときは
聞き返さず Rule に倒す（決定 0008）。別の話なので混同しない。
