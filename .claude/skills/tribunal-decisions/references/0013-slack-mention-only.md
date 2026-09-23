# ADR 0013: Slack では mention だけを受け、thread に返す

- Status: Accepted
- Date: 2026-08-22

## Context

Slack から Bot を呼ぶ方法として slash command / mention / DM があった。
また Slack は event に 3 秒以内の ACK を要求する。

## Decision

`app_mention` だけを受ける。**slash command は使わない。**
Slack が行頭の `/` を横取りするため、`/game <question>` のような自前の書式は成立しない
（[0009](0009-intent-tags-and-keywords.md) でタグに `/` を使わない理由と同じ）。

回答は原則 thread 内に返す。top-level の mention はその message に thread をぶら下げ、
thread 内の mention はその thread に返す。

3 秒 ACK を守るため、**ack と回答生成を分離する**。ack は即返し、生成は lazy listener で走らせる。
生成には時間がかかるので、先に「調べている」ことを伝える受付メッセージを出し、
回答は別メッセージとして返す。

platform 固有の実装は application 層から分離する。Chat Adapter が持つのは
event 受信 / verification / mention / thread handling / platform 固有の整形までで、
**RAG や OpenAI の実装詳細を知らない。**

## Consequences

- チャンネルを汚さずに済む（thread に収まる）
- 受付メッセージと回答で 2 通になる。受付メッセージは編集せず残る
- mention が必須なので、thread 内の追い質問でも `@bot` を付ける必要がある
- Discord は Gateway 方式で FastAPI に mount できないため、同じ adapter には乗らない
