# ボードゲームAI 実装タスクリスト

> タスクは A〜O の分解、**着手順は以下の Phase** を見る。Phase は「何ができるようになるか」の単位で、
> 各 Phase は完了条件を満たした時点で終わり。Phase をまたいで先に進めない訳ではないが、
> **完了条件を観測してから次へ行く**（特に Phase 2 の eval を飛ばすと以降の改善が測れなくなる）。
>
> Claude / Codex へ渡す単位は、Phase ではなく `A1`, `C3`, `D2` のような**小見出し 1 つ**。

# Phase (機能マイルストーン)

## Phase 0. 疎通 (Sprites + Slack)

**最優先。** RAG より先に、常駐と wake の挙動を実機で確認する。

- Sprite 上で service として起動(`note.md` の runbook)
- public URL + Slack Event Subscriptions
- `app_mention` → 固定応答
- A1 の一部(Sprites 上で起動できる最小構成)

完了条件:

- Slack で mention → 固定応答が thread に返る
- 30 秒放置して warm に落ちたあと、再 mention で wake して応答する
- cold wake でも service が自動再起動し、手動操作が不要

## Phase 1. 1ゲームのルールに答えられる (最小 Rule RAG の縦切り)

精度は後回しで、**R2 → Vector Store → Slack 回答**の経路を一本通す。

- A1 残り(lint / format / type check / test)、A2 ドメインモデル
- B1 / B2 `games.yaml`
- C1 R2 ディレクトリ設計、C3 / C4 `meta.yaml`
- D1 Vector Store
- E1 Responses API + File Search
- H1 Slack mention → `AnswerService.ask()` 接続

この Phase では **game_id はユーザーが明示する**前提でよい(GameResolver は Phase 3)。

**R2 への配置と Vector Store への登録は手作業でよい。** この Phase で扱うのは 1 ゲームの rulebook
数件なので、差分を取る仕組み(C2 / D2)は Phase 5 へ送った。改訂は数年に一度で、人が差し替えれば済む。

完了条件:

- 1 ゲームの rulebook を R2 に置き `meta.yaml` に宣言 → 手動で Vector Store に載せる → Slack でルール質問に出典付きで答える
- 宣言していない R2 object が ingest されない

## Phase 2. 厳密な裁定者になる (品質を測れるようにする)

ここが本題。**先に eval を作る**ことで、以降の改善が「体感」でなく数字になる。

- G1 生 PDF での baseline 評価
- O1 Rule Eval Dataset(20〜50 問)、O2 Retrieval Eval、O3 Adjudication Eval
- F1 Rule Adjudicator Protocol、F2 回答フォーマット

完了条件:

- baseline の数値が出ている
- Adjudicator Protocol の適用前後で差分が測れる
- 誤答を retrieval miss / reasoning miss に切り分けられる

## Phase 3. 会話として使える (Chat UX)

毎回ゲーム名を書かず、thread で追い質問できる状態にする。

- B3 GameResolver
- H2 thread conversation、H3 standalone question 生成
- J1 Query Pipeline、J2 Intent Router

完了条件:

- thread で「じゃあ2人戦だと？」が意図通り解決される
- ゲーム名を書かなくても解決される / 曖昧なら聞き返す
- 過去の Bot 回答がルール根拠として使われていない

## Phase 4. retrieval を改善する

Phase 2 の eval が下支えになっている前提で着手する。

- E2 Explicit Retrieval API、E3 Multi-query Retrieval
- 必要なら G2 page-aware Markdown

完了条件:

- retrieved chunk と score をアプリ側で確認できる
- O2 / O3 の数値が baseline から改善している

## Phase 5. Strategy に答えられる

Rule と混ざらないことを保ちながら、別系統として足す。

crawl で件数が増え、**人が把握しきれなくなる**のがこの Phase。差分を取る仕組みが必要になるのはここから。

- C2 R2 クライアント、D2 sync CLI(Phase 1 から移動)
- K1〜K3 Strategy document / schema / R2 構造
- L1〜L3 crawler
- M1 Strategy 専用 Vector Store、M2 Strategy Analyst Protocol、M3 Hybrid Query
- N1 / N2 ゲーム別拡張
- D4 GC / 整合性チェック(宣言漏れを人がたまに検査する)

