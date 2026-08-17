# Board Game AI Chatbot - 実装指示書

## 1. 目的

Slack / Discord から、ボードゲームに関する以下の質問へ回答できる AI chatbot を実装する。

* 公式ルール
* FAQ / Errata
* カードの効果
* 定石・戦略
* カードの評価や使い方
* 独自に追加したプレイ知見

ルールや戦略情報は事前に登録し、OpenAI Vector Store を利用した RAG で回答する。

---

## 2. 基本アーキテクチャ

```text
Slack / Discord
      │
      ▼
Chat Adapter
      │
      ▼
Application / Query Service
      │
      ├── SQLite
      │     └── game / document catalog
      │
      └── OpenAI Responses API
             └── Vector Store / File Search

Knowledge Ingest
      │
      ├── Source files
      │     └── R2
      │
      ├── SQLite metadata
      │
      └── OpenAI Vector Store
```

実行環境には **Fly.io Sprites** を利用する。

Sprite 内には以下を配置する。

```text
Sprite
├── chatbot application
├── ingest / knowledge management application
└── SQLite
```

原本ファイルは R2 に保存する。

---

# 3. コンポーネント分割

Chat との通信部分と Knowledge / RAG 部分を分離する。

## 3.1 Chat Adapter

責務:

* Slack / Discord からイベントを受信
* slash command の処理
* mention の処理
* platform 固有データを内部形式へ変換
* Application Service を呼び出す
* 回答を Slack / Discord 形式へ変換して返却

Chat Adapter は RAG の実装詳細を知らないこと。

例:

```python
class ChatMessage:
    platform: str
    channel_id: str
    user_id: str
    text: str
    thread_id: str | None
```

Adapter:

```text
SlackAdapter
DiscordAdapter
```

内部処理は可能な限り共通化する。

---

## 3.2 Application / Query Service

Chat platform に依存しない問い合わせ処理。

責務:

1. 対象ゲームを特定
2. 質問を分類
3. retrieval 条件を決定
4. Vector Store を検索
5. LLM に回答生成させる
6. citation / source を返す

インターフェース例:

```python
answer = query_service.ask(
    game_id="nusfjord",
    question="2人戦で序盤に1株だけ買うのは強い？",
)
```

戻り値例:

```python
class Answer:
    text: str
    sources: list[Source]
```

Chat Adapter はこの API のみ利用する。

---

# 4. Knowledge / Ingest

Chat処理とは独立した実装にする。

例えば CLI として実装する。

```bash
boardgame-ai game add ...
boardgame-ai ingest ...
boardgame-ai document list ...
boardgame-ai document delete ...
```

将来的には管理API/UIへ変更可能な構造にする。

---

# 5. データ保存

## 5.1 R2

Source of Truth として利用。

```text
games/
  nusfjord/
    rulebook/
      rulebook-ja.pdf

    faq/
      faq-ja.md

    strategy/
      shares.md
      cards.md
```

OpenAI 上のファイルを原本として扱わない。

---

## 5.2 SQLite

Knowledge catalog を管理する。

最低限以下を持つ。

### games

```text
id
name
aliases
created_at
updated_at
```

例:

```text
nusfjord
Nusfjord
["ヌースフィヨルド"]
```

### documents

```text
id
game_id
content_type
authority
edition
language
player_count
source_uri
openai_file_id
status
created_at
updated_at
```

`source_uri` は R2 上の原本を指す。

---

# 6. Knowledge Type

最低限以下を区別する。

```text
rulebook
errata
faq
strategy
card_guide
play_log
```

また情報の信頼レベルを持つ。

```text
official
publisher
community
personal
```

例:

```yaml
game_id: nusfjord
content_type: strategy
authority: personal
edition: bigbox
language: ja
player_count: 2
```

---

# 7. OpenAI Vector Store

初期実装では **単一 Vector Store** を利用する。

ゲームや情報種別は File Attributes で区別する。

例:

