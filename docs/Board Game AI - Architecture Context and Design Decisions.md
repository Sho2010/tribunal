# Board Game AI - Architecture Context and Design Decisions

## 1. このアプリケーションが目指すもの

Slack / Discord からボードゲームについて自然言語で質問し、以下を扱えるBotを作る。

### Rule

- ルール確認
- 例外処理
- FAQ / Errata
- カード効果
- プレイヤー人数によるルール差
- 複数箇所を横断しないと判断できないルール裁定

単純な検索ではなく、**関連ルールを横断確認して厳密に裁定すること**を重視する。

### Strategy

将来的には以下にも回答できるようにする。

- 定石
- カード評価
- ドラフト判断
- カードの使い方
- シナジー
- 特定ゲーム状態での候補手比較
- 期待値・統計を使った分析

例:

- Dominion のSupplyから強そうなengine / synergyを提案
- Agricolaのドラフトpickを評価
- 特定カードの人数別評価
- プレイ方針や機会費用を比較

RuleとStrategyは同じ「ボードゲーム知識」だが、**求められる推論方法と情報の信頼性が異なるため別系統として扱う**。

---

# 2. 全体アーキテクチャ

想定構成:

```text
Slack / Discord
      │
      ▼
Chat Adapter
      │
      ▼
Query Orchestrator
      │
      ├── GameResolver
      ├── Standalone Question Generator
      ├── Intent Router
      │      ├── rule
      │      ├── strategy
      │
      ├── Retrieval
      │      ├── Rule corpus
      │      └── Strategy corpus
      │
      ├── Rule Adjudicator
      └── Strategy Analyst
             │
             ▼
          Answer
```

Knowledge ingestion:

```text
catalog (desired)        R2 (bytes / source of truth)
        │                              │
        └──────────────┬───────────────┘
                       ▼
                   sync CLI
                       │  diff & apply (冪等)
                       ▼
             OpenAI Vector Store
              (Rule Store / Strategy Store)
```

Runtime:

```text
Sprites
 └── Chatbot / application runtime
```

---

# 3. Runtime: Sprites

チャットBot本体は Sprites 上で動かす方針。

選定理由:

- Slack / Discord Botでは常駐プロセスが便利
- Discord Gateway対応が将来必要になる可能性がある
- Python/FastAPI等を普通のLinux環境として扱える
- serverless構成を過度に複雑化しない
- 今回使ってみたいという目的もある

ただし、Knowledge ingest処理はSpriteに集中させず、Cloudflare側に寄せてもよい。

---

# 4. R2をSource of Truthとする

Knowledgeの原本はCloudflare R2に保存する。

重要な設計原則:

> **R2がdocument の唯一のauthoritative stateであり、OpenAI Vector Storeは再生成可能な検索indexである。**

Vector Storeが壊れてもR2から再構築できることを前提にする。

## catalog(desired state)はgitに置く

metadataをR2のpathから導出する案は採らない(「ファイル構造とmetadataの持ち場所」)。代わりに`games/<game_id>/meta.yaml`にmetadataを宣言する。

したがってSoTは役割ごとに分かれる。

```text
document → R2
desired catalog → git repo (games/<game_id>/meta.yaml / Markdownのfront matter)
actual state    → OpenAI Vector Store (file attributes)
```

catalogをgitに置く理由:

- review / 履歴 / CIでのschema validationが効く
- 編集が容易

RDBMS / SQLiteをKnowledge catalogとして持つ案は引き続き採用しない。避けたいのは同じ情報を複数箇所で**mutableに**持つことであり、上記3者は役割が異なる。**desiredとactualを混ぜない**ことを守る(observed情報をcatalogに書き戻さない)。

## 他人の著作物をpushしない(厳守)

rulebookは個人利用の範囲で複製しているもの。守るべきは**GitHubに上げないこと**であって、ローカルの作業ツリーに実体があること自体は問題ない。むしろR2へuploadする元がそこに要る。

