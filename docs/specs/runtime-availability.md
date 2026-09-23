# 常駐と wake

Sprites は inbound request が途切れると pause し、走っている処理も一緒に凍る。
その上で応答を落とさないことを保証する。

## 要件

- Slack の mention に対し、**3 秒以内に ACK を返す**
- 回答生成は ACK と分離して走らせる
- **生成中は Sprite を pause させない。** 生成が 30 秒を超えても応答が返る
- pause から復帰（wake）したあと、再 mention で応答する
- cold wake でも service が自動で再起動し、**手動操作を必要としない**
  （これはアプリ側のコードではなく Sprites の service 機能が担う。
  常駐プロセスを `exec` の foreground 起動にすると成立しない）
- Sprites 以外の環境（ローカル / CI）でも、pause 対策なしで動く

## 受け入れ条件

実機でしか確認できない。回帰したときはこれで気づく。

```text
Slack で mention する
 → 3 秒以内に受付が返る
 → 続いて回答が同じ thread に返る
```

```text
30 秒以上放置して warm に落とす
 → 再 mention する
 → wake して応答する
```

```text
cold wake（プロセスが落ちた状態）から mention する
 → service が自動で再起動して応答する
 → 手で起動しなおす必要がない
```

```text
生成に 30 秒以上かかる質問を投げる
 → 途中で凍らず、最後まで回答が返る
```

## 保証していないこと

- 生成の所要時間そのもの。長い質問は長いままで、打ち切らない
- pause 対策のコードにテストが無い。実機で確認するしかない
- HTTP port を持てる service は 1 つだけ。2 つ目を足すと成立しない

## 関連

決定の理由: `tribunal-decisions` の 0012 / 0013。
実機の挙動と運用手順は `docs/sprites-pause-and-async-work.md`。
