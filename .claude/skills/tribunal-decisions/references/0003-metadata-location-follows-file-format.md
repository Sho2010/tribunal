# ADR 0003: metadata の置き場所はファイル形式で決める

- Status: Accepted
- Date: 2026-08-19

## Context

[0002](0002-metadata-is-declared-not-derived.md) で metadata を宣言すると決めたあと、
その宣言をどのファイルに書くかを決める必要があった。content_type で分ける案もあった。

## Decision

**そのファイル形式が metadata を内包できるか**で決める。

| 形式 | metadata の場所 |
|---|---|
| PDF / 画像（metadata を持てない） | `games/<game_id>/meta.yaml` に宣言 |
| Markdown（持てる） | file 内の YAML front matter |

content_type を軸に分けないのは、公式 FAQ や errata が PDF で配布されることが普通にあるため。
形式基準にしておけば、PDF の FAQ は自動的に `meta.yaml` 側に落ちる。

`meta.yaml` は **game 1 つにつき 1 ファイル**とし、そのゲームのディレクトリ直下に置く。
1 ファイルに全 game を並べると、game 追加や crawler による追記で編集が競合する。

`game_id` はディレクトリ名から導出せず中に明記する（[0002](0002-metadata-is-declared-not-derived.md) の原則を宣言側でも守る）。
`edition` は optional にする。FAQ や errata は版に紐づかないことがあり、必須にすると嘘を書くことになる。

YAML を採るのはコメントが書けるため。「この FAQ は publisher 見解なので authority=publisher」
といった判断理由を metadata の隣に残せる。

derived artifact（PDF から生成した Markdown や page image）は宣言しない。
変換 pipeline が元 PDF の metadata を front matter として継承させる。catalog が宣言するのは source のみ。

## Consequences

- rulebook を Markdown へ正規化したとき、metadata の置き場所が自動的に front matter へ移る
- game を足す PR が他の game の宣言に触らない
- 宣言が 2 箇所（`meta.yaml` と front matter）に分かれるので、読む側は両方を見る必要がある