```text
ローカル作業ツリー : metadata + bytes (実体がある)
push対象           : metadataのみ
R2                 : bytes (uploadの宛先)
```

したがって`games/<game_id>/`配下はdocumnetとmetadataが同居し、**`.gitignore`が境界を引く**。

```gitignore
games/*/rule/
games/*/strategy/
games/*/raw/
```

拡張子ではなく**置き場所で無視する**。PDFから生成したMarkdown(「Page-aware Markdown」)やcrawl結果は拡張子で判別できないため、documentが入るディレクトリごと落として`meta.yaml`だけを残す。

この形にすると、ローカルのディレクトリがそのままR2の姿になるので、uploadは`games/<game_id>/`をそのまま同期するだけで済む。

---

# 5. Ingest経路

## v1: sync CLIによるreconcile

catalogがgit上にあるため、catalogの変更はR2 eventでは検知できない。したがってingestは**sync CLIによるreconcile**を主経路とする。

```text
catalog (desired)  +  R2 (bytes)
                ↓
            sync CLI
                ↓
          diff & apply
                ↓
OpenAI Vector Store (actual)
```

desiredとactualのdiffを取って適用するだけなので**冪等**。何度実行しても安全で、実行漏れ・重複・順序に依存しない。

- desiredにあってactualに無い → Files upload + attach + attributes設定
- actualにあってdesiredに無い → detach / delete
- 両方にあるがR2のETagが変わっている → 再upload
- orphan OpenAI File → delete (gc)

ローカル実行、またはmerge時にCIで実行する。

## R2 Event Driven Ingest (v1では保留)

当初はR2 object create/deleteをtriggerに、Cloudflare Queue経由で自動ingestする構成を検討した。

```text
R2 object create/delete → Event Notification → Queue → Worker → Vector Store
```

Queueを挟む理由はOpenAI API一時障害 / rate limit / retry / DLQ / 疎結合化だった。

しかしcatalogがgit上にある構成では、この経路が担当できるのは「R2へ直接ファイルを置いた場合の自動取り込み」だけになる。人の手間もsync CLIとほぼ変わらないため、**v1では実装しない**。

R2へのドラッグ&ドロップ運用が実際に不便になった段階で追加する。reconcileが冪等なので、後から足してもsync CLIと共存できる。

---

# 6. ファイル構造とmetadataの持ち場所

`games/<game_id>/`をローカル作業ツリーとR2で共通の単位とする。ローカルにはbytesとmetadataが同居し、pushされるのは`meta.yaml`だけ(「R2をSource of Truthとする」)。

```text
games/
  games.yaml              # game識別 (aliases, identifying terms, editions)
  <game_id>/
    meta.yaml             # document宣言。これだけpushされる
    rule/                 ┐
    strategy/             │ .gitignore。R2へupload
    raw/                  ┘
```

## pathからmetadataを導出しない

以前はpath自体をmetadata schemaにする案だった(`games/<game>/official/rulebook/ja/rulebook.pdf`から4項目を導出する)。これは採らない。

理由:

- pathがそのままschemaになる。typoしても構造上はvalidなので、誤ったattributeで静かにingestされる
- 次元(edition, expansionなど)を後から足すと、全pathをmoveして再ingestになる
- player_count / edition / 複数言語 / faqとerrataの両方に当たる文書などは階層に収まらない。結局path以外の機構が必要になり、機構が2つに増える
- pathはevent routingやprefix filterにも使うため、metadata都合で自由に再構成できない

## pathはlocatorとして扱う

`game_id` prefixだけは維持する。per-gameのlist / delete、reconciliationが素直になるため。

その下は**人が手で整理するための粗い区分**を3つ置く。

```text
<game_id>/
  rule/        # 公式。rulebook / FAQ / errata。裁定の根拠になる
  strategy/    # 非公式。前処理済みのplain text。ingest対象
  raw/         # crawl生データ。ingest対象外。前処理のやり直し用
```

