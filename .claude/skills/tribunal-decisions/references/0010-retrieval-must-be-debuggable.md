# ADR 0010: File Search で始め、retrieval と reasoning を切り分けられる形を保つ

- Status: Accepted
- Date: 2026-08-19

## Context

Rule 用途では `Question → File Search → Answer` の一発では不十分だと考えていた。
関連する節・例外・example を横断しないと裁定できない質問があるため。

一方で、最初から query decomposition や multi-query を作ると、
どこが効いているのか分からないまま複雑になる。

## Decision

初期実装では Responses API の `file_search` を使う。ただし retrieval を差し替えられる形を保つ。

`Retriever` Protocol を切り、`file_search` 版と将来の明示的な Retrieval API 版で
実装が 2 つになることを前提にする（**port を切るのは retrieval だけ**という方針の由来）。

目的は精度改善そのものより **debug の切り分け**。

```text
正しい chunk が取れていない   → Retrieval problem
正しい chunk が取れているのに誤答 → Reasoning / prompt problem
```

この切り分けができないと、prompt を直すべきか検索を直すべきか分からないまま手を入れることになる。

PDF の前処理も同じ理由で後回しにする。生 PDF をそのまま Vector Store に載せ、
parsing / chunking / embedding は OpenAI に任せる。**eval で実際の失敗パターンを観測してから改善する。**

## Consequences

- 当面は 1 回の Responses API 呼び出しで、質問文をそのまま投げる。
  横断確認は [0006](0006-rule-adjudicator-protocol.md) の prompt が担っている
- `Answer.sources` が title と uri しか持たず file_id 単位で dedup されるため、
  chunk / score / 順位が残らない。「正しい section を引けたか」は現状では測れない
- Retrieval Eval は明示的な Retrieval API が入るまで書けない