完了条件:

- 戦略質問に前提 / 評価軸 / 複数候補 / trade-off を明示して答える
- Rule 回答に community / personal の情報がルール根拠として混入しない
- `sync` を 2 回連続で実行しても差分が出ない(冪等の確認)

## Phase X. 必要になったらやる

不便になるまで着手しない。

- D3 R2 event driven ingest(R2 直置き運用が欲しくなったら)
- I1 / I2 Discord
- G3 Vision preprocessing、N3 structured play data
- O4 モデル比較(Retrieval / Protocol / Context を改善した後で)

---

# タスク分解

## A. 基盤・リポジトリ

### A1. Pythonプロジェクトの初期構成
- Pythonプロジェクト作成
- ディレクトリ構成(arch §38)の骨組みを作る
- CLI / test 構成
- lint / format / type check
- 設定・secret管理方針
- Sprites上で起動できる最小構成

### A2. ドメインモデル整理
最低限以下をコード上の型として定義する。

- Game
- Document
- Question
- Answer
- Source / Citation
- ContentType
  - rulebook
  - errata
  - faq
  - strategy
  - card_guide
  - play_log

### A3. パッケージ名の確定と rename ✅
プロダクト名 = **tribunal**(arch §38)。package / repo / Sprite すべて`tribunal`に統一済み。

- `src/tribunal/`、`pyproject.toml`、全import、起動対象`tribunal.entrypoints.slack:app`
- `README.md`、`CLAUDE.md`、`docs/sprites.md`、`note.md`のrunbook
- repo: `github.com/Sho2010/tribunal`

Sprite はまだ作成していないので、`note.md` の runbook 通り`sprite create tribunal`から始める(`.sprite`は`sprite use`が書き換える)。

---

## B. Game Catalog / GameResolver

### B1. `games.yaml` 実装
- game ID
- name
- aliases
- identifying terms
- edition情報

### B2. `games.yaml` JSON Schema
**pending**
- schema validation
- duplicate/default edition等の追加validation

### B3. GameResolver
入力:

```text
question
thread context
games.yaml
```

出力:

```text
Resolved(game_id)
Ambiguous(candidates)
Unknown
```

判定優先順位:

1. threadから既知のgame_id
2. game name / alias
3. identifying terms
4. LLMによる推定
5. 不明ならユーザーへ確認

---

## C. R2 Storage

### C1. R2ディレクトリ設計
**done** — arch §6 に記載。

```text
games/<game_id>/{rule,strategy,raw}/
```

各区分の意味・下位はフラット / 命名自由・pathの区分と`meta.yaml`のmetadataが別物である理由は arch §6 を見る。

bytes はローカルには置くが**push しない**。`.gitignore` が 3 区分ごと落とす(arch §4, 厳守)。

### C2. R2クライアント
**pending (Phase 5)** — R2 を読むのは sync CLI(D2)だけで、その D2 が Phase 5 送りのため呼び出し側がいない。
Phase 1 の範囲(rulebook 数件)は手作業で配置する。

- upload
- get
- list (ETag取得含む)
- delete

R2をdocument bytesのSource of Truthとして扱う。

### C3. document catalog (`games/<game_id>/meta.yaml`)
desired state。**game 1つにつき1ファイル**で、そのgameのディレクトリ直下に置く。PDF / 画像のmetadataを宣言する。Markdownはfile内のYAML front matterに持つので書かない(arch §6)。

```yaml
# games/nusfjord/meta.yaml
version: 1
game_id: nusfjord

documents:
  - path: rule/rulebook-ja.pdf
    content_type: rulebook
    authority: official
    language: ja
    edition: bigbox
```

`path`は`meta.yaml`からの相対。R2 keyは`games/<game_id>/` + `path`で組み立てる。
`game_id`はディレクトリ名から導出せず中に明記する。`openai_file_id`やhashのような観測結果は書かない(desiredとactualを混ぜない)。

