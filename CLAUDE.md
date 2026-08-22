# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 何のプロジェクトか

**tribunal** — Slack（将来的に Discord）からボードゲームのルール / 戦略を質問できる RAG chatbot。Python 3.11+ / FastAPI + slack_bolt、パッケージ管理は `uv`。実行環境は Fly.io Sprites。

ゴールは「ルールブック検索 bot」ではなく、**Rule については厳密な裁定者、Strategy については根拠を持った分析者**として振る舞うこと。

コードは **Phase 0（Sprites + Slack 疎通）** の段階: `app_mention` を受けて固定文字列を返すだけ。retrieval / ingest / R2 / catalog はすべて未実装。着手順は `docs/tasks.md` 先頭の Phase を見る。

## コマンド

```bash
uv sync                                                          # 依存同期
uv run uvicorn tribunal.entrypoints.slack:app --port 8080 --reload    # ローカル起動（.env を読む）
curl localhost:8080/                                             # health: {"status":"ok","platforms":["slack"]}
```

- 環境変数は `.env.example` を `.env` にコピーして設定（`SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`）。`.env` の読み込みは entrypoint（`src/tribunal/entrypoints/slack.py`）が行う。
- テスト / lint / formatter はまだ導入されていない（tasks.md A1 の残タスク）。構文チェックだけなら `uv run python -m py_compile <files>`。

## 開発の進め方

**`docs/tasks.md` の小見出し 1 つ（`A1`, `C3`, `D2`）= 1 ブランチ = 1 worktree = 1 セッション。** 詳細は `docs/workflow/branching.md`。

- worktree は `claude --worktree <task-id>-<slug>` で作る。本体ツリーへの書き込みが機械的にブロックされる
- **worktree 内では commit / push を確認なしで行ってよい。PR を立てるまで confirm 少なめで進める。** マージは PR 経由（ユーザーが review する）
- **本体ツリー（main の作業ツリー）では commit しない。** worktree 内のファイルだけを触る（本体の読み取りは可）
- **PR 本文に「なぜそうしたか」を書かない。** 書くのは「何を変更したか / 何ができるようになったか / 注意が必要な点 / 読むのに前提が要る点」の 4 つだけ。設計判断の理由は arch doc 側。型は `docs/workflow/pr-template.md`

### コメント / docstring

**PR 本文と同じ基準。コード内に「なぜこう設計したか」を書かない。** 設計の理由は arch doc にあり、
コード側に写すと二重管理になって片方が腐る。

- **docstring は 1 行。** 何をする関数かだけ。名前と型注釈で分かるなら書かない
- 複数段落の docstring を書かない。**背景 / 検討経緯 / 「〜のため」はすべて削る**
- コードを言い換えただけのコメントは書かない
- ソースに残すのは、**コードを読んでも分からない外部制約**だけ。
  外部 API の非自明な挙動（「`App()` は生成時に `auth.test` を叩く」）、仕様上の制約、ドメイン知識。
  「なぜこう書いたか」ではなく「**そう書かないと何が起きるか**」の形にする

それ以外の「ここはこう考えた」の類はソースに入れない。**PR の該当行コメントで伝える**
（運用の詳細は未確定）。

## ドキュメント

1. **`docs/Board Game AI - Architecture Context and Design Decisions.md`** — 設計判断とその理由。**これが正**。
2. **`docs/tasks.md`** — 先頭の **Phase（機能マイルストーン）が着手順で、各 Phase に完了条件がある**。その下の A〜O がタスク分解。**小見出し 1 つ（`A1`, `C3`, `D2` など）を 1 タスクの単位**として扱う。次に何をやるかはここを見る。
3. **`docs/sprites.md`** — Fly.io Sprites 運用リファレンス。`note.md` は初回デプロイ runbook。
4. **`docs/workflow/`** — 開発の進め方。`branching.md`（worktree / ブランチ / PR 規約）、`pr-template.md`（PR 本文の型）、`session-kickoff.md`（タスクセッションの立ち上げ方）、`tasks/<task-id>.md`（個別タスクの指示書）。

初期の実装指示書 `plan.md` (`docs/first-plan.md`) は、現行方針と矛盾する記述で誤判断を招くため削除した（git 履歴に残る。まだ有効だった細目は arch doc §37 に移設済み）。

### 採らない案（提案し直さないこと）

検討して却下された判断。理由付きで潰れているので、再提案する前に arch doc の該当節を読む。

- **SQLite を knowledge catalog にしない。** 同じ情報を複数箇所で mutable に持つ不整合を避けるため（arch §4）。会話履歴 DB も持たない（Slack thread から取得、arch §17）。
- **R2 の path から metadata を導出しない。** path を metadata schema にすると typo が silently 通り、次元を足すと全 path の move + 再 ingest になる。しかも player_count / edition / 多言語は階層に収まらないので機構が 2 つに増える（arch §6）。path は locator（`game_id` prefix のみ）。
- **単一 Vector Store + attributes で済ませない。** Rule / Strategy Store を分離する（arch §8）。理由は検索性能ではなく trust boundary。
- **event driven ingest（R2 Event → Cloudflare Queue → Worker）を v1 で作らない。** catalog が git 上にあるので、この経路が担当できるのは「R2 へ直接置いた場合の自動取り込み」だけで、人の手間は sync CLI と変わらない（arch §5, tasks D3 は保留）。
- **File Search の結果からそのまま回答させない。** query decomposition → multi-query retrieval → Rule Adjudicator（arch §9, §10, §34）。
- **retrieval を「Vector Store なし・直接 file input」で始めない。** 一度検討したが破棄（file_id を SQLite で管理する前提だったため）。Vector Store + File Search で進める（tasks D1/E1/M1）。

