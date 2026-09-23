# ADR 0011: 会話履歴 DB を持たず、過去の Bot 回答をルール根拠にしない

- Status: Accepted
- Date: 2026-08-19

## Context

thread で追い質問できるようにするには、会話の文脈が要る。
文脈を持つ方法として、自前の会話履歴 DB を置く案があった。

また、一度答えた内容を次の回答が再利用すると効率はよい。

## Decision

Slack thread を conversation 単位（`thread_ts` = conversation_id）とし、
**thread 履歴は Slack から取得する。会話履歴用 DB を原則持たない。**

そして **過去の Bot 回答は conversation context には使うが、ルール根拠には使わない。**

一度誤答した内容を次の回答が事実として利用すると、誤りが連鎖する。
thread 履歴からは standalone question を生成し、**毎回 Vector Store を再検索する。**

## Consequences

- 状態を持たないので、Bot を作り直しても会話が壊れない
- 同じ質問を繰り返すと毎回検索する。キャッシュが効かない
- 誤答が次の回答に伝播しない
- Slack API への依存が増える（thread 履歴の取得）