```yaml
game_id: nusfjord
content_type: rulebook
authority: official
edition: bigbox
language: ja
```

検索時には最低限 `game_id` を filter する。

---

# 8. Retrieval 方針

ルールと戦略情報を同一の情報として扱わない。

## ルール質問

例:

```text
このカードを使ったあと魚は何匹払う？
```

優先対象:

```text
rulebook
errata
faq
```

原則として strategy / play_log はルール根拠に使用しない。

---

## 戦略質問

例:

```text
2人戦で序盤に株を買うのは強い？
```

対象:

```text
strategy
card_guide
play_log
```

必要に応じてルール情報も参照する。

LLMへの指示でも、

```text
公式ルール
```

と

```text
戦略上の評価・意見
```

を明確に区別して回答させる。

---

# 9. Metadata

初期段階では過度に構造化しない。

必須候補:

```text
game_id
content_type
authority
edition
language
```

必要になった段階で追加:

```text
player_count
expansion
```

以下は基本的に semantic search に任せる。

```text
cards
topics
mechanics
```

---

# 10. PDF / 画像

初期実装:

```text
PDF
 ↓
OpenAI Vector Store
```

でよい。

ただしボードゲームでは、

* アイコン
* コンポーネント配置
* セットアップ図
* フローチャート

が重要なため、将来的に ingest pipeline を拡張できるようにする。

想定:

```text
PDF
 ├── text
 │
 └── page image
        ↓
     Vision
        ↓
structured markdown
        ↓
Vector Store
```

ページ番号は可能な限り保持する。

将来的に、

```text
Vector Search
     ↓
page 7 hit
     ↓
R2から該当ページ画像取得
     ↓
Visionで再確認
```

という fallback を追加可能にする。

---

# 11. Chat UX

問い合わせ時にゲームを明示できるようにする。

例:

```text
/game nusfjord 株を1枚だけ買うのって強い？
```

mention:

```text
@boardgame-ai nusfjordで株を買った時の配当ルール教えて
```

将来的には channel / thread 単位で game context を保持してもよい。

ただし初期実装では、暗黙的な状態管理を増やしすぎない。

---

# 12. Slack / Discord

Adapter として独立させる。

```text
adapters/
  slack/
  discord/
```

Slack:

```text
slash command
mention
```

Discord:

```text
slash command
mention
```

Discord Gateway が必要になる場合でも、Knowledge / Application 層には影響させない。

---

# 13. 推奨コード構成

```text
src/
├── adapters/
│   ├── slack/
│   └── discord/
│
├── application/
│   └── query_service.py
│
├── knowledge/
│   ├── retrieval.py
│   ├── ingest.py
│   └── documents.py
│
├── openai/
│   ├── client.py
│   └── vector_store.py
│
├── storage/
│   ├── sqlite.py
│   └── r2.py
│
├── domain/
│   ├── game.py
│   ├── document.py
│   └── answer.py
│
└── cli/
```

Chat Adapter から直接 OpenAI API / SQLite / R2 を呼ばない。

---

# 14. 初期スコープ

まず以下だけ実装する。

1. Sprite 上で Python アプリを起動
2. SQLite 作成
3. game / document 登録CLI
4. R2への原本保存
5. OpenAI Vector Storeへの ingest
6. File Search による問い合わせ
7. Slack Adapter
8. Discord Adapter
9. 出典を含む回答

以下は後回し。

```text
管理UI
高度な会話履歴
Vision preprocessing
画像retrieval
自動ゲーム判定
高度なreranking
ユーザー投稿からの自動knowledge追加
```

---

# 15. 設計上の原則

* R2 を原本とする
* SQLite は catalog / metadata として使う
* Vector Store は検索indexとして使う
* Chat platform固有処理とRAGを分離する
* 公式情報と戦略情報を混同しない
* 最初から複雑なRAG pipelineを作らない
* semantic searchで十分なものをmetadata化しすぎない
* OpenAI固有実装はadapter層に閉じ込め、Application層から直接依存させすぎない
