# ブランチ戦略 / worktree 運用

tasks.md の Phase を worktree で並行して進めるための規約。2026-08-22 に決定。

## 単位

**`docs/tasks.md` の小見出し 1 つ（`A1`, `C3`, `D2`）= 1 ブランチ = 1 worktree = 1 セッション。**

依存のないタスクは並行してよい。1 セッションで複数タスクを抱えない（context が混ざり、後続タスクの立ち上がりが遅くなる）。

## 命名

```text
branch    : <task-id>-<slug>          例) a1-tooling, a2-domain, b-games-catalog, c-r2
worktree  : ../tribunal-<branch>      例) ../tribunal-a1-tooling
```

worktree は **repo の親ディレクトリ**に掘る。repo 内に置くと worktree 自身が追跡対象に混入しうるため。

```bash
git worktree add -b a1-tooling ../tribunal-a1-tooling
```

タスク完了後:

```bash
git worktree remove ../tribunal-a1-tooling
git branch -d a1-tooling          # マージ済みなら
```

## commit / push

worktree 内で作業している間は、**commit と push を都度確認なしで行ってよい**（global の commit 禁止に対するこの repo 限定の例外）。

- 適用範囲は **worktree 内のみ**。main の作業ツリー（`src/github.com/Sho2010/tribunal` 本体）では従来どおり commit しない
- push 先は worktree の作業ブランチ。main への直 push はこの例外に含まれない
- 区切りのよい単位で commit する

## 触ってよい範囲

**実装タスクのセッションは、自分の worktree 内のファイルだけを触る。**

- worktree 内なら**確認なしでゴリゴリ触ってよい**
- **本体ツリー（`src/github.com/Sho2010/tribunal`）や他の worktree は変更しない。** 読むのは可
  （arch doc / tasks.md の参照は本体側にあってもよい）
- 本体側を直す必要が出たら、それ自体を別タスクとして切り出す。他の worktree の作業と衝突するため

### 強制の仕組み

`claude --worktree <name>` で起動すると、この分離が**機械的に強制される**（規約頼みにしなくてよい）。

```bash
claude --worktree a1-tooling
```

ブロックされるもの:

- メインチェックアウトへの Edit / Write
- メインチェックアウトに解決する Bash の cwd
- `git -C` / `--git-dir` でメインへ向かうコマンド
- brace expansion や unquoted heredoc など、宛先を検証できない構文

手で `git worktree add` して `cd && claude` する方式でもよいが、その場合 Read / Edit / Write は
絶対パスで動くため本体への書き込みは防げない。**規約として守るしかなくなるので `--worktree` 推奨。**

補足:

- **モデル側から cwd は変えられない。** `/cd` `/add-dir` はユーザーが打つコマンドで、Claude からは
  呼べない。Bash の `cd` は次の呼び出しに引き継がれるが、プロジェクト外に出ると自動でリセットされる
- worktree は fresh checkout なので、セッション開始後に `uv sync` が要る
- `.env` のような gitignored ファイルを持ち込むには `.worktreeinclude` に列挙する
- `.gitignore` に `.claude/worktrees/` を足しておく（`--worktree` が使う置き場所）

## PR

**マージは PR 経由。ユーザーが review する。**

```bash
gh pr create --base main --head <branch>
```

- **PR を立てるまでは confirm を挟まずゴリゴリ進める。** 設計判断が必要な場面でも、arch doc / CLAUDE.md の方針で決まるなら自分で決めて進む
- confirm が要るのは、arch doc の決定を覆す場合や、そこに書かれていない新しい設計判断が必要になった場合だけ

### PR 本文

型は `docs/workflow/pr-template.md`。**「なぜそうしたか」は書かない。** 書くのは 4 つだけ。

1. 何を変更したか
2. 何ができるようになったか
3. 注意が必要な点（壊れやすい / 後続タスクが踏む）
4. 読むのに前提が要る点（テクニカル / ドメイン知識）

設計判断の理由は arch doc に書き、PR には `arch §N を更新` の 1 行だけ置く。
自明な設定値、検討して捨てた案、実装の逐次説明、テストケースの列挙は書かない。
**diff を読めば分かることは書かない。**

## 着手順（Phase 1）

依存関係。左が先。

```text
A1 (lint/format/typecheck/test)
     ↓  ※ config が全 worktree に効くので、A1 だけ先にマージしてから残りを切る
  ┌──┴──┬─────────┐
  A2    B1+B2     C1+C2         ← 並行可
  │       │         │
  └───┬───┘         │
      C3+C4 ────────┤           ← C3 は A2 の ContentType を参照
      D1 ───────────┤
                    ↓
                   D2            ← C2 の ETag と C3 の catalog を食う
                    ↓
                   E1
                    ↓
                   H1
```

Phase 1 の完了条件は tasks.md を参照。
