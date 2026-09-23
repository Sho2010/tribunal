# ADR 0015: retrieval を Vector Store + File Search で始める

- Status: Accepted
- Date: 2026-08-19

## Context

retrieval の初期実装として「Vector Store を使わず、PDF を直接 file input としてモデルへ渡す」案を検討した。
Vector Store の管理が要らず、最初の 1 ゲームなら成立する。

しかしこの案は `file_id` を自前で管理する前提だった。
どの file が何の document かを記録する場所として SQLite を想定しており、
それは [0001](0001-r2-as-source-of-truth.md) で却下した「同じ情報を複数箇所で mutable に持つ」構成になる。

## Decision

Vector Store + File Search で進める。直接 file input は採らない。

`file_id` と document の対応は Vector Store の file attributes（actual state）が持ち、
desired は catalog が持つ（[0001](0001-r2-as-source-of-truth.md)）。自前の管理台帳を作らない。

## Consequences

- parsing / chunking / embedding を OpenAI に任せられる（[0010](0010-retrieval-must-be-debuggable.md)）
- document が増えても同じ経路で扱える
- 検索の中身（どの chunk が何点で引かれたか）が見えない。
  これは明示的な Retrieval API を挟むまで解消しない
