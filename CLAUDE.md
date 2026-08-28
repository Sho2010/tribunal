# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 何のプロジェクトか

**tribunal** — Slack（将来的に Discord）からボードゲームのルール / 戦略を質問できる RAG chatbot。Python 3.11+ / FastAPI + slack_bolt、パッケージ管理は `uv`。実行環境は Fly.io Sprites。

ゴールは「ルールブック検索 bot」ではなく、**Rule については厳密な裁定者、Strategy については根拠を持った分析者**として振る舞うこと。

コードは **Phase 0（Sprites + Slack 疎通）** の段階: `app_mention` を受けて固定文字列を返すだけ。retrieval / ingest / R2 / `games/` の読み込みはすべて未実装。着手順は `docs/tasks.md` 先頭の Phase を見る。

## コマンド

```bash
uv sync --group dev                                              # 依存同期（dev ツール込み）
uv run uvicorn tribunal.entrypoints.slack:app --port 8080 --reload    # ローカル起動（.env を読む）
curl localhost:8080/                                             # health: {"status":"ok","platforms":["slack"]}
```

lint / format / type check / test（CI で回るのと同じ 4 つ）:

```bash
uv run ruff check .          # lint（--fix で自動修正）
uv run ruff format --check . # format 確認（--check を外すと整形）
uv run mypy                  # type check（strict。対象は pyproject の files=）
uv run pytest                # test
```

- 環境変数は `.env.example` を `.env` にコピーして設定（`SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`）。`.env` の読み込みは entrypoint（`src/tribunal/entrypoints/slack.py`）が行う。
- dev 依存は `[dependency-groups]` の `dev`（uv のネイティブな置き場所。`[project.optional-dependencies]` ではない）。
- mypy は `strict`。型スタブを同梱しない `slack_bolt` / `slack_sdk` だけ module 単位で `ignore_missing_imports` を許容している（全体を緩めない）。
- ruff は `E` / `F` / `I` / `UP` / `B` に加えて **相対 import 禁止（`TID252`）**。レイヤの依存方向を import 文から追える状態を保つため。line-length は 100。
- CI は `.github/workflows/ci.yml`。**Python 3.11**（`requires-python` の下限）で上記 4 つを実行する。

## 開発の進め方

### 小さく作る

**タスクは動く最小単位まで割る。** `docs/tasks.md` の小見出しですら大きいことがあるので、
その場合はさらに割る。目安:

- **1 PR は「1 つのことができるようになる」まで。** 先回りして周辺を整えない
- **動くものを先に出す。** 抽象化・拡張性・将来の分岐は、2 つ目の使い道が出てから
- 設計判断が要る大きさになったら、それは割り方が粗いサイン。**手を動かす前に議論する**

**`docs/tasks.md` は着手順の参考であって、そのままの粒度で実装する契約ではない。**

**`docs/tasks.md` の小見出し 1 つ（`A1`, `C3`, `D2`）= 1 ブランチ = 1 worktree = 1 セッション。**

- worktree は `claude --worktree <task-id>-<slug>` で作る。本体ツリーへの書き込みが機械的にブロックされる
- **worktree 内では commit / push を確認なしで行ってよい。PR を立てるまで confirm 少なめで進める。** マージは PR 経由（ユーザーが review する）
- **本体ツリー（main の作業ツリー）では commit しない。** worktree 内のファイルだけを触る（本体の読み取りは可）
- **PR 本文に「なぜそうしたか」を書かない。** 書くのは「何を変更したか / 何ができるようになったか / 注意が必要な点 / 読むのに前提が要る点」の 4 つだけ。設計判断の理由は arch doc 側。**タスク識別子（`A1` / `B1` …）は本文に書かない**（branch 名と title にある）。型は repo 直下の `pr-template.md`

### タスク識別子で会話しない（厳守）

**ユーザーとの議論・説明・提案では `A1` / `C3` / `D2` のような `docs/tasks.md` の識別子を使わない。**
ユーザーは番号を覚えていないので、識別子だけ言われても何の話か分からない。