- `rule` / `strategy`の境界は**trust boundary**。単なるジャンル分けではなく、Rule StoreとStrategy Storeを分離しているのと同じ線(「Rule corpusとStrategy corpus」)。ルール裁定の根拠にcommunity / personalの情報が混ざらないことを、置き場所の段階で保つ
- `raw`は**処理段階**の区別。ingest対象かどうかがディレクトリを開いた時点で分かる
- **各区分の下はフラットで、命名は自由。** editionをpathに出さない。中身は開けば分かる

これはmetadataの導出元ではなく、単なる置き場所として扱う。

## pathの区分とmeta.yamlのmetadataは別物

上記の3区分はpathに情報を出しているが、これは冒頭の「pathからmetadataを導出しない」に反しない。**粒度と読み手が違う**ため。

| | 読み手 | 粒度 |
|---|---|---|
| pathの区分 | 人 (ディレクトリを開いて整理する) | `rule` / `strategy` / `raw` の3つ |
| `meta.yaml`の宣言 | 機械 (ingest / retrieval) | `content_type: rulebook \| faq \| errata`、`authority`、`language`、`edition` … |

原則が禁じているのは**pathをmetadata schemaの代わりにすること**、つまり機械がpathをparseして属性を得る状態である。それをやるとtypoが構造上validなまま静かに通り、次元を足すたびに全pathのmoveが要る。

したがって:

- **機械が参照するのは`meta.yaml`の宣言(とfront matter)だけ。** pathをparseして`content_type`を決めない
- pathの区分を増やしたくなっても、それはmetadataの次元追加ではない。3つで足りなくなった時点で考える

## metadataの持ち場所は「形式」で決める

**そのファイル形式がmetadataを内包できるか**で決める。

| 形式 | metadataの場所 |
|---|---|
| PDF / 画像 (metadataを持てない) | `games/<game_id>/meta.yaml`に宣言 |
| Markdown (metadataを持てる) | file内のYAML front matter |

content_typeを軸に分けない理由は、公式FAQやerrataがPDFで配布されることが普通にあるため。形式基準にしておけば、PDFのFAQは自動的に`meta.yaml`側に落ち、「Page-aware Markdown」でrulebookをMarkdownへ正規化した時もfront matterへ移るのが自然に決まる。

crawlerが生成するファイルは必ずfile内にmetadata sectionを持つ(「Strategy Corpus」)。

## document catalog (games/<game_id>/meta.yaml)

**game 1つにつき1ファイル**とし、そのgameのディレクトリ直下に置く。1ファイルに全gameを並べると、game追加やcrawlerによる追記で編集が競合するため。

宣言するのは人が決める情報だけで、`openai_file_id`や同期済みhashのような観測結果は書かない(「R2をSource of Truthとする」)。

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
  - path: rule/faq-2021.pdf
    content_type: faq
    authority: official
    language: en