## アーキテクチャ

レイヤの依存方向は **entrypoints → adapters → application → domain** の一方向。全体のディレクトリ構成は arch §38（現状は下記の一部だけが存在する）。

```text
catalog/              # 宣言データ (games.yaml, documents/<game_id>.yaml, schema/)
evals/                # eval dataset
src/tribunal/
  entrypoints/        # uvicorn 起動対象
  adapters/           # inbound: chat platform
  application/        # answer_service.py, ports.py, pipeline/, rule/, strategy/
  domain/
  infra/              # outbound: openai/, r2/
  knowledge/          # catalog 読み込み / front matter / reconcile
  eval/  cli/
```

命名で守ること:

- **`adapters/` は inbound（呼ばれる側）専用。** OpenAI / R2 のような outbound client は `infra/` に置く。両方を adapters に入れると依存方向が逆のものが同居する。
- **`adapters/` `application/` から `knowledge/` を import しない。** ingest は手元 / CI で走り、Sprite 上の bot は R2 も catalog も触らない。逆向き（`cli/` → `knowledge/` → `infra/`）は正常。
- **port を切るのは retrieval だけ**（E1 の `file_search` → E2 の Retrieval API で実装が 2 つになるため）。他は必要になるまで Protocol を作らない。
- **protocol prompt は `.md` ファイル**として使う側にコロケートし（`application/rule/prompts/adjudicator.md`）、コード内の文字列リテラルにしない。eval で前後比較する対象なので diff が見えることが要件。
- **`catalog/` と `evals/` は `src/` の外**。人が宣言・レビューするデータでコードではない。

現在あるモジュール:

- `src/tribunal/domain/` — chat platform 非依存の値オブジェクト（`Answer`, `Source`）。
- `src/tribunal/application/answer_service.py` — `AnswerService.ask(question, game_id=None) -> Answer`。**Chat adapter が触ってよい唯一の入口**。retrieval はここ以下に実装し、adapter から OpenAI / R2 を直接呼ばない。
- `src/tribunal/adapters/slack/app.py` — slack_bolt の `App`（HTTP Events モード、署名検証）と `register(app)` で `POST /slack/events` を FastAPI に mount。module import 時に `os.environ[...]` を読むので、**import しただけで Slack の env が必須になる**点に注意。
- `src/tribunal/app_factory.py` — `create_app(platforms)` が合成の中心。platform ごとに adapter を **遅延 import** して mount するので、有効化していない platform の依存・env を要求しない。新しい platform を足すならここに分岐を追加する。
- `src/tribunal/entrypoints/<platform>.py` — uvicorn の起動対象。`.env` 読み込み → `create_app([...])`。`src/tribunal/main.py` は slack entrypoint を re-export する後方互換シム。

Discord は FastAPI に mount できない Gateway（常時 websocket）方式に寄せる方針なので、`app_factory` ではなく独立 entrypoint / 別 service として扱う（対応自体を見送る可能性あり）。

### 目標とする query pipeline（docs §34 / tasks J1）

この順序を崩さない。

```text
Chat Event → Chat Adapter → GameResolver → Thread Context Resolution
  → Standalone Question → Intent Router(rule/strategy/hybrid) → Query Decomposition
  → Retrieval → Rule Adjudicator / Strategy Analyst → Citation → Answer → Chat Adapter
```

### 設計上ぶれさせない前提

- **rulebook 本文を repo に置かない（厳守）。** 個人利用の範囲で複製しているものなので、PDF・page image・**PDF から生成した全文 Markdown** はすべて R2 のみに置く。repo に持つのは metadata だけ。`.gitignore` で `*.pdf` / `*.epub` は弾いているが、変換後 Markdown は拡張子で判別できないので、sync CLI が repo 内に bytes を書き出さない設計にする（arch §4）。`games/` は ignore しない（crawl 結果の保存と catalog を repo に置くため）。
- **SoT は役割で分かれる。** document bytes = R2 / desired catalog = git repo（`documents.yaml` と Markdown の front matter）/ actual state = Vector Store の file attributes。**desired と actual を混ぜない**（`openai_file_id` や同期済み hash を `documents.yaml` に書き戻さない）。Vector Store は R2 から再生成可能な derived index（arch §4）。
- **metadata の置き場所はファイル形式で決まる。** PDF / 画像（metadata を持てない）は repo の `documents.yaml` に宣言、Markdown（持てる）は file 内の YAML front matter。content_type で分けないのは公式 FAQ / errata が PDF で配布されるため（arch §6）。`documents.yaml` は YAML 1.1 の暗黙型変換に注意（`language: no` が `False` になる）→ `safe_load` + JSON Schema で `type: string` を強制する。
- **ingest は sync CLI の reconcile。** desired と actual の diff を取って適用するだけなので冪等。実行漏れ・重複・順序に依存しない（arch §5, tasks D2）。
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

`note.md` はユーザー個人用のファイル。ユーザーの明示的な依頼なしに編集 / 移動 / 削除しないこと。