### C4. document catalog の JSON Schema
- schema validation
- `language`は`enum: [ja, en]`。typo(`jp` / `eng`)も弾く
- `edition`はoptional(FAQ / errataは版に紐づかない)
- ディレクトリ名と`game_id`の一致を検査する
- 宣言したファイルが実在しないケースの検出、`path`重複の検出

---

## D. Rulebook Ingest / Vector Store

### D1. OpenAI Vector Store基本実装
- Vector Store作成
- File upload
- Vector Storeへのattach
- attributes設定
- status確認
- delete

### D2. sync CLI(ingest主経路)
**pending (Phase 5)** — 差分方式が効くのは、件数が増えて人が把握しきれなくなってから。
Phase 1 の範囲(rulebook 数件 / 改訂は数年に一度)では手作業で足りる。crawl を始める Phase 5 で作る。

`meta.yaml` + Markdown front matter(desired)とVector Store(actual)のdiffを取って適用する。冪等。

```text
desiredにあってactualに無い     → Files upload + attach + attributes設定
actualにあってdesiredに無い     → detach / delete
両方にあるがR2のETagが違う      → 再upload
```

ローカル実行、またはmerge時にCIで実行する。

### D3. R2 Event Driven Ingest(保留)
v1では実装しない(arch §5)。catalogがgit上にあるため、この経路が担当できるのは「R2へ直接置いた場合の自動取り込み」だけで、人の手間はsync CLIと変わらない。

必要になった段階で追加する:

```text
R2 object create/delete → Event Notification → Cloudflare Queue → Worker
```

### D4. GC / 整合性チェック
**pending (Phase 5)。人がたまに手で流す**もので、自動実行やCIには載せない。
宣言漏れは Phase 1 の規模なら bot が答えないことで気づくが、crawl で件数が増えると取りこぼす。

D2のreconcileで拾えない残骸を掃除する。

- orphan OpenAI File(どのVector Storeからも参照されていない)
- R2にあるがmeta.yamlにもfront matterにも宣言が無い(=ingestされない)object。**`raw/`は宣言しない前提なので除外する**
- meta.yamlが指すpathがR2に存在しない

`gc` / `doctor` コマンドとして実装。

---

## E. Rule Retrieval

### E1. Responses API + File Search
最小のRule RAGを実装。

```text
Question
→ game_id filter
→ rulebook / faq / errata
→ Answer
```

### E2. Explicit Retrieval API
File Search任せではなく、検索結果をアプリ側で取得できるようにする。

目的:

- retrieval結果のdebug
- score確認
- multi-query
- reranking
- retrieval miss / reasoning miss の切り分け

### E3. Multi-query Retrieval
質問から複数の検索観点を生成する。

例:

```text
対象アクション
関連コンポーネント
setup
player count
exceptions
examples
```

---

## F. Rule Adjudicator

### F1. Rule Adjudicator Protocol
現在効果が確認できている裁定プロトコルを正式化する。

必須確認:

- 基本ルール
- 用語定義
- setup
- player count差
- 例外
- examples
- 関連する別section

禁止:

- 一つの記述から即座に一般化
- 例示をルールとして扱う
- 推測を公式ルールとして断定

### F2. 回答フォーマット
基本:

```text
結論
根拠となるルール
解釈
引用
```

原則日本語。

可能なら:

- source filename
- page
- 原文引用

を付ける。

---

## G. PDF Preprocessing

### G1. 生PDFでのbaseline評価
まず前処理なしで精度測定。

### G2. PDF → page-aware Markdown
必要になった場合:

```text
PDF
→ page単位抽出
→ Markdown
→ page metadata保持
→ Vector Store
```

### G3. Vision preprocessing
図・アイコン・セットアップ図を解析。

```text
PDF page image
→ Vision
→ structured Markdown
```

後回しでよい。

---

## H. Slack Adapter

### H1. Slack App基本実装
- mention
- slash command
- request verification
- 3秒以内ACK
- async処理

### H2. Thread conversation
Slack threadをconversation単位として利用。

```text
thread_ts = conversation_id
```

- bot回答はthreadへ返す
- thread履歴取得
- follow-up質問に対応

### H3. Standalone Question生成
thread履歴:

```text
Q1
A1
Q2: 「じゃあ2人戦だと？」
```

