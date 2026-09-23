# thread context と standalone question

## Slack conversation model

Slack thread を conversation 単位として使う（`thread_ts` = conversation_id）。

```text
@bot ヌースフィヨルドの給仕について教えて
   └─ bot response
   └─ じゃあ2人戦だと？        ← follow-up
```

thread 履歴は Slack から取得する（会話履歴 DB は持たない。決定 0011）。

## standalone question

follow-up をそのまま検索しない。thread context から独立した質問に書き換えてから retrieval へ渡す。

```text
じゃあ2人戦だと？
  ↓
ヌースフィヨルドの Serve Fish アクションについて、2人戦ではどのように処理が変わるか？
```

この変換は Retrieval の前、Intent 判定の前に行う
（Intent 判定が thread を見ない前提はこれに依存している。決定 0008）。

## 現状との差

`thread_ts` は返信先と hold 名にしか使っていない。**thread 履歴の取得も standalone question 生成も無い。**
現在 Intent 判定に渡っているのは生の質問文。
