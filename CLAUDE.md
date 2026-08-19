# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 何のプロジェクトか

Slack（将来的に Discord）からボードゲームのルール / 戦略を質問できる RAG chatbot。Python 3.11+ / FastAPI + slack_bolt、パッケージ管理は `uv`。実行環境は Fly.io Sprites。

ゴールは「ルールブック検索 bot」ではなく、**Rule については厳密な裁定者、Strategy については根拠を持った分析者**として振る舞うこと。

現状は **M1（骨組み段階）**: Slack の `app_mention` を受けて固定文字列を返すだけ。retrieval / ingest / R2 / games.yaml はすべて未実装。

## コマンド

```bash
uv sync                                                          # 依存同期
uv run uvicorn src.entrypoints.slack:app --port 8080 --reload    # ローカル起動（.env を読む）
curl localhost:8080/                                             # health: {"status":"ok","platforms":["slack"]}
```

- 環境変数は `.env.example` を `.env` にコピーして設定（`SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`）。`.env` の読み込みは entrypoint（`src/entrypoints/slack.py`）が行う。
- テスト / lint / formatter はまだ導入されていない（tasks.md A1 の残タスク）。構文チェックだけなら `uv run python -m py_compile <files>`。

## ドキュメント

1. **`docs/Board Game AI - Architecture Context and Design Decisions.md`** — 設計判断とその理由。**これが正**。
2. **`docs/tasks.md`** — 実装タスクの分解と推奨実装順。**小見出し 1 つ（`A1`, `B1`, `D3` など）を 1 タスクの単位**として扱う設計になっている。次に何をやるかはここを見る。
3. **`docs/sprites.md`** — Fly.io Sprites 運用リファレンス。`note.md` は初回デプロイ runbook。

初期の実装指示書 `plan.md` (`docs/first-plan.md`) は、現行方針と矛盾する記述で誤判断を招くため削除した（git 履歴に残る。まだ有効だった細目は arch doc §37 に移設済み）。

### 採らない案（提案し直さないこと）

初期案にあったが却下された判断。理由付きで潰れているので、再提案する前に arch doc の該当節を読む。

- **SQLite を knowledge catalog にしない。** R2 / SQLite / OpenAI File / Vector Store の 4 箇所に同じ情報を持つ不整合を避けるため（arch §4）。game 識別用の小さな catalog は `games.yaml` のみ（arch §16）、document の metadata は R2 の path から導出する（arch §6）。会話履歴 DB も持たない（Slack thread から取得、arch §17）。
- **単一 Vector Store + attributes で済ませない。** Rule / Strategy Store を分離する（arch §8）。理由は検索性能ではなく trust boundary。
- **手動 CLI で ingest / sync しない。** R2 Event Notification → Cloudflare Queue → Ingest Worker（arch §5, tasks D2/D3）。CLI は reconciliation / GC（`sync`, `gc`）に限定（tasks D4）。ingest は Sprite ではなく Cloudflare 側に寄せる（arch §3）。
- **File Search の結果からそのまま回答させない。** query decomposition → multi-query retrieval → Rule Adjudicator（arch §9, §10, §34）。
- **retrieval を「Vector Store なし・直接 file input」で始めない。** 一度検討したが破棄（file_id を SQLite で管理する前提だったため）。Vector Store + File Search で進める（tasks D1/E1/M1）。

## アーキテクチャ

レイヤの依存方向は **adapters → application → domain** の一方向。

