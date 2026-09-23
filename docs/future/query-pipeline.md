# 目標とする query pipeline

最終的に目指す処理順。

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

## Query Decomposition / Multi-query Retrieval

検索結果 1 件で即答させたくない。質問を複数の検索観点に分解して引く。

「Serve Fish の人数差」であれば:

```text
Serve Fish / Banquet Table / player count / setup / examples / exceptions
```

## 現状との差

実装されているのは **Chat Adapter → Intent Router → Retrieval → Answer** の 4 つだけ。
GameResolver / Thread Context / Standalone Question / Query Decomposition は無い。

現在は 1 回の Responses API 呼び出しに質問文をそのまま渡しており、
横断確認は Rule Adjudicator Protocol の prompt が担っている（決定 0006 / 0010）。
