# ボードゲームAI 実装タスクリスト

## A. 基盤・リポジトリ

### A1. Pythonプロジェクトの初期構成
- Pythonプロジェクト作成
- package / CLI / test構成
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

---

## B. Game Catalog / GameResolver

### B1. `games.yaml` 実装
- game ID
- name
- aliases
- identifying terms
- edition情報

### B2. `games.yaml` JSON Schema
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
例:

```text
games/
  nusfjord/
    official/
      rulebook/
    strategy/
```

### C2. R2クライアント
- upload
- get
- list
- delete
- metadata取得

R2をSource of Truthとして扱う。

---

## D. Rulebook Ingest / Vector Store

### D1. OpenAI Vector Store基本実装
- Vector Store作成
- File upload
- Vector Storeへのattach
- attributes設定
- status確認
- delete

### D2. R2 Event Notification
構成:

```text
R2
 ↓
Event Notification
 ↓
Cloudflare Queue
```

対象:

- object-create
- object-delete

### D3. Ingest Worker
Queue consumerとして実装。

Create:

```text
R2 object取得
→ OpenAI Files upload
→ Vector Store attach
→ attributes設定
```

Delete:

```text
R2 key
→ Vector Store上の対応file特定
→ detach/delete
```

### D4. Reconciliation / GC
イベント駆動だけでは残り得る不整合を修復する。

- R2にあるがVector Storeにない
- Vector StoreにあるがR2にない
- orphan OpenAI File
- hash差分

`sync` / `gc` コマンドとして実装。

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

を比較。

---

# 推奨実装順

依存関係を考えると、まず以下です。

```text
1. A1 Python project
2. B1/B2 games.yaml
3. C R2
4. D1 OpenAI Vector Store
5. E1 basic RAG
6. F Rule Adjudicator
7. O Rule Eval
8. D2/D3 R2 Event ingest
9. B3 GameResolver
10. H Slack Adapter / thread
11. E2/E3 Retrieval改善
12. K Strategy document
13. L Strategy crawler
14. M Strategy Analyst
15. Discord / Vision / structured statistics
```

特に **Claude / Codexへ渡す単位としては、この `A1`, `B1`, `D3` のような小見出し1つを1タスク** と考えるのがよい。