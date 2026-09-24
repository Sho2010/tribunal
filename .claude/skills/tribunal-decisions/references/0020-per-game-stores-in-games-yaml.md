# ADR 0020: Store をゲームごとに持ち、games.yaml に区分名をキーにして宣言する

- Status: Accepted
- Date: 2026-09-24
- Supersedes: [0004](0004-split-rule-and-strategy-stores.md) の「Vector Store が別（`TRIBUNAL_RULE_VECTOR_STORE_ID` / `TRIBUNAL_STRATEGY_VECTOR_STORE_ID`）」

## Context

Store は全ゲーム共通で Rule / Strategy の 2 つだけで、env で ID を 1 つずつ渡していた。
ゲームの絞り込みは file attribute `game_id` のフィルタで行う作りだったが、
Slack から `game_id` を渡していないので、実際には全ゲームの資料を区別せずに検索していた。

ゲームごとに Store を分けたい。検討した形:

- **1 ゲーム : n Store（区分ごとに複数 Store）** — 同じ区分に Store が並んでも、どれを引くかを決める
  材料が無い。使い分けの判断の仕様が無いまま Store だけ並べることになる
- **区分をゲームごとに持つ**（例: ドミニオンに rule / strategy に加えて「サプライ管理」）—
  処理は GameResolver → Classification → LLM 呼び出しの順なので、ゲームが先に決まり順序は壊れない。
  ただし `Intent` の enum、タグ / keyword、protocol prompt、authority の扱いが全ゲーム共通の
  `[rule, strategy]` を前提にしているので、それらをゲーム依存にする変更になる
- **1 ゲーム : 2 Store（rule / strategy）** — 今の区分のまま、Store をゲームごとにするだけ

## Decision

**1 ゲームにつき rule / strategy の Store を 1 つずつ持つ。** 区分をゲームごとに持たせるのは、
必要になってから行う。

- 宣言は `games/games.yaml` の各ゲームの `stores`。**区分名をキーにした map** にし、
  `rule_store:` / `strategy_store:` のような固定項目にしない。区分をゲームごとに持たせるときに
  キーが増えるだけで済む
- 値は Store ID 1 つ。未設定は `null`
- キーは今は `rule` / `strategy` だけを許し、それ以外は読み込み時にエラーにする
- Store ID の env（`TRIBUNAL_RULE_VECTOR_STORE_ID` / `TRIBUNAL_STRATEGY_VECTOR_STORE_ID`）は廃止する
- 対象ゲームは、`game_id` が渡されればそれ、無ければ Rule Store を持つゲームが 1 つのときだけそれに決める。
  決められなければ回答しない。**複数ゲームの Store をまとめて検索しない**
- Rule Store の無いゲームは回答の対象にしない。対象が 1 つも無ければ起動時に落とす
- ある区分の Store が無いとき、別の区分・別のゲームの Store で代替しない（[0004](0004-split-rule-and-strategy-stores.md) の fallback 禁止を、ゲーム単位に広げたもの）

## Consequences

- ゲームの分離が Store 単位になり、file attribute `game_id` のフィルタは使わなくなった
- Rule Store を持つゲームが 2 つ以上になると、GameResolver が入るまで Slack からは全質問が
  「特定できない」になる
- Store ID は Vector Store 側の実体の ID なので、desired catalog（git）に actual state が入る
  （[0001](0001-r2-as-source-of-truth.md) の「desired と actual を混ぜない」と緊張する）。
  Vector Store を作り直すと games.yaml を書き換える必要がある
- 区分を増やすときは、`Intent` / 判定 / protocol prompt / authority をゲーム依存にする変更が先に要る
