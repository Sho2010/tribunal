# オーケストレーション

タスクを並行で走らせるときの、状態管理・セッション間通信・自走の組み合わせ方。

3 つの層がある。**排他ではなく重ねて使う。**

| 層 | 役割 | 実体 |
|---|---|---|
| 状態 | 進行状況の single source of truth | `docs/workflow/status.md`（git に残る） |
| 通信 | セッション間の問い合わせ / 報告 | `ListAgents` / `SendMessage` |
| 実行 | タスクを自走させる | `claude --worktree` + `/goal` |

状態を git に置くのが土台。通信が届かなくても、セッションが落ちても、`status.md` を読めば現在地が
分かる状態を保つ。

---

## ユーザーがタスクを指示する方法

### 1. 単発で 1 タスクを走らせる（基本）

```bash
claude --worktree a1-tooling
```

セッションが開いたら:

```text
docs/workflow/tasks/a1-tooling.md の A1 をやる。
```

指示書が無いタスクなら:

```text
docs/tasks.md の B1 と B2 をやる。docs/workflow/session-kickoff.md の前提に従う。
```

### 2. 自走させる（`/goal`）

セッション内で `/goal` に**検証可能な終了条件**を渡すと、条件を満たすまでターンを繰り返す。
各ターン後に判定モデルが達成 / 未達 / 不可能を評価する。

```text
/goal uv run ruff check . と uv run mypy と uv run pytest が全部通り、CI が緑で、PR が立っている
```

条件の書き方が肝心。**コマンドの終了状態など機械的に確認できる形**にする。

- 良い: `pytest が全部通り、ruff check がエラーゼロで、PR が立っている`
- 悪い: `コードがきれいになっている`（判定不能で止まらない）

`/loop`（時間間隔で繰り返す）とは別物。CI 待ちのようなポーリングは `/loop`、完了条件がある実装は `/goal`。

### 3. 完全非対話で回す（CI / 放置したいとき）

```bash
claude -p "/goal 全テストが通り PR が立っている" \
  --permission-mode auto \
  --output-format stream-json --verbose
```

permission の扱いは危険度順に:

1. `--allowedTools "Read,Edit,Bash(git *),Bash(uv run *)" --permission-mode dontAsk` — 最も安全。許可を明示
2. `--permission-mode auto` — 分類器が安全な操作を自動承認。誤判定の可能性あり
3. `--dangerously-skip-permissions` — **コンテナ / VM 内でのみ。** ホストでは使わない

この repo はホストで動かすので **1 か 2**。3 は使わない。

### 4. 司令塔に聞く

このセッション（オーケストレーション役）に状況を聞く / 次の判断をさせる:

```text
status.md 見て、いま何を並行で切れる？
```

```text
A1 の PR 出たからマージした。次いこう。
```

---

## 司令塔セッションの役割

**実装はしない。** 状態管理と交通整理に徹する。実装に手を出すと context が埋まって全体が見えなくなる。

やること:

- `status.md` を読んで、**依存が解けたタスク**と**並行できる組み合わせ**を答える
- タスク完了の報告を受けて `status.md` を更新する
- 横断的な判断（arch doc に書かれていない設計判断が複数タスクに影響する場合）を記録する
- 走っているセッションに `ListAgents` / `SendMessage` で問い合わせる

やらないこと:

- 実装タスクのコードを書く
- ユーザーの review を代行する（PR の可否はユーザーが決める）

---

## セッション間通信

`ListAgents` でこのマシン上の他の Claude セッションが見える。`SendMessage` で名前を指定して送る。

```text
ListAgents → tribunal-b7 [66e46d] のような名前が返る
SendMessage({to: "tribunal-b7", message: "..."})
```

**セッション名は起動ごとに変わる。** 指示書に名前をハードコードせず、`ListAgents` で探す。

実装セッション側の使い方:

- 詰まったとき、横断的な判断が要るときに司令塔へ問い合わせる
- タスク完了時に報告する（ただし **`status.md` の更新が本体**。通信は補助）

通信は届かないことがある（相手が停止中、セッションが落ちた）。**通信が失敗しても `status.md` を見れば
状態が分かる**構造を崩さない。

---

## サブエージェントによる並行実行

ユーザーが明示的に依頼した場合のみ、司令塔が Agent ツールで実装エージェントを起動する。

```text
A2 と B1+B2 を並行でサブエージェントに投げて
```

- `isolation: "worktree"` を指定して worktree を分ける（ファイル衝突を防ぐ）
- PR を立てるところまでやらせて、**review はユーザーが行う**
- 機械的なタスク向け。設計判断が要るタスクは対話セッションでやる

**依頼が無い限り使わない。** review が飛ぶため、これがデフォルトになると PR を挟む意味が薄れる。

---

## 典型的な流れ

```text
1. ユーザー: claude --worktree a1-tooling で A1 を開始
2. 実装セッション: /goal で自走 → PR を立てる → status.md を「PR」に更新
3. ユーザー: PR を review してマージ
4. ユーザー: 司令塔に「A1 マージした」
5. 司令塔: status.md を「済」に更新、次に切れる 4 本（A2 / B / C / D1）を提示
6. ユーザー: 好きな本数を並行で開始
```
