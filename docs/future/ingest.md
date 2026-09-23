# ingest（R2 / meta.yaml / sync CLI）

document を R2 に置き、宣言に従って Vector Store へ載せるまでの経路。
**どれも未実装。** 現在は手で Vector Store に載せている。

## ディレクトリ

```text
games/
  games.yaml              # game識別（実在。読むコードは無い）
  schema/                 # JSON Schema（未）
  <game_id>/
    meta.yaml             # document宣言。これだけpushされる（未）
    rule/                 ┐
    strategy/             │ .gitignore。R2へupload（ディレクトリは実在）
    raw/                  ┘ ingest対象外。前処理のやり直し用
```

`rule` / `strategy` の境界は trust boundary、`raw` は処理段階の区別（決定 0002 / 0004）。
各区分の下はフラットで命名は自由。edition を path に出さない。

## meta.yaml

game 1 つにつき 1 ファイル（決定 0003）。

```yaml
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

`path` は `meta.yaml` からの相対。R2 の key は `games/<game_id>/` + `path` で組み立てる。

必須にする予定の項目: `game_id` / `content_type` / `authority` / `edition` / `language`。
必要になってから足す: `player_count` / `expansion`。
`cards` / `topics` / `mechanics` は metadata 化せず semantic search に任せる。

content_type の候補: `rulebook` / `errata` / `faq` / `strategy` / `card_guide` / `play_log`。

## sync CLI

desired（catalog）と actual（Vector Store）の diff を取って適用する（決定 0005）。

- desired にあって actual に無い → upload + attach + attributes 設定
- actual にあって desired に無い → detach / delete
- ETag が変わっている → 再 upload
- orphan な OpenAI File → delete

冪等なので何度実行してもよい。ローカル実行、または merge 時に CI で実行する。

置き場所の案: `src/tribunal/knowledge/`（catalog 読み込み / front matter / 差分計算）と
`src/tribunal/cli/`（sync / gc / doctor）。`adapters/` `application/` からは import しない。

## 受け入れ条件

```text
1 ゲームの rulebook を R2 に置き meta.yaml に宣言する
 → 手動で Vector Store に載せる
 → Slack でルール質問に出典付きで答えられる
```

```text
宣言していない R2 object が ingest されない
```

sync CLI を作ったあと（決定 0016 の閾値を超えてから）:

```text
sync を 2 回連続で実行しても差分が出ない（冪等の確認）
```