- ✅ 「Vector Store の sync CLI（desired と actual の diff を取って適用するやつ）をやりますか」
- ❌ 「次は D2 をやりますか」
- ❌ 「D2（sync CLI）をやりますか」— 括弧で補っても識別子を先に出さない

識別子を書いてよいのは、**人間向けの散文ではない場所**だけ:
branch 名（`d2-sync-cli`）、PR title、`docs/tasks.md` 自身。
これらに触れる必要があるときも、会話文では「sync CLI のブランチ」のように内容で呼ぶ。

ユーザーが `D2` のように識別子で指してきた場合は、**こちらの返答では内容に開いて答える**
（「sync CLI ですね。〜」）。

### コメント / docstring

**PR 本文と同じ基準。コード内に「なぜこう設計したか」を書かない。** 設計の理由は arch doc にあり、
コード側に写すと二重管理になって片方が腐る。

- **docstring は 1 行。** 何をする関数かだけ。名前と型注釈で分かるなら書かない
- 複数段落の docstring を書かない。**背景 / 検討経緯 / 「〜のため」はすべて削る**
- コードを言い換えただけのコメントは書かない
- ソースに残すのは、**コードを読んでも分からない外部制約**だけ。
  外部 API の非自明な挙動（「`App()` は生成時に `auth.test` を叩く」）、仕様上の制約、ドメイン知識。
  「なぜこう書いたか」ではなく「**そう書かないと何が起きるか**」の形にする
- **doc へのポインタも書かない**（`arch doc「〜」参照`）。理由を書かないのだから参照も要らない。
  下の「成果物に doc への参照を書かない」を見る

それ以外の「ここはこう考えた」の類はソースに入れない。**PR の該当行コメントで伝える**
（運用の詳細は未確定）。

## ドキュメント

1. **`docs/Board Game AI - Architecture Context and Design Decisions.md`** — 設計判断とその理由。現時点の合意はこれを見る（下の「設計 doc は書き換える前提」も読む）。
2. **`docs/tasks.md`** — 先頭の **Phase（機能マイルストーン）が着手順で、各 Phase に完了条件がある**。その下の A〜O がタスク分解。**小見出し 1 つ（`A1`, `C3`, `D2` など）を 1 タスクの単位**として扱う。次に何をやるかはここを見る。
3. **`note.md`** — 初回デプロイ runbook（Sprites）。
4. **`pr-template.md`**（repo 直下）— PR 本文の型。
5. **`docs/context.md`** — Rule 回答の元プロンプト（実験で効果が確認できたもの）。Rule Adjudicator Protocol を実装するときはこの原文を正とする。

初期の実装指示書 `plan.md` (`docs/first-plan.md`) は、現行方針と矛盾する記述で誤判断を招くため削除した（git 履歴に残る。まだ有効だった細目は arch doc の「付録: 初期案から引き継いだ細目」に移設済み）。

### 成果物に doc への参照を書かない（厳守）

**成果物は自己完結させる。** 対象は**あらゆる成果物**——コード / コメント / docstring / 設定ファイル /
commit message / PR title / PR 本文 / `docs/tasks.md` / 新しく書く doc / ユーザーへの説明文。

#### 節番号は書かない

**`§4` / `arch §38` のような節番号での参照をどこにも書かない。** 節は追加・削除・並べ替えで番号が
ずれるが、参照側は一緒に動かないので黙って別の節を指すようになる。番号は読み手にとっても中身の
手がかりにならない。

#### arch doc への参照そのものを既定で書かない

節名に書き換えれば OK という話ではない。**arch doc へのポインタを成果物に残さない。**
`arch doc「〜」を見る` と書いた時点で、読み手は別ファイルを開かないと意味が取れず、
doc 側が変わると参照が腐る。

書きたくなったら、次のどちらかにする。

1. **参照ごと消す** — 既定はこれ。理由が要らない場所（コード / 設定ファイルのコメント）は特にそう。
   「なぜこう設計したか」をコードに書かない方針と同じ
2. **その場で完結する 1 行に書き下す** — 読み手に必要な事実だけを、doc を開かずに済む形で書く