- `src/domain/` — chat platform 非依存の値オブジェクト（`Answer`, `Source`）。
- `src/application/answer_service.py` — `AnswerService.ask(question, game_id=None) -> Answer`。**Chat adapter が触ってよい唯一の入口**。retrieval はここ以下に実装し、adapter から OpenAI / R2 を直接呼ばない。
- `src/adapters/slack/app.py` — slack_bolt の `App`（HTTP Events モード、署名検証）と `register(app)` で `POST /slack/events` を FastAPI に mount。module import 時に `os.environ[...]` を読むので、**import しただけで Slack の env が必須になる**点に注意。
- `src/app_factory.py` — `create_app(platforms)` が合成の中心。platform ごとに adapter を **遅延 import** して mount するので、有効化していない platform の依存・env を要求しない。新しい platform を足すならここに分岐を追加する。
- `src/entrypoints/<platform>.py` — uvicorn の起動対象。`.env` 読み込み → `create_app([...])`。`src/main.py` は slack entrypoint を re-export する後方互換シム。

Discord は FastAPI に mount できない Gateway（常時 websocket）方式に寄せる方針なので、`app_factory` ではなく独立 entrypoint / 別 service として扱う（対応自体を見送る可能性あり）。

### 目標とする query pipeline（docs §34 / tasks J1）

この順序を崩さない。

```text
Chat Event → Chat Adapter → GameResolver → Thread Context Resolution
  → Standalone Question → Intent Router(rule/strategy/hybrid) → Query Decomposition
  → Retrieval → Rule Adjudicator / Strategy Analyst → Citation → Answer → Chat Adapter
```

### 設計上ぶれさせない前提

- **R2 が唯一の authoritative state**、Vector Store は R2 から再生成可能な derived index。壊れたら R2 から作り直せること。metadata は可能な限り R2 の path から導出する（`games/<game>/official/rulebook/ja/rulebook.pdf` → game_id / authority / content_type / language）。
- **Rule と Strategy を混ぜない。** Rule 回答に community / personal の情報をルール根拠として混ぜない。Rule を Strategy corpus から推測しない。
- **検索結果 1 件で即答させない。** Rule 回答では **Rule Adjudicator Protocol**（docs §9）を prompt として明示するのが必須: 基本ルール / 用語定義 / setup / player count 差 / 例外 / examples / 関連 section を横断確認し、example を一般ルール化しない・推測を公式ルールとして断定しない。回答形式は「結論 → 根拠 → 解釈 → 引用」、原則日本語。
- Strategy は唯一解がないので、Rule Adjudicator を拡張せず別の **Strategy Analyst Protocol**（前提 / 評価軸 / 複数候補 / trade-off を明示）を使う。
- Slack thread を conversation 単位（`thread_ts` = conversation_id）とし、thread 履歴から standalone question を生成して毎回再検索する。**過去の bot 回答は context には使うがルール根拠にはしない**（誤答の連鎖を防ぐ）。
- retrieval / reasoning の切り分けが debug できる構造にする（Responses API の `file_search` 任せにせず、Retrieval API を明示的に挟める形）。モデルを上げる前に Retrieval / Protocol / Context を改善し、同一 eval で比較する。

## Sprites でのデプロイ

詳細は `docs/sprites.md`、手順は `note.md`。落とし穴だけ:

- **ディスクは自動永続、RAM / プロセスは pause で消える。** 常駐プロセスは `exec` の foreground 起動ではなく **service 化**する（cold wake 時に自動再起動される）。checkpoint はディスク永続のためには不要。
- HTTP port を持てる service は **1 つだけ**（8080 を bot が確保）。
- `sprite-env services ...` は Sprite 内部コマンド。ローカルからは `sprite exec -- sprite-env services ...`、または sprites MCP の `service_create` / `service_start` を使う。
- ログ: `sprite exec -- tail -n 50 /.sprite/logs/services/slackbot.log`
- Slack は 3 秒 ACK。wake レイテンシ（warm 100–500ms / cold 1–2s）があるので、重い処理を入れる段階では slack_bolt の lazy listener で即 ack する。
- secret は Sprite のスナップショットに残る（専用 vault なし）。この割り切りは既に合意済み。

`docs/` と `note.md` は現時点で git 未追跡（untracked）。ユーザーの明示的な依頼なしに add / 移動 / 削除しないこと。
