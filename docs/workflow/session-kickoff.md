# タスクセッションの立ち上げ方

新しい worktree でセッションを開くときの手順と、渡す指示のテンプレート。

## 手順

```bash
claude --worktree <task-id>-<slug>
```

`--worktree` なら本体ツリーへの書き込みが機械的にブロックされる（branching.md「強制の仕組み」）。
worktree は fresh checkout なので、セッション開始後に `uv sync` を走らせる。

既に `git worktree add` で切ってある場合は `cd` して `claude`。ただしこの場合、本体への書き込みは
規約頼みになる。

セッションの最初に以下を伝える。CLAUDE.md は worktree 内にもあるので自動で読まれる。

## 指示テンプレート

```text
docs/tasks.md の <task-id> をやる。

前提:
- docs/workflow/branching.md の規約に従う（worktree 内なので commit / push は確認不要、
  PR を立てるまで confirm 少なめで進める）
- 設計の正は docs/Board Game AI - Architecture Context and Design Decisions.md
- CLAUDE.md の「採らない案」を再提案しない

完了したら PR を立てる。本文は docs/workflow/pr-template.md の型に従う
（WHY は書かない。変更 / できるようになったこと / 注意点 / 前提の 4 つだけ）。
```

## 渡す前に確認すること

- **そのタスクの依存が満たされているか**（branching.md の着手順）。A1 未マージのまま A2 を始めると lint 設定が後追いになる
- **arch doc の該当節**を指示に添える。tasks.md の記述は分解であって理由が書かれていない。理由は arch doc 側にある

| task | 読むべき arch 節 |
|---|---|
| A2 | §37（Authority / ContentType / metadata 方針）, §38 |
| B1 / B2 | §16 |
| C1 / C2 | §4, §6 |
| C3 / C4 | §6（metadata の置き場所、YAML 1.1 の `language: no` 問題） |
| D1 / D2 | §5（reconcile が冪等）, §7 |
| E1 | §11（file_search から始めてよいが Retrieval API を挟める構造に）, §38「port を切るのは retrieval だけ」 |
| H1 | §20, §21（3 秒 ACK） |

## 注意

- **rulebook 本文を repo に置かない（arch §4, 厳守）。** PDF / page image / 変換後 Markdown はすべて R2。sync CLI が repo 内に bytes を書き出さない設計にする
- `note.md` はユーザー個人用。触らない
- レイヤの依存方向は `entrypoints → adapters → application → domain`。`adapters/` `application/` から `knowledge/` を import したら設計が壊れたサイン