- ✅ `# key は games/ を含める。ローカルのツリーと R2 の姿を一致させる`
- ✅ `bytes はローカルには置くが push しない。.gitignore が 3 区分ごと落とす（厳守）`
- ❌ `# key は games/ を含める（arch doc「R2をSource of Truthとする」）`
- ❌ `詳細は arch doc「ファイル構造とmetadataの持ち場所」を見る`
- ❌ `arch §6 参照`

例外は **arch doc 自身の中での自己参照**だけ（同一ファイル内なので開き直す必要がない）。
この場合も番号ではなく節名で書く: `（「Rule corpusとStrategy corpus」）`。

なお arch doc の見出しに付いている番号（`# 4. R2をSource of Truthとする`）は目次として残してよい。
消すのは**他所から番号で指す**ことのほう。

#### 会話でも同じ

ユーザーへの説明で `§6` や `arch doc の「〜」節にある通り` と言わない。**内容を直接言う**
（タスク識別子で会話しないのと同じ理由——ユーザーは節番号も節名も覚えていない）。

### 設計 doc は書き換える前提（重要）

**arch doc は作業を進めるための足場であって、守るべき制約ではない。** 手を動かして実情が見えた結果
「こっちのほうがいい」となったら、**doc のほうを変える**。実装を doc に合わせて捻じ曲げない。

書かれている内容は、多くが**手を動かす前に想像で決めたもの**。実際にファイルを並べてみる / 使う人の動きを
追う段階で前提が変わるのは正常で、そのとき doc が古くなるのは織り込み済み。

- **doc に書いてあることを理由に「できません」と言わない。** 良い案なら提案する。
  「arch doc にこう書いてあるので」は、**議論を止める根拠にはならない**
- 実装と doc がズレたら、**doc を直すのが既定**。ズレたまま放置しない
- ただし**黙って変えない**。「実情に合わないので arch doc のこの節をこう変えたい」と言ってから変える
- 変えたら理由も doc に残す。次に読む人（Claude 含む）が同じ議論を蒸し返さないため

下の「採らない案」も同じ。**却下の理由が今も成立するか**を見て、崩れているなら再提案してよい。
禁止リストではなく「一度潰れているので、蒸し返すなら理由を確認してから」という意味。

### 一度却下された案

検討して却下された判断。理由付きで潰れているので、**再提案する前に arch doc の該当節を読み、
却下の理由が今も成立するか確認する**。成立しているなら蒸し返さない。崩れているなら提案してよい。

- **SQLite を knowledge catalog にしない。** 同じ情報を複数箇所で mutable に持つ不整合を避けるため。会話履歴 DB も持たない（Slack thread から取得）。
- **R2 の path から metadata を導出しない。** path を metadata schema にすると typo が silently 通り、次元を足すと全 path の move + 再 ingest になる。しかも player_count / edition / 多言語は階層に収まらないので機構が 2 つに増える。path は locator。ただし **`rule` / `strategy` / `raw` の 3 区分は人が整理するために置く**（機械が参照するのは `meta.yaml` の宣言だけ）。
- **単一 Vector Store + attributes で済ませない。** Rule / Strategy Store を分離する。理由は検索性能ではなく trust boundary。
- **event driven ingest（R2 Event → Cloudflare Queue → Worker）を v1 で作らない。** catalog が git 上にあるので、この経路が担当できるのは「R2 へ直接置いた場合の自動取り込み」だけで、人の手間は sync CLI と変わらない（tasks D3 は保留）。
- **File Search の結果からそのまま回答させない。** query decomposition → multi-query retrieval → Rule Adjudicator。
- **retrieval を「Vector Store なし・直接 file input」で始めない。** 一度検討したが破棄（file_id を SQLite で管理する前提だったため）。Vector Store + File Search で進める（tasks D1/E1/M1）。

## アーキテクチャ

レイヤの依存方向は **entrypoints → adapters → application → domain** の一方向。全体のディレクトリ構成は下記（現状はこの一部だけが存在する）。

