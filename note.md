# bg-bot 初回デプロイ runbook（Sprites）

> docs 調査で判明した修正済み版。詳細・出典は `docs/sprites.md`（§10）を参照。
> 前提: ローカルに `sprite` CLI をインストール・認証済み。repo は git clone できる状態。

## 1. Sprite を作る, 繋ぐ
```bash
sprite create tribunal        # 名前は任意
sprite use tribunal           # 以降のデフォルト対象に
sprite list                   # 確認
```

繋ぐ
```
sprite sessions --tty /bin/bash
```

## 2. コードを Sprite に載せる
ディスクは自動永続するので `exec` での clone でよい（checkpoint 不要）。
```bash
sprite exec -- bash -c "cd /home/sprite && git clone <REPO_URL> bg-bot"
```
- public repo なら HTTPS clone が楽。SSH clone は Sprite 側に鍵が必要。

## 3. 依存を入れる（uv）
uv がプリインストールか不明なので明示インストール前提。結果は永続する。
```bash
sprite exec -- bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"   # 未導入時
sprite exec -- bash -c "cd /home/sprite/bg-bot && ~/.local/bin/uv sync"
```

## 4. サーバは **service 化**（★ここが最重要の修正点）
`exec` の foreground 起動は **sleep でプロセスが死ぬ**（RAM/プロセスは pause で失われる）。
常駐は Service にする → wake 時に自動再起動される。secret は起動時 env 注入（ファイル直置きなし）。
```bash
sprite exec -- sprite-env services create tribunal \
  --cmd /home/sprite/.local/bin/uv \
  --args "run,uvicorn,src.entrypoints.slack:app,--host,0.0.0.0,--port,8080" \
  --dir /home/sprite/bg-bot \
  --env "SLACK_BOT_TOKEN=xoxb-...,SLACK_SIGNING_SECRET=..." \
  --http-port 8080
```
注意:
- `--cmd` は**バイナリのみ**（シェル文字列不可）。`--args` / `--env` は**カンマ区切り**（値にカンマを含めない）。
- 起動対象は `src.entrypoints.slack:app`（`src.main:app` でも後方互換で可）。
- **http-port を持てる service は1つだけ**（8080 を bot に確保。2つ目は 409）。
- `sprite-env services` は Sprite 内部コマンド。ローカルからは上記のように `sprite exec -- sprite-env ...` でラップ。または **MCP の `service_create` / `service_start` が確実**。
- 管理: `sprite exec -- sprite-env services list / start / stop slackbot`

## 5. port 8080 を public 公開して URL 取得
```bash
sprite config update --url-auth public   # 既定は org 限定(private)
sprite info                              # → https://bg-bot-<org-id>.sprites.app/
```
- slack_bolt の署名検証が前段認証になるので public 化して可。
- まず `curl https://bg-bot-<org-id>.sprites.app/` が `{"status":"ok",...}` を返すか確認。

## 6. Slack App 側
- **Event Subscriptions** を ON、Request URL = `https://bg-bot-<org-id>.sprites.app/slack/events`
  - 保存時に challenge が飛ぶ → 200 で Verified。Sprite が寝てると初回 wake に 1–2s、失敗したら再保存。
- **Subscribe to bot events**: `app_mention`
- **OAuth & Permissions**: `app_mentions:read`, `chat:write` → ワークスペースに（再）インストール
- install は単一 token 運用（OAuth install URL は使わない）。api.slack.com の Install ボタンで `SLACK_BOT_TOKEN` を取得。

## 7. 動作確認
```bash
# ログ確認
sprite exec -- tail -n 50 /.sprite/logs/services/slackbot.log
```
- bot を対象チャンネルに招待 → `@bg-bot テスト`
- `🎲 boardgame-ai は準備中です。` が返ればゴール
- **sleep/wake**: 30秒放置で warm pause → 再 mention で wake（warm 100–500ms / cold 1–2s）して応答。service は cold wake でも自動再起動されるので手動操作不要（＝常時起動でない挙動の確認）。

## 覚えておくべき前提（通説の修正）
- **ディスク永続に checkpoint は不要**。checkpoint は git-restore 的な手動 undo。
- **RAM/プロセスは pause で消える** → 常駐は必ず service。
- **開いた TCP は warm でも切れる**が、本 bot は inbound POST 駆動なので service だけで足りる（Tasks API 不要）。
- **wake レイテンシ × Slack 3秒 ack** → slack_bolt は即 ack（lazy listener）。※現状は固定応答で処理一瞬なので実害なし。
- **secret は checkpoint/スナップショットに残る**（Sprites に専用 vault 無し）。リモート配置は割り切り済み。

## ⚠️ 実機で確定したい曖昧点（docs 未明記）
- `sprite exec --env` / `sprite-env services` の外部 CLI からの正確な呼び出し形（`--help` で確認、or MCP `service_*` を使う）。
- uv/uvicorn のプリインストール有無（上記は明示インストール前提）。
- `sprite config update --url-auth` と `sprite url update` の表記ゆれ。
- アイドルタイムアウト「約30秒」は将来変更含みの表現。