```

`path`は`meta.yaml`からの相対。R2のkeyは`games/<game_id>/` + `path`で組み立てる。

`path`の`rule/`は人が整理するための区分で、`content_type`(`rulebook` / `faq`)は機械が使う分類。**同じ`rule/`の下から粒度の違う`content_type`が出る**ので、pathをparseして`content_type`を決めてはいけない。

`game_id`はディレクトリ名から導出せず**中に明記する**(pathから導出しないという原則を、宣言側でも守る)。ディレクトリ名と`game_id`の一致はschemaでvalidationする。

`edition`は**optional**。FAQやerrataは版に紐づかないことがあり、必須にすると嘘を書くことになる。

YAMLを採る理由はコメントが書けること。「このFAQはpublisher見解なのでauthority=publisher」といった判断理由をmetadataの隣に残せる。`yaml.safe_load`とJSON Schemaでvalidationする。

## derived artifactは宣言しない

PDFから生成したpage-aware Markdownやpage imageはderived artifactなので手で宣言しない。変換pipelineが元PDFのmetadataをfront matterとして継承させる。catalogが宣言するのはsourceのみ。

---

# 7. Vector Store

OpenAI Vector Store / Responses API / Retrieval APIを使用する。

Vector Storeの位置付け:

> databaseではなく、R2から生成される検索index。

OpenAI側に任せるもの:

- parsing
- chunking
- embedding
- vector index
- semantic search
- keyword search

初期段階では生PDFをそのまま登録し、前処理を増やしすぎない。

---

# 8. Rule corpusとStrategy corpus

最初はmetadata filteringだけで単一Storeにまとめる案もあった。

しかし最終的には、以下の理由から論理的または物理的に分離する方針が有力。

```text
Rule Store
Strategy Store
```

最大の理由は検索性能ではなく**trust boundary**。

Rule:

```text
rulebook
errata
official FAQ
```

Strategy:

```text
strategy article
card guide
community discussion
play log
personal analysis
```

Rule回答時にcommunity opinionを公式ルールとして混ぜないことを重視する。

---

# 9. Rule Adjudicator Protocol

実験中、単純なFile Searchではモデルが近視眼的な回答をしやすい問題が発生した。

具体例:

- setup時の人数差をゲーム中の制約と誤解
- テーブル上のfish token数と支払いfish数を混同
- 1箇所の記述だけから一般化
- 関連するexampleを確認せず回答

これに対して、**Rule Adjudicator Protocolをpromptとして明示したところ大きく改善した。**

そのためRule回答では必須プロトコルとして扱う。

protocolの本文は`src/tribunal/application/rule/prompts/adjudicator.md`。回答の順序は「根拠→分析→結論」で、
結論を先に書かせない。

---

# 10. Retrievalは即Answerさせない

最初は:

```text
Question
 ↓
File Search
 ↓
Answer
```

だったが、Rule用途では不十分。

目標:

```text
Question
 ↓
Query decomposition
 ↓
Multi-query Retrieval
 ↓
Related rule collection
 ↓
Rule Adjudication
 ↓
Answer
```

例えば「Serve Fishの人数差」であれば検索観点を:

```text
Serve Fish
Banquet Table
player count
setup
examples
exceptions
```

に分解する。

---

# 11. File SearchとRetrieval API

初期実装ではResponses APIの`file_search`を使ってよい。

ただし精度改善とdebugのため、Retrieval APIを明示的に挟める構造にする。

目的:

- retrieved chunkの確認
- score確認
- multi-query
- reranking
- retrieval missとreasoning missの切り分け

重要なdebug観点:

```text
正しいchunkが取れていない
→ Retrieval problem

正しいchunkが取れているのに誤答
→ Reasoning / prompt problem
```

---

# 12. PDF Preprocessing

初期段階:

```text
PDF
 ↓
Vector Store
```

で開始する。

理由:

- OpenAI側が自動でparse/chunkする
- 最初から複雑なETLを作らない
- evalで実際の失敗パターンを観測してから改善する

---

---

---

# 13. GameResolver

ユーザーが毎回ゲーム名を書くとは期待しない。

Pipeline:

```text
User Question
 ↓
GameResolver
 ↓
Standalone Question
 ↓
Retrieval
```

GameResolverの優先順位:

1. thread contextに既知のgame_id
2. question中のgame name
3. alias
4. identifying terms
5. LLMによる推定
6. confidenceが低ければユーザーへ確認

高confidenceなら確認を挟まず回答してよい。

---

# 14. games/games.yaml

GameResolver用のcatalog。

Knowledge document一覧はここに持たせない(gameごとの`meta.yaml`が持つ、「ファイル構造とmetadataの持ち場所」)。

役割:

```text
game identification
aliases
identifying terms
edition aliases
```

例:

```yaml
version: 1

games:
  - id: nusfjord
    name: Nusfjord
    aliases:
      - ヌースフィヨルド

    identifying_terms:
      - 晩餐会テーブル
      - Banquet Table
      - 給仕
      - Serve Fish
      - 長老
      - Elder

    editions:
      - id: base
        name: Nusfjord
        default: true
      - id: bigbox
        name: Nusfjord Big Box