```text
games/                # games.yaml, schema/, <game_id>/{meta.yaml, rule/, strategy/, raw/}
evals/                # promptfooconfig.yaml, cases/, provider.py
src/tribunal/
  entrypoints/        # uvicorn 起動対象
  adapters/           # inbound: chat platform
  application/        # answer_service.py, ports.py, pipeline/, rule/, strategy/
  domain/
  infra/              # outbound: openai/, r2/
  knowledge/          # meta.yaml 読み込み / front matter / reconcile
  cli/
```

命名で守ること:

- **`adapters/` は inbound（呼ばれる側）専用。** OpenAI / R2 のような outbound client は `infra/` に置く。両方を adapters に入れると依存方向が逆のものが同居する。
- **`adapters/` `application/` から `knowledge/` を import しない。** ingest は手元 / CI で走り、Sprite 上の bot は R2 も `games/` も触らない。逆向き（`cli/` → `knowledge/` → `infra/`）は正常。
- **port を切るのは retrieval だけ**（E1 の `file_search` → E2 の Retrieval API で実装が 2 つになるため）。他は必要になるまで Protocol を作らない。
- **protocol prompt は `.md` ファイル**として使う側にコロケートし（`application/rule/prompts/adjudicator.md`）、コード内の文字列リテラルにしない。eval で前後比較する対象なので diff が見えることが要件。
- **`games/` と `evals/` は `src/` の外**。人が宣言・レビューするデータでコードではない。
- **eval runner を自作しない。** promptfoo を使い、`evals/promptfooconfig.yaml` と Python provider
  （`AnswerService` を叩くだけの薄いもの）を置く。promptfoo は npm パッケージなので bot の実行環境には入らない。

現在あるモジュール:

- `src/tribunal/domain/` — chat platform 非依存の値オブジェクト（`Answer`, `Source`）。
- `src/tribunal/application/answer_service.py` — `AnswerService.ask(question, game_id=None) -> Answer`。**Chat adapter が触ってよい唯一の入口**。retrieval はここ以下に実装し、adapter から OpenAI / R2 を直接呼ばない。
- `src/tribunal/application/rule/` `src/tribunal/application/strategy/` — protocol prompt の置き場所。`protocol.py` の `adjudicator_prompt()` / `analyst_prompt()` が同階層の `prompts/*.md` を読む。**Rule Adjudicator を拡張して Strategy を兼ねさせない**。呼び分け（Intent Router）は未実装で、現在 mount されるのは Rule 側だけ。
- `src/tribunal/infra/openai/file_search_retriever.py` — `FileSearchRetriever`。store 非依存で、`for_rule()` / `for_strategy()` が読む env（`TRIBUNAL_RULE_VECTOR_STORE_ID` / `TRIBUNAL_STRATEGY_VECTOR_STORE_ID`）と注入する prompt だけが違う。**片方が未設定のとき他方へ fallback しない**（trust boundary のため）。
- `src/tribunal/adapters/slack/app.py` — slack_bolt の `App`（HTTP Events モード、署名検証）と `register(app)` で `POST /slack/events` を FastAPI に mount。`os.environ[...]` を読むのは **`register()` の中だけ**（module import 時ではない）。import しただけで Slack の env が必須になると test も他 platform も巻き添えになるため。`create_app(..., verify_credentials=False)` で起動時の `auth.test`（slack_bolt が既定で叩く token 検証）を止められる。test 専用のフックで、本番は既定の `True`。
- `src/tribunal/app_factory.py` — `create_app(platforms)` が合成の中心。platform ごとに adapter を **遅延 import** して mount するので、有効化していない platform の依存・env を要求しない。新しい platform を足すならここに分岐を追加する。
- `src/tribunal/entrypoints/<platform>.py` — uvicorn の起動対象。`.env` 読み込み → `create_app([...])`。`src/tribunal/main.py` は slack entrypoint を re-export する後方互換シム。

Discord は FastAPI に mount できない Gateway（常時 websocket）方式に寄せる方針なので、`app_factory` ではなく独立 entrypoint / 別 service として扱う（対応自体を見送る可能性あり）。

