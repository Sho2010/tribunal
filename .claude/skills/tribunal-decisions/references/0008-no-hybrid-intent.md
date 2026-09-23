# ADR 0008: intent に hybrid を作らず、曖昧なら Rule に倒す

- Status: Accepted
- Date: 2026-08-26

## Context

Intent Router の出力を当初 `rule` / `strategy` / `hybrid` の 3 語で決めていた。
実装に入る段階で、hybrid が何を指すのかを確定する必要が出た。

## Decision

出力は `Rule` / `Strategy` の 2 値 + `Ambiguous` とし、**hybrid を作らない。**

hybrid は「Rule Store で interaction 確認 → Strategy Store で評価検索 → Strategy Analyst が統合」であり、
**prompt を選ぶ話ではなく retrieval を 2 本走らせて統合する話**だった。
retrieval が 2 本必要になる段階まで決定を後回しにする。
3 値にすると `hybrid` を返せる型なのに実装が対応しない状態になる。

`Ambiguous` はユーザーに聞き返さず、**既定側（Rule）で処理する。**
理由は外したときの被害が非対称だから。

```text
strategy 質問を rule で答える → 「資料に記載がありません」と返る（無害）
rule 質問を strategy で答える → 非公式資料でルールを語る（trust boundary 違反）
```

判定は **standalone question 1 つだけを見る**。thread context を判定材料にしない。
pipeline 上、Intent Router の手前で standalone question が生成されるので、
thread の情報はその時点で質問文に畳み込まれている。判定器が thread を再び見ると
同じ情報を 2 箇所で解釈することになり、食い違ったときにどちらを正とするか決められない。

## Consequences

- 「このカードコンボ強い？」のようにルールと戦略に跨る質問は、Rule として処理される
- 聞き返しが無いので Slack の体験は軽い。代わりに誤判定は回答を見るまで分からない
  （そのため untagged のときは判定結果を回答に添える。[0009](0009-intent-tags-and-keywords.md)）
- retrieval が 2 本必要になったら、この決定を supersede して hybrid を足す