```

`games`はmappingではなくlistにし、`game_id`は`id`として中に明記する。

- mapping keyだと重複`game_id`が`safe_load`の時点でsilentlyに後勝ちする。検出するにはloader差し替えが要る
- `meta.yaml`(「ファイル構造とmetadataの持ち場所」)と形が揃う。あちらも`game_id`をディレクトリ名から導出せず中に明記している

`editions`はoptional。版を区別しないゲームで空の宣言を強制しない。

`games.yaml`は小さく安定したcatalogとして扱う。

JSON Schemaも用意しvalidationする(tasks B2)。

---

# 15. Slack Conversation Model

Slack threadをconversation単位として利用する。

```text
thread_ts = conversation_id
```

新規質問:

```text
@bot ヌースフィヨルドの給仕について教えて
   └─ bot response
```

follow-up:

```text
   └─ じゃあ2人戦だと？
```

thread履歴はSlackから取得する。

そのため会話履歴用DBを原則持たない。

---

# 16. 過去のBot回答の扱い

重要な原則:

> 過去のBot回答はconversation contextには使うが、ルール根拠には使わない。

理由:

一度誤答した内容を次の回答が事実として利用すると、誤りが連鎖する。

そのため:

```text
thread history
 ↓
standalone question生成
 ↓
毎回Vector Storeを再検索
```

する。

---

# 17. Standalone Question

follow-up:

```text
じゃあ2人戦だと？
```

をそのまま検索しない。

thread contextから:

```text
ヌースフィヨルドのServe Fishアクションについて、
2人戦ではどのように処理が変わるか？
```

のようなstandalone questionへ変換する。

この処理はRetrieval前に行う。

---

# 18. Slack / Discord Adapter

platform固有実装はApplication層から分離する。

```text
adapters/
  slack/
  discord/
```

Chat Adapterの責務:

- event受信
- verification
- slash command
- mention
- thread handling
- platform固有response formatting

RAGやOpenAIの実装詳細は知らない。

---

# 19. Slack

対応:

- mention
- thread conversation

slash commandは使わない。Slackが先頭`/`を横取りするため、`/game`のような自前の書式は成立しない。

3秒以内ACKが必要なため、重い処理とは分離する。

Botは原則thread内に回答する。

thread内follow-upをどう検出するかは実装時に調整する。

初期案:

- threadでもmention必須

将来:

- bot参加済みthreadならmention不要

---

# 20. Discord

slash commandはHTTP Interactionで扱える。

mention対応はGateway connectionが必要になる可能性があるため、常駐runtimeとしてSpritesを選ぶ理由の一つ。

初期優先度はSlackより低い。

---

# 21. StrategyはRuleとは別問題

Ruleの目的:

> 正しい唯一の解釈へ近づける。

Strategyの目的:

> 複数の候補からより良いプレイを推論する。

したがってRule Adjudicatorをそのまま拡張しない。

別に:

```text
Strategy Analyst Protocol
```

を用意する。

---

# 22. Strategy Analyst Protocol

想定フロー:

```text
1. game state整理
2. 関係するルール / カード能力確認
3. Strategy corpus検索
4. 候補手生成
5. synergy分析
6. opportunity cost分析
7. risk / counterplay分析
8. 条件付き推奨
```

Strategyは必ずしも唯一の正解がない。

したがって:

```text
- 前提
- 評価軸
- 複数候補
- trade-off
```

を明示する回答が望ましい。

---

---


---


---

---

---


---

---


---

# 23. 基本的なQuery Pipeline

最終的に目指す処理順:

```text
Chat Event
 ↓
Chat Adapter
 ↓
GameResolver
 ↓
Thread Context Resolution
 ↓
Standalone Question
 ↓
Intent Router
 ↓
Query Decomposition
 ↓
Retrieval
 ↓
Rule Adjudicator / Strategy Analyst
 ↓
Citation generation
 ↓
Answer
 ↓