### 目標とする query pipeline（tasks J1）

この順序を崩さない。

```text
Chat Event → Chat Adapter → GameResolver → Thread Context Resolution
  → Standalone Question → Intent Router(rule/strategy/ambiguous) → Query Decomposition
  → Retrieval → Rule Adjudicator / Strategy Analyst → Citation → Answer → Chat Adapter
```

### 設計上ぶれさせない前提

- **他人の著作物を push しない（厳守）。** 守るのは「GitHub に上げないこと」であって、**ローカルの作業ツリーに実体があるのは正常**（R2 へ upload する元が要る）。`games/<game_id>/` に metadata と bytes が同居し、`.gitignore` が `rule/` `strategy/` `raw/` を落とす。拡張子ではなく置き場所で無視するのは、変換後 Markdown や crawl 結果が拡張子で判別できないため。
- **SoT は役割で分かれる。** document bytes = R2 / desired catalog = git repo（`games/<game_id>/meta.yaml` と Markdown の front matter）/ actual state = Vector Store の file attributes。**desired と actual を混ぜない**（`openai_file_id` や同期済み hash を `meta.yaml` に書き戻さない）。Vector Store は R2 から再生成可能な derived index。
- **metadata の置き場所はファイル形式で決まる。** PDF / 画像（metadata を持てない）は `meta.yaml` に宣言、Markdown（持てる）は file 内の YAML front matter。content_type で分けないのは公式 FAQ / errata が PDF で配布されるため。
- **ingest は sync CLI の reconcile。** desired と actual の diff を取って適用するだけなので冪等。実行漏れ・重複・順序に依存しない（tasks D2）。
- **Rule と Strategy を混ぜない。** Rule 回答に community / personal の情報をルール根拠として混ぜない。Rule を Strategy corpus から推測しない。
- **検索結果 1 件で即答させない。** Rule 回答では **Rule Adjudicator Protocol** を prompt として明示するのが必須: 基本ルール / 用語定義 / setup / player count 差 / 例外 / examples / 関連 section を横断確認し、example を一般ルール化しない・推測を公式ルールとして断定しない。回答形式は【ルール引用】→【分析・検討】→【結論】の順で、**結論を先に書かせない**。原則日本語。
- Strategy は唯一解がないので、Rule Adjudicator を拡張せず別の **Strategy Analyst Protocol**（前提 / 評価軸 / 複数候補 / trade-off を明示）を使う。
- Slack thread を conversation 単位（`thread_ts` = conversation_id）とし、thread 履歴から standalone question を生成して毎回再検索する。**過去の bot 回答は context には使うがルール根拠にはしない**（誤答の連鎖を防ぐ）。
- retrieval / reasoning の切り分けが debug できる構造にする（Responses API の `file_search` 任せにせず、Retrieval API を明示的に挟める形）。モデルを上げる前に Retrieval / Protocol / Context を改善し、同一 eval で比較する。

## Sprites でのデプロイ

手順は `note.md`。落とし穴だけ:

- **ディスクは自動永続、RAM / プロセスは pause で消える。** 常駐プロセスは `exec` の foreground 起動ではなく **service 化**する（cold wake 時に自動再起動される）。checkpoint はディスク永続のためには不要。
- HTTP port を持てる service は **1 つだけ**（8080 を bot が確保）。
- `sprite-env services ...` は Sprite 内部コマンド。ローカルからは `sprite exec -- sprite-env services ...`、または sprites MCP の `service_create` / `service_start` を使う。
- ログ: `sprite exec -- tail -n 50 /.sprite/logs/services/slackbot.log`
- Slack は 3 秒 ACK。wake レイテンシ（warm 100–500ms / cold 1–2s）があるので、重い処理を入れる段階では slack_bolt の lazy listener で即 ack する。
- secret は Sprite のスナップショットに残る（専用 vault なし）。この割り切りは既に合意済み。

`note.md` はユーザー個人用のファイル。ユーザーの明示的な依頼なしに編集 / 移動 / 削除しないこと。
