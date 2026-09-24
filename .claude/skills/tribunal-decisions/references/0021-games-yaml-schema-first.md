# ADR 0021: games.yaml の schema は JSON Schema を正にし、pydantic モデルを生成する

- Status: Accepted
- Date: 2026-09-24

## Context

games.yaml の読み込みは、フィールドごとに型とキーの有無を手で検査していた。GameResolver が
`name` / `aliases` / `identifying_terms` を読むようになって検査が増え、
`editions` や `meta.yaml` を読むようになればさらに増える。

検討した形:

- **手書きの検査を続ける** — フィールドが増えるたびに検査と変換を両方書くことになる
- **pydantic のモデルを正にし、JSON Schema は書き出す** — 生成ツールが要らず、検証と変換が
  1 ファイルで済む。ただし正が Python のコードになり、YAML を書く人が見る定義は派生物になる
- **JSON Schema を正にし、pydantic のモデルを生成する** — 正がデータファイルになる。
  生成のステップが 1 つ増える

どちらを正にしても、派生物（書き出した JSON Schema か、生成したモデル）が正とずれていないかを
検査する手間は同じ。

## Decision

**`games/schema/games.schema.json`（JSON Schema）を正にし、datamodel-code-generator で
pydantic v2 のモデルを生成する。**

- games.yaml は人が宣言・レビューするデータなので、その定義もデータファイルとして置く。
  エディタの YAML 補完・検証にもそのまま使える
- アプリケーションの一般的な作り方（schema first）に揃える。このリポジトリで
  Python の schema first を経験しておくことも目的に含む
- 生成物は `src/tribunal/knowledge/games_schema.py` に commit する。生成オプションは
  pyproject の `[tool.datamodel-codegen]` に置き、引数なしで再生成できるようにする
- 生成物のずれは **pytest を落として検出する**。CI で再生成して自動 commit する案は、
  workflow に write permission を持たせる必要があるので採らない
- JSON Schema で表現できない検査（game id の一意性）と、domain の `Game` への変換は、
  生成物の外に手で書く。domain は pydantic に依存させない
- 検査の意味は変えない。`stores` のキー欠落・`null`・空文字の区別は
  [0020](0020-per-game-stores-in-games-yaml.md) のまま

## Consequences

- schema を変えたら再生成して一緒に commit する必要がある。忘れると pytest が落ちる
- datamodel-code-generator は dev 依存だけで、bot の実行環境には入らない。
  生成物が import する pydantic は本体の依存に明示する
- `meta.yaml` や Markdown の front matter の schema を足すときも、同じ形（JSON Schema → 生成）に
  寄せられる