から、

```text
「ヌースフィヨルドの○○について、2人戦ではどうなるか？」
```

へ変換。

過去Bot回答は質問解決のcontextには使うが、**ルール根拠として使用しない**。

---

## I. Discord Adapter

### I1. Slash command
HTTP Interactionベースで実装。

### I2. Mention / Gateway
必要になった段階で常駐Gateway connectionを追加。

Slack/Discord固有処理はApplication層から分離する。

---

## J. Query Orchestration

### J1. Query Pipeline
最終的に以下の順序を固定する。

```text
Chat message
 ↓
GameResolver
 ↓
Standalone Question
 ↓
Intent classification
 ↓
Retrieval
 ↓
Rule / Strategy processor
 ↓
Answer
 ↓
Chat Adapter
```

### J2. Intent Router

最低限:

```text
rule
strategy
hybrid
```

---

## K. Strategy Corpus

### K1. Strategy Document Schema
Markdownはfile内にmetadataを持つ形式なので、front matterがmetadataの唯一の置き場所になる(arch §6)。`meta.yaml`には書かない。crawlerが生成するファイルも必ずfront matterを持つ。

基本:

```text
1 document = 1 Markdown
               +
             YAML front matter
```

front matter候補:

```yaml
schema_version:
game_id:
content_type:
authority:
title:
author:
source_id:
source_url:
source_type:
published_at:
retrieved_at:
edition:
player_counts:
topics:
cards:
```

### K2. Strategy JSON Schema
YAML front matterをvalidationするSchemaを作る。

### K3. Strategy R2構造
rule corpusとは論理的に分離する。

```text
games/<game>/strategy/
```

---

## L. Strategy Crawler

### L1. Crawler共通interface
各crawlerの出力を、

```text
Raw source
→ Normalizer
→ Markdown + YAML front matter
→ R2
```

に統一する。

### L2. 最初のstrategy sourceを決定
無差別crawlerではなく、信頼できるソースを少数選ぶ。

候補:

- BGG
- strategy wiki
- Reddit
- blog
- personal notes

### L3. Source-specific crawler
ソースごとに別タスクとして実装する。

例:

```text
BGG crawler
Reddit crawler
specific blog crawler
```

---

## M. Strategy Retrieval / Analyst

### M1. Strategy専用Vector Store
Rule Storeと分離する。

```text
official-rules
strategy
```

### M2. Strategy Analyst Protocol
Rule Adjudicatorとは別プロトコル。

例:

1. game state整理
2. 正確なルール・カード能力確認
3. strategy knowledge検索
4. 候補手生成
5. synergy / opportunity cost / risk比較
6. 条件付き推奨

### M3. Hybrid Query
例:

```text
「このカードコンボ強い？」
```

の場合、

```text
Rule Store
→ interaction確認

Strategy Store
→ 評価・定石検索

Strategy Analyst
→ 統合
```

---

## N. ゲーム別Strategy拡張

### N1. Dominion Strategy
Supplyを入力として、

- card text
- trash
- draw
- actions
- payload
- gain
- attack / defense
- synergy

を分析する。

### N2. Agricola Strategy
- draft pick
- card evaluation
- player count
- combo
- food engine
- opportunity cost

を分析。

### N3. Structured Play Data
将来的に文章RAGとは別に、

```text
pick rate
win rate
card combinations
player count
ranking
```

などの統計データを扱う仕組みを検討。

---

## O. Eval / Quality

### O1. Rule Eval Dataset
まず20〜50問。

各ケース:

```yaml
question:
expected:
required_evidence:
traps:
```

特に:

- setupとゲーム中ruleの混同
- 資源支払いと配置の混同
- 例示からの誤一般化
- exception見落とし
- 複数page横断

### O2. Retrieval Eval
- 正しいsectionが検索できたか
- ranking
- irrelevant chunk

### O3. Adjudication Eval
正しいcontextを与えた状態で裁定できたか。

### O4. Model比較
同じevalで、

```text
Terra
Sol
reasoning effort差
```

※ Terra / Sol は OpenAI ChatGPT 5.6 世代のモデル名。

を比較。
