# ADR 0014: eval runner を自作せず promptfoo を使う

- Status: Accepted
- Date: 2026-09-23

## Context

RAG の改善を「体感」ではなく数値で測るために eval が要る。
当初は `src/tribunal/eval/` に runner を書き、`cli/eval` から回す構成を想定していた。

候補を調べた結果:

- OpenAI Evals API は **2026-11-30 に停止**（2026-10-31 に read-only）。Datasets も同じ platform で同時に終わる
- OpenAI 公式が移行先として promptfoo を挙げている
- eval 実行層のデファクトは promptfoo と deepeval の 2 つ

## Decision

eval runner を自作しない。**promptfoo** を使い、`evals/` に `promptfooconfig.yaml` と
Python provider（`AnswerService` を叩くだけの薄いもの）を置く。

promptfoo は npm パッケージなので **bot の実行環境には入らない**。
依存の向きは promptfoo → tribunal の一方向で、`pyproject.toml` にも Sprite にも影響しない。

`evals/` は `games/` と同じく `src/` の外に置く。人が宣言・レビューするデータでコードではない。

最初は Adjudication Eval（最終回答の質）だけを作る。
Retrieval Eval は [0010](0010-retrieval-must-be-debuggable.md) の通り、
`Source` が chunk / score を持たないため現状では書けない。

## Consequences

- runner のメンテナンスが要らない。assertion の種類も揃っている（model-graded / RAG 系）
- 開発環境に Node が必要になる。CI で回すなら job を分ける
- protocol prompt を `.md` で外に出してあるので、prompt を差し替えた前後で同じ eval を回せる
- モデル採点の assertion には API コストがかかる
