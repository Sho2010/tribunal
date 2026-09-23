---
name: tribunal-decisions
description: tribunal の過去の設計判断とその理由を調べる。変更が下の表の領域に触れるときだけ読む。現在の振る舞いはコードと docs/specs/ が定義しており、この skill は定義しない。
---

# tribunal decisions

**この skill は現在の振る舞いを定義しない。** 制約がなぜそうなっているかを思い出すためだけに使う。

判断の優先順位:

1. **動いているコードとテスト** — 実際の振る舞いはこれを見る
2. **`docs/specs/`** — 保証しているはずの契約
3. **この skill** — 過去の意図と trade-off。**現在の要件ではない**

1 と 2 は「実際にどうなっているか」と「どうあるべきか」なので、**どちらかが自動的に正ではない。**

食い違っていたら、**どちらが正しいかを人に確認してから直す**（実装がバグっている可能性がある）。
**accepted な決定記録の中身は書き換えない。**

**作業に関係する 1 本だけ読む。全部ロードしない。**

## 決定一覧

| No. | Date | Status | 決定 | 読むとき |
| ---: | --- | --- | --- | --- |
| 0001 | 2026-08-19 | Accepted | [R2 を source of truth にし、SoT を役割で分ける](references/0001-r2-as-source-of-truth.md) | document の置き場所、catalog の持ち方、Vector Store の再生成を変えるとき |
| 0002 | 2026-08-19 | Accepted | [metadata を path から導出せず宣言する](references/0002-metadata-is-declared-not-derived.md) | R2 の path 構造、ディレクトリの区分、metadata の取得元を変えるとき |
| 0003 | 2026-08-19 | Accepted | [metadata の置き場所はファイル形式で決める](references/0003-metadata-location-follows-file-format.md) | `meta.yaml` や front matter の schema を足す / 変えるとき |
| 0004 | 2026-08-19 | Accepted | [Rule / Strategy corpus を分離する](references/0004-split-rule-and-strategy-stores.md) | Store の分け方、fallback、情報の信頼レベルの扱いを変えるとき |
| 0005 | 2026-08-19 | Accepted | [ingest を reconcile にする](references/0005-ingest-is-reconcile.md) | ingest の起動方法、冪等性、R2 event の扱いを変えるとき |
| 0006 | 2026-08-22 | Accepted | [Rule Adjudicator Protocol を必須にする](references/0006-rule-adjudicator-protocol.md) | `adjudicator.md` を変える、Rule 回答のフォーマットや検証手順を変えるとき |
| 0007 | 2026-08-26 | Accepted | [Strategy を Rule の拡張にしない](references/0007-strategy-is-not-rule.md) | `analyst.md` を変える、Strategy 回答の形や Rule との境界を変えるとき |
| 0008 | 2026-08-26 | Accepted | [hybrid を作らず、曖昧なら Rule に倒す](references/0008-no-hybrid-intent.md) | `Intent` の値を増やす、Ambiguous の扱いや聞き返しを変えるとき |
| 0009 | 2026-08-26 | Accepted | [明示タグを主経路にし keyword は補助](references/0009-intent-tags-and-keywords.md) | タグの形式、keyword、判定順、untagged の注記を変えるとき |
| 0010 | 2026-08-19 | Accepted | [File Search で始め、retrieval と reasoning を切り分ける](references/0010-retrieval-must-be-debuggable.md) | retrieval の実装を差し替える、PDF 前処理や multi-query を足すとき |
| 0011 | 2026-08-19 | Accepted | [会話履歴 DB を持たない](references/0011-no-conversation-history-db.md) | thread context の取得方法、過去の Bot 回答の扱いを変えるとき |
| 0012 | 2026-08-19 | Accepted | [Sprites を runtime にし pause 対策を持つ](references/0012-sprites-runtime.md) | `task_hold.py`、service 構成、Sprite 名、deploy 手順を触るとき |
| 0013 | 2026-08-22 | Accepted | [Slack では mention だけ受け thread に返す](references/0013-slack-mention-only.md) | Slack の event 種別、ack と生成の分離、返信先を変えるとき |
| 0014 | 2026-09-23 | Accepted | [eval runner を自作せず promptfoo を使う](references/0014-do-not-build-an-eval-runner.md) | eval の置き場所、harness、assertion の作り方を決めるとき |
| 0015 | 2026-08-19 | Accepted | [Vector Store + File Search で始める](references/0015-use-vector-store-not-direct-file-input.md) | retrieval の経路そのもの、file_id の管理方法を変えるとき |
| 0016 | 2026-09-23 | Accepted | [ingest の自動化は規模が閾値を超えてから](references/0016-automate-ingest-only-past-a-threshold.md) | sync CLI / gc / doctor を作るとき、差分判定の方法を決めるとき |

決定が変わったら、**理由を書き換えずに新しい番号で追加する。**
古い方の Status を `Superseded` にし、両方から相互にリンクする。

## 出自

これらは `docs/Board Game AI - Architecture Context and Design Decisions.md`（1011 行）を
解体して起こした。解体前の最終状態は commit `c9d2fbb`。
