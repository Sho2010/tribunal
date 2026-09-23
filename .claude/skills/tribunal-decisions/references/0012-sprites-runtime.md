# ADR 0012: Sprites を runtime にし、pause 対策を持つ

- Status: Accepted
- Date: 2026-08-19

## Context

Slack / Discord Bot をどこで動かすかを決める必要があった。

- 常駐プロセスがあると Slack / Discord Bot は書きやすい
- Discord の mention 対応には Gateway（常時 websocket）が必要になる可能性がある
- serverless に寄せると構成が複雑になる
- Fly.io Sprites を使ってみたい、という動機もあった

## Decision

Bot 本体は Fly.io Sprites 上で動かす。Python / FastAPI を普通の Linux 環境として扱える。

Sprites には **inbound request が 30 秒ほど途切れると pause する**性質があり、
service 内で走っている処理も一緒に凍る。回答生成は 3 秒の ACK より長いので、
lazy listener で走らせると生成中に pause しうる。

対策として **Tasks API に task を登録している間だけ pause しない**性質を使う。
ack の時点で hold を取り、回答を返し終えたら解放する。expire を過ぎた task は自動で消えるので、
プロセスが落ちても hold は残らない。Sprites 外では socket が無いので hold なしで動く。

Sprite 名はプロダクト名と揃えて `tribunal` に固定する。
**稼働後に Sprite 名を変えると公開 URL が変わり、Slack の Request URL 再設定と
URL verification のやり直しが必要になる**ため、何も作っていない段階で揃えておくのが安い。

## Consequences

- 常駐プロセスとして書けるので、Discord Gateway が必要になっても構成を変えずに済む
- pause 対策のコードが必要になった（`src/tribunal/infra/sprites/task_hold.py`）。
  外部の挙動に依存した、コードだけ読んでも理由が分からない部類の実装
- HTTP port を持てる service は 1 つだけ。8080 を bot が確保する
- secret は Sprite のスナップショットに残る（専用 vault が無い）。この割り切りは合意済み
- ingest 処理は Sprite に集中させず、Cloudflare 側に寄せてもよい