Chat Adapter
```

この順序を崩さない。

---

---

---

# 24. 付録: 初期案から引き継いだ細目

初期の実装指示書（`first-plan.md`, 現在は削除済み / git 履歴に残る）にしか書かれていなかった決定のうち、現在も有効なものをここに移した。

## Authority（情報の信頼レベル）

```text
official     公式ルールブック / 公式FAQ / errata
publisher    出版社・ローカライズ元の公式見解
community    BGG / Reddit / wiki など
personal     自分のプレイ知見・分析
```

Rule回答の根拠に使えるのは `official` / `publisher` まで。


## Metadata方針

初期段階では過度に構造化しない。

必須:

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

以下は **metadata化せずsemantic searchに任せる**:

```text
cards
topics
mechanics
```

検索時には最低限 `game_id` をfilterする。


## Retrieval時のVision fallback（将来）

ingest時のVision前処理とは別に、検索後の再確認経路も将来的に追加可能にする。

```text
Vector Search
 ↓
page 7 hit
 ↓
R2から該当ページ画像を取得
 ↓
Visionで再確認
```

そのためpage番号は可能な限り保持する。

---

# 25. ディレクトリ構成

```text
.
├── games/                      # gameごとのmetadata + bytes。bytesは.gitignore
│   ├── games.yaml              #   game識別 (aliases, identifying terms)
│   ├── schema/                 #   JSON Schema
│   └── <game_id>/
│       ├── meta.yaml           #   document宣言。これだけpushされる
│       ├── rule/               #   .gitignore。R2へupload
│       ├── strategy/           #   .gitignore
│       └── raw/                #   .gitignore。ingest対象外
├── evals/                      # promptfooconfig.yaml, cases/, provider.py
├── docs/
├── src/tribunal/
│   ├── entrypoints/            # uvicorn 起動対象 (platformごと)
│   ├── app_factory.py
│   ├── adapters/               # inbound: chat platform
│   │   └── slack/
│   ├── application/            # platform非依存のorchestration
│   │   ├── answer_service.py   #   adapterが触る唯一の入口
│   │   ├── ports.py            #   差し替え点のProtocol
│   │   ├── pipeline/           #   game_resolver / standalone_question / intent_router / decomposition
│   │   ├── rule/               #   Rule Adjudicator (+ prompts/)
│   │   └── strategy/           #   Strategy Analyst (+ prompts/)
│   ├── domain/                 # Game, Document, Answer, Source, ContentType, Authority
│   ├── infra/                  # outbound: 外部システムのclient
│   │   ├── openai/             #   files / vector_store / responses / retrieval
│   │   └── r2/
│   ├── knowledge/              # catalog読み込み / front matter / reconcileの差分計算
│   └── cli/                    # sync / gc / doctor
└── tests/
```

依存方向:

```text
entrypoints → adapters → application → domain
                              ↓ (ports経由)
                            infra
