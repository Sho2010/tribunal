# Phase 1 進行状況

Phase 1 = 「1ゲームのルールに答えられる（最小 Rule RAG の縦切り）」。完了条件は `tasks.md` を参照。

**このファイルが進行状況の single source of truth。** 各セッションは自分のタスクの状態が変わったら
ここを更新してから次に進む。司令塔セッションはここを読んで次に切るタスクを判断する。

更新は本体ツリーの main へ直接 commit してよい（worktree からでもこのファイルだけは例外）。
衝突を避けるため、**自分の行だけ**を書き換える。

## 状態の凡例

| 状態 | 意味 |
|---|---|
| `未着手` | worktree も切っていない |
| `作業中` | worktree があり、セッションが動いている（または中断中） |
| `PR` | PR を立てた。ユーザーの review 待ち |
| `済` | main にマージ済み |
| `保留` | 依存待ちや判断待ちで止めている。理由を必ず書く |

## タスク

| task | 状態 | branch | PR | 依存 | メモ |
|---|---|---|---|---|---|
| A1 lint/format/typecheck/test | 未着手 | `a1-tooling` | - | なし | 指示書 `tasks/a1-tooling.md`。**これをマージするまで他を切らない**（config が全 worktree に効く） |
| A2 ドメインモデル | 未着手 | `a2-domain` | - | A1 | arch §37（Authority / ContentType）, §38 |
| B1+B2 games.yaml + Schema | 未着手 | `b-games-catalog` | - | A1 | arch §16 |
| C1+C2 R2 設計 + client | 未着手 | `c-r2` | - | A1 | arch §4, §6 |
| C3+C4 documents.yaml + Schema | 未着手 | `c-documents` | - | A2, C2 | arch §6。YAML 1.1 の `language: no` 問題 |
| D1 Vector Store 基本 | 未着手 | `d1-vector-store` | - | A1 | arch §7 |
| D2 sync CLI | 未着手 | `d2-sync-cli` | - | C2, C3, D1 | arch §5。冪等な reconcile |
| E1 Responses API + File Search | 未着手 | `e1-file-search` | - | D2 | arch §11, §38（port を切るのは retrieval だけ） |
| H1 Slack → AnswerService 接続 | 未着手 | `h1-slack-wiring` | - | E1 | arch §20, §21（3 秒 ACK） |

## 並行できる組み合わせ

A1 マージ後、**A2 / B1+B2 / C1+C2 / D1 の 4 本は互いに独立**なので同時に走らせてよい。

その後 C3+C4 → D2 → E1 → H1 は直列。

## 決定ログ

判断が必要になって決めたことを、日付つきで残す。PR 本文にも書くが、横断的な決定はここにも。

- 2026-08-22 ブランチ戦略を決定（`docs/workflow/branching.md`）。1 小見出し = 1 worktree = 1 セッション、
  `claude --worktree` で本体保護、マージは PR 経由
- 2026-08-22 `docs/a.md`（arch doc の旧版）を削除。差分 4 箇所はすべて CLAUDE.md の「採らない案」に
  載っている却下済みの案だった
- 2026-08-22 `games/` は `.gitignore` しない。crawl 結果の保存と catalog を repo に置くため
