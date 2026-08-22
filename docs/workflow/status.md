# Phase 1 タスクの依存と決定ログ

Phase 1 = 「1ゲームのルールに答えられる（最小 Rule RAG の縦切り）」。完了条件は `tasks.md` を参照。

**進捗はここに書かない。** ブランチと PR の状態は git / gh が正確に持っている。

```bash
gh pr list --state all     # 何が PR 中 / マージ済みか
git branch -a              # 何に着手済みか
```

手で更新する進捗表は必ず腐る（A1 が merged 後も「未着手」のまま残った）。
このファイルが持つのは **git から読み取れないもの＝依存関係と、なぜそう決めたか**だけ。

## 依存

| task | branch | 依存 | メモ |
|---|---|---|---|
| A1 lint/format/typecheck/test | `a1-tooling` | なし | **済**（PR #1）。config が全 worktree に効くので、これが最初のボトルネックだった |
| A2 ドメインモデル | `a2-domain` | A1 | arch §37（Authority / ContentType）, §38 |
| B1+B2 games.yaml + Schema | `b-games-catalog` | A1 | arch §16 |
| C1 R2 設計 | `c-r2` | A1 | **済**。arch §4, §6。C2 client は Phase 5 送り |
| C3+C4 meta.yaml + Schema | `c-documents` | A2 | arch §6。`edition` は optional |
| D1 Vector Store 基本 | `d1-vector-store` | A1 | arch §7 |
| E1 Responses API + File Search | `e1-file-search` | D1 | arch §11, §38（port を切るのは retrieval だけ） |
| C2 R2 client / D2 sync CLI | — | — | Phase 5（crawl で件数が増えてから） |
| H1 Slack → AnswerService 接続 | `h1-slack-wiring` | E1 | arch §20, §21（3 秒 ACK） |

## 並行できる組み合わせ

A1 が済んだので、**A2 / B1+B2 / C1+C2 / D1 の 4 本は互いに独立**。同時に走らせてよい。

その後 C3+C4 → D2 → E1 → H1 は直列。

## 決定ログ

判断が必要になって決めたことを、日付つきで残す。PR 本文にも書くが、横断的な決定はここにも。

- 2026-08-22 ブランチ戦略を決定（`docs/workflow/branching.md`）。1 小見出し = 1 worktree = 1 セッション、
  `claude --worktree` で本体保護、マージは PR 経由
- 2026-08-22 `docs/a.md`（arch doc の旧版）を削除。差分 4 箇所はすべて CLAUDE.md の「採らない案」に
  載っている却下済みの案だった
- 2026-08-22 `games/` は `.gitignore` しない。crawl 結果の保存と catalog を repo に置くため