cli → knowledge → infra
```

eval runnerは自作しない。promptfooに`evals/promptfooconfig.yaml`とPython providerを置き、
providerが`AnswerService`を叩く。promptfooはnpmパッケージなのでbotの実行環境には入らない。

## 名前

プロダクト名 / import package = **tribunal**(裁定所)。Rule Adjudicator(「Rule Adjudicator Protocol」)を中心に据えた性格をそのまま名前にしている。

```text
package : tribunal          (src/tribunal/)
起動対象 : tribunal.entrypoints.slack:app
repo    : github.com/Sho2010/tribunal
Sprite  : tribunal          (URL: tribunal-<org-id>.sprites.app)
```

Sprite名も揃えた。**稼働後にSprite名を変えると公開URLが変わり、SlackのRequest URL再設定とURL verificationのやり直しが必要になる**ため、まだ何も作っていない段階で揃えておくのが安い。

---

# 26. Intent判定の仕様

Intent Routerは当初`rule` / `strategy` / `hybrid`の3語しか決めていなかった。実装に入る段階で以下を確定した。

## 判定は質問文だけを見る

入力は**standalone question 1つ**とする。thread contextを判定材料にしない。

「基本的なQuery Pipeline」の順序ではIntent Routerの手前でstandalone questionが生成されるので、threadの情報はその時点で質問文に畳み込まれている。判定器がthreadを再び見ると**同じ情報を2箇所で解釈する**ことになり、食い違ったときにどちらを正とするか決められない。

またthreadを見る判定は状態が増え、LLMへの依存が強くなってデバッグが困難になる。決定的に判定できる形を保つほうが運用コストが低い。

## hybridを作らない

出力は`Rule` / `Strategy`の2値 + `Ambiguous`。

hybridは「Rule Storeでinteraction確認 → Strategy Storeで評価検索 → Strategy Analystが統合」で、**promptを選ぶ話ではなくretrievalを2本走らせて統合する話**。retrievalが2本必要になる段階まで意思決定を後回しにする。3値にすると`hybrid`を返せる型なのに実装が対応しない状態になる。

## Ambiguousは既定側（Rule）で処理する

GameResolverの`Unknown`に相当する状態は作らない（intentに「どちらでもない質問」は実質存在しない）。

`Ambiguous`をRuleに倒すのは、**外したときの被害が非対称**だから。

```text
strategy質問をruleで答える → 「資料に記載がありません」と返る（無害）
rule質問をstrategyで答える → 非公式資料でルールを語る（「Rule corpusとStrategy corpus」のtrust boundary違反）
```

迷ったらRuleが安全側。ユーザーへ聞き返す形は取らない（Slackの体験として重い）。

## 判定優先順位

```text
1. 明示タグ
2. rule寄りkeyword
3. strategy寄りkeyword
4. LLMによる推定        (未実装。場所だけ空ける)
5. 既定 → Rule
```

**rule keywordをstrategyより先に見る。** 「この効果は強い制約ですか」のようにstrategy語を含むが実体はrule裁定の質問を取りこぼさないため。両方に該当した場合は`Ambiguous`とし、曖昧だった事実を消さない。

## 明示タグの形式

行頭のみ。空白あり / なしの両方を受ける。

```text
戦略: / strategy: / [戦略] / [strategy]    → Strategy
ルール: / rule:   / [ルール] / [rule]      → Rule
```

コロン形式を主、角括弧形式をaliasとする。**日常的に打つ形と確実に効かせたい形で求めるものが違う**ため両方受ける（コロンは打鍵が軽くIMEでも近い / 角括弧は誤検出がほぼない）。行頭限定にすれば曖昧さは形式の数に依存しないので、aliasを増やすコストは実質ゼロ。

`/strategy`のようなslash command風の形は採らない。**Slackが行頭の`/`をslash commandとして横取りする**ため、行頭に打った場合に送信前に弾かれる。将来slash commandを実装するときに名前も衝突する。

判定後、タグは質問文から除去してretrieverへ渡す（タグが検索クエリに混ざると検索結果が劣化する）。

## タグなしのときは判定結果を回答に添える

タグを付けずに投げた場合、どちらとして処理したかを回答に明示する。運用ルールを事前に説明しなくても使いながら覚えられ、**判定が壊れていることが使用中にすぐ分かる**。タグを明示した場合は付けない（ユーザーが既に知っている情報なので）。

## keyword群はチューニング前提

初期セットは当て推量であり、実際の質問文を見て調整する。**運用としては明示タグを主経路とし、keywordはタグを忘れた場合の推測**として位置づける。したがってkeywordの精度が甘くても実害は小さい。

## Protocolを切る

判定方式は`keyword` → 将来の`LLM`で**実装が2つになることが確定している**ため、「ディレクトリ構成」の「portを切るのはretrievalだけ」の例外としてProtocolを置く。retrievalにportを切ったのと同じ理由（実装が2つになる確定）による。

置き場所は`application/pipeline/`（「ディレクトリ構成」に従う）。`ports.py`には置かない。`ports.py`は「adapterから見た差し替え点」で、intent判定はapplication内部の部品なので層が違う。
