# Fly.io Sprites 運用リファレンス (tribunal 向け)

> このドキュメントは Fly.io Sprites の公式ドキュメント (https://docs.sprites.dev) を蒸留した**運用者向けリファレンス**です。
> 想定ワークロード: **Python (FastAPI + slack_bolt) の Slack bot**。ポート 8080 で Slack HTTP Events (`/slack/events`) を受け、sleep/wake を跨いで常駐し、secrets (`SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`) は起動時に注入する。
>
> 最終確認日: 2026-08-18 / CLI: v0.0.1-rc47 / OS イメージ: Ubuntu 25.10
>
> ⚠️ **推測・曖昧箇所は各所で「⚠️ 推測」「⚠️ 曖昧」と明記**しています。ドキュメントに明記がなかった点は末尾にまとめています。

---

## 1. 概要 / メンタルモデル

- Sprite = **永続化される、ハードウェア分離された Linux 環境**。コンテナではなく**専用 microVM (Firecracker 系)** で、ハードウェアレベル分離。
- **フル Linux** (Ubuntu 25.10)。`sudo`, `apt`, 任意のバイナリ/プロセスが動く。Node / Python3 / Go などのランタイムがプリインストール。
- リソース: **8 vCPU / メモリは負荷に応じてオートスケール / 100 GB ストレージ**(実使用量課金)。
- ファイルシステムは **ext4、高速 NVMe**。アイドル時は**durable なオブジェクトストレージにバックアップされ、wake 時に自動復元**される。→ **ディスクへ書いたものはコマンドをまたいで永続する**(パッケージインストール、git clone、SQLite など)。
- 各 Sprite は**固有の URL**を持ち、内部の Web サービス/API を簡単に公開できる。
- メンタルモデルの核心: **「ディスクはスナップショットに入る、メモリは入らない」**。この境界がライフサイクル・サービス・チェックポイントすべてを貫く原則。

出典: https://docs.sprites.dev/ , https://docs.sprites.dev/concepts/lifecycle/ , https://docs.sprites.dev/sprite-maintenance/

---

## 2. ライフサイクルと永続化

3 状態で遷移する:

| 状態 | 説明 | wake レイテンシ | メモリ/プロセス |
|------|------|----------------|----------------|
| **Active** | リクエスト/コマンド/接続を処理中。課金対象。 | — | 稼働 |
| **Warm** | VM サスペンド。メモリは凍結。課金停止。 | **100–500ms** | **凍結され、途中から再開**(プロセスは殺されない) |
| **Cold** | VM 完全停止。メモリ破棄。 | **1–2s** | **破棄。プロセスはゼロから起動** |

- **アイドルタイムアウト: 約 30 秒**(現状値)で Active → Warm へ。
- **wake-on-request**: 停止中でも inbound HTTPS / コマンド実行で**自動的に起きる**。CLI 常駐は不要(「always on: no CLI required」)。

### 何が生き残るか

**Warm / Cold 両方で永続(ディスク上のもの):**
- ファイル/ディレクトリ、インストール済みパッケージ、git リポジトリ、SQLite など。
- **手動チェックポイントは不要**。ディスク永続は自動。

**pause で失われるもの:**
- 実行中プロセス(**Services または Tasks API で管理していない限り**)
- インメモリ状態
- **開いている TCP 接続は warm でも切れる**(warm でもプロセスは凍るが、リモート側は接続を保持できない → クライアント側で再接続が必要)

### service が必要 vs one-off exec で十分

- **常駐が必要 → Service にする**: 我々の uvicorn サーバのように「起動しっぱなしで inbound を待つ」プロセス。cold wake でも自動再起動される。
- **one-off で十分 → `sprite exec`**: `pip install` / `git clone` / `uv sync` などの1回きりのセットアップ。結果(ディスク変更)は永続するので exec でよい。
- ⚠️ 重要: **quiet な(リクエストを処理していない)service は Sprite を Active に保持しない**。HTTP を処理している間だけ activity としてカウントされる。Slack bot はリクエストが来れば wake して処理し、その後 30 秒で再び warm に落ちる = 正常な挙動。**外向き接続を維持したいワークロード(websocket ワーカー等)は別途 Tasks API が必要**だが、Slack の Events API は inbound POST なので Service だけで足りる。

出典: https://docs.sprites.dev/concepts/lifecycle/ , https://docs.sprites.dev/keeping-sprites-running/ , https://docs.sprites.dev/concepts/services/

---

## 3. Services(常駐プロセス)

Service = **Sprite ランタイムが所有する管理プロセス**。boot 時に起動、クラッシュ時に再起動、HTTP トラフィックを受けられる。手動 exec のプロセスと違い、再起動後も自動復活する。

### 作成コマンド構文

```
sprite-env services create <name> --cmd <binary> --args "<a,b,c>" [options]
```

| フラグ | 意味 |
|--------|------|
| `--cmd <path>` | 実行バイナリ(必須、**バイナリのみ** — シェル文字列不可) |
| `--args <a,b,c>` | **カンマ区切り**の引数リスト |
| `--env <K=v,...>` | **カンマ区切り**の環境変数 |
| `--dir <path>` | ワーキングディレクトリ |
| `--needs <svc,...>` | 依存する(先に起動すべき)service |
| `--http-port <port>` | Sprite URL をこのポートへルーティング + リクエストで auto-start |
| `--duration <time>` | 作成後のログストリーム時間(既定 5s) |
| `--no-stream` | 作成後のログストリームをしない |

### 管理コマンド

| コマンド | 機能 |
|----------|------|
| `sprite-env services list` | 一覧と状態 |
| `sprite-env services get <name>` | 定義とライブ状態 |
| `sprite-env services start <name>` | 停止中の service を起動 |
| `sprite-env services stop <name>` | 停止(明示停止した service は起動されるまで停止のまま) |
| `sprite-env services restart <name>` | stop→start しログをストリーム |
| `sprite-env services signal <name> <SIGNAL>` | シグナル送信(HUP, TERM 等) |
| `sprite-env services delete <name>` | 定義削除 |

### 自動再起動の挙動

- **Warm wake**: 再起動せずプロセスがそのまま再開(100–500ms)。
- **Cold boot**: 全 service を依存順にゼロから起動(1–2s)。
- **クラッシュ**: 自動再起動、`restart_count` が増える。
- **明示 stop**: 手動 start するまで停止のまま。

### HTTP ポートの制約(重要)

- **`--http-port` を持てる service は 1 つだけ**。2 つ目を作ると `409: another service already has an HTTP port configured` で失敗。
- cold な Sprite にリクエストが来ると、http-port を持つ service が auto-start する。

### ログ

`/​.sprite/logs/services/<name>.log` に出力(タイムスタンプ + stream タグ付き)。

```
tail -f /.sprite/logs/services/web.log
```

### この bot 用の service 作成例(uvicorn)

```
sprite-env services create slackbot \
  --cmd uv \
  --args "run,uvicorn,tribunal.entrypoints.slack:app,--host,0.0.0.0,--port,8080" \
  --dir /home/sprite/tribunal \
  --env "SLACK_BOT_TOKEN=xoxb-...,SLACK_SIGNING_SECRET=..." \
  --http-port 8080
```

- ⚠️ 注意1: `--cmd` は**バイナリのみ**。`uv` が PATH 上のバイナリとして解決できる前提(通常 `~/.local/bin/uv`)。解決できない場合は絶対パス(例 `--cmd /home/sprite/.local/bin/uv`)を指定。
- ⚠️ 注意2: `--args` はカンマ区切り。**引数値自体にカンマを含めない**こと(secrets はコンマ含まないトークンなので `--env` 側も要注意 → 9章参照)。
- ⚠️ 注意3: `--host 0.0.0.0` は必須(Sprite URL からの内部ルーティングを受けるため)。

出典: https://docs.sprites.dev/concepts/services/ , https://docs.sprites.dev/keeping-sprites-running/

---

## 4. Networking / 公開 URL

### ポート公開と URL 認証

```
sprite config update --url-auth public   # 誰でもアクセス可(認証なし)
sprite config update --url-auth sprite   # 既定: org メンバーのみ
```

- **既定は private (`sprite`)**: org メンバー(ブラウザ / org トークン)のみ到達可能。
- **public** にすると URL を知る誰でもアクセスできる(**認証なし**)。
- ⚠️ セキュリティ: 公式も「secrets / 内部エンドポイントを晒すなら public にするな。実運用なら前段に自前の認証を置け」と警告。**Slack bot の場合は、slack_bolt の署名検証 (`SLACK_SIGNING_SECRET`) が「自前の認証」に相当**するため public 化して問題ない。

### URL フォーマット

```
https://<sprite-name>-<org-id>.sprites.app/
```

- 正確な URL と認証設定は **`sprite info`** で確認できる。

### wake-on-request / Slack の inbound POST

- inbound HTTPS が Sprite URL に届くと、**Sprite が自動で wake** し、内部の HTTP サービス(= http-port の service)へルーティングされる。CLI 常駐不要。
- **Slack の Events API POST (`/slack/events`) が届くたびに Sprite が起きて処理する**。処理後アイドル 30 秒で再び warm に落ちる。
- ⚠️ wake レイテンシ考慮: warm 100–500ms / cold 1–2s。Slack の Events API は 3 秒以内の 200 応答を要求する。cold からでも 1–2s で wake するため通常は間に合うが、**slack_bolt は ack を即返す設計(`ack()` を先に呼ぶ / lazy listener)にしておくのが安全**。

### ポートフォワード(ローカル開発用)

```
sprite proxy 5432          # remote 5432 → localhost 5432
sprite proxy 3001:3000     # localhost 3001 → remote 3000
sprite proxy 3000 8080 5432  # 複数同時
```
`Ctrl+C` で停止。DB クライアントやブラウザからローカル接続したい時に使う(公開 URL とは別物)。

出典: https://docs.sprites.dev/concepts/networking/ , https://docs.sprites.dev/cli/commands/

---

## 5. Checkpoints

- **Git のバージョン管理ではない**。「環境の状態(セットアップ・設定・周辺の可動部)の高速な undo ポイント」。危険な操作の前に作る**任意のセーフティネット**。
- **ディスク永続には不要**(2 章参照)。ディスク状態は自動で pause を跨いで保持される。checkpoint は「手動の巻き戻しポイント」。

### capture するもの / しないもの

- **含む**: ファイル/ディレクトリ、インストール済みパッケージ、config/dotfiles、ディスク上の DB(SQLite 等)。
- **含まない**: 実行中プロセス、インメモリ状態、開いている接続。(= ディスク境界と同じ原則)

### コマンド

```
sprite checkpoint create --comment "説明"
sprite checkpoint list --include-auto      # auto- 付き自動 checkpoint も表示
sprite checkpoint info [checkpoint-id]
sprite restore v1                          # または sprite checkpoint restore v1
sprite checkpoint delete [checkpoint-id]
```

- **自動 checkpoint**: バックグラウンドで作成され `auto-` プレフィックス付き(手動の `v0`, `v1`... 番号は消費しない)。既定では非表示。「セーフティネットであってプランではない」。
- **Sprite 内部から**(agent など)は `sprite-env` 経由でも可:
  ```
  sprite-env checkpoints create --comment "label"
  sprite-env checkpoints restore v4
  ```

⚠️ CLI 表記ゆれ: 外部 CLI は `sprite checkpoint`(単数)、Sprite 内部は `sprite-env checkpoints`(複数)。ドキュメント間で混在しているため、実機で `--help` 確認推奨。

出典: https://docs.sprites.dev/concepts/checkpoints/ , https://docs.sprites.dev/sprite-maintenance/

---

## 6. CLI リファレンス

### インストール

```bash
# 推奨(OS/arch 自動判定、~/.local/bin へ)
curl -fsSL https://sprites.dev/install.sh | sh
sprite --help          # 確認
sprite upgrade         # アップグレード
```

手動インストール(v0.0.1-rc47)は `https://sprites-binaries.t3.storage.dev/client/v0.0.1-rc47/sprite-<os>-<arch>.tar.gz` から。macOS ARM は `sprite-darwin-arm64.tar.gz`。

### 認証(トークン)

```bash
sprite org auth                          # ブラウザで Fly.io ログイン
sprite org list                          # セッション確認
sprite org auth --org my-team            # 追加 org
sprite -o my-team list                   # org 切替(一時)
sprite org logout --org my-team          # 単一 org ログアウト
sprite logout                            # 全削除
```

**CI / 非対話環境:**
```bash
sprite auth setup --token "my-org/token-id/secret"
```
トークンは `sprites.dev/account` で発行し、CI シークレットに保存。

**環境変数:**
- `SPRITE_ORG` — デフォルト org
- `SPRITES_API_URL` — API エンドポイント上書き

トークンは既定でシステムキーリングに保存。`sprite org keyring disable` でファイル(`~/.sprites/sprites.json`)保存に切替。

### 主要コマンド表

| コマンド | 構文 | 用途 |
|----------|------|------|
| create | `sprite create [name]` | Sprite 作成 |
| use | `sprite use <name>` | カレントディレクトリの `.sprite` にアクティブ Sprite を設定 |
| list (ls) | `sprite list [--prefix <p>]` | 一覧 |
| destroy | `sprite destroy -s <name>` | 削除(不可逆) |
| exec (x) | `sprite exec [--tty] [--env ...] -- <cmd>` | コマンド実行(完了までブロック、stdout/stderr 返す) |
| console (c) | `sprite console` | 対話シェル(TTY) |
| info | `sprite info` | URL・認証設定表示 |
| config update | `sprite config update --url-auth public\|sprite` | URL 認証切替 |
| proxy | `sprite proxy <port>[:<local>] ...` | ローカルポートフォワード |
| checkpoint create | `sprite checkpoint create [--comment ...]` | チェックポイント作成 |
| checkpoint list | `sprite checkpoint list [--include-auto]` | 一覧 |
| restore | `sprite restore <version-id>` | 復元 |
| sessions (s) | `sprite sessions list\|attach <id>\|kill <id>` | detach 可能セッション管理 |
| org auth | `sprite org auth [--org <org>]` | 認証 |
| upgrade | `sprite upgrade` | CLI 更新 |

### exec の補足

- `sprite exec -- <cmd>` は完了までブロックし stdout/stderr を返す。
- `sprite exec --tty -- <cmd>` は detach 可能セッション。`Ctrl+\` で detach、`sprite sessions attach <id>` で再接続。
- **リッスンしたポートは既定で自動フォワード**される。`--no-port-forward` で無効化。
- ⚠️ `sprite exec --env` の**正確なフラグ書式はドキュメントに明記なし**(「environment variable support」とのみ)。実機で `sprite exec --help` を確認すること。

出典: https://docs.sprites.dev/cli/installation/ , https://docs.sprites.dev/cli/authentication/ , https://docs.sprites.dev/cli/commands/ , https://docs.sprites.dev/working-with-sprites/

---

## 7. API リファレンス(要点)

自動化に関係する主なエンドポイント/ソケット:

- **Services (外部 REST)**: `/v1/sprites/{name}/services` — fleet プロビジョニング用。SDK あり。
- **Sprite 削除**: `DELETE /v1/sprites/{name}`
- **Tasks API(Sprite 内部、管理ソケット経由)**: Unix ソケット `/.sprite/api.sock`、仮想ホスト `sprite`。
  - `POST http://sprite/v1/tasks -d '{ "name": "...", "expire": "1h" }'` 作成
  - `PUT http://sprite/v1/tasks/<name> -d '{ "expire": "1h" }'` 更新(heartbeat)
  - `DELETE http://sprite/v1/tasks/<name>` 削除
  - `GET http://sprite/v1/tasks` 一覧
  - expire は秒(整数)または `"30m"`/`"1h"`。**1 回あたり最大 1 時間**。長時間はリフレッシュ必須。
  - ⚠️ **この bot には Tasks API は不要**(inbound 駆動なので Service だけで足りる)。外向き接続を保持する必要が出たら使う。
- **Connectors ゲートウェイ**: `https://api.sprites.dev/v1/gateway/<provider>/<connection_id>/<path>` — org に保存した資格情報経由で API を呼ぶ(GitHub OAuth / OpenRouter / カスタム API)。deny-by-default のアクセスポリシー。
- **exec / checkpoints / network policy** も Sprite 環境 API から利用可能(MCP はこれらをラップ、8 章参照)。
- API ホストは `https://api.sprites.dev`(MCP の `https://sprites.dev/mcp` とは別)。

⚠️ 曖昧: 個々の REST エンドポイントの完全なリクエスト/レスポンススキーマ(exec, ports/proxy, filesystem)は公式の「API reference」ページに委譲されており、今回クロールした概念ページには詳細スキーマが載っていない。自動化で厳密な形が要る場合は公式 API reference を参照。

出典: https://docs.sprites.dev/keeping-sprites-running/ , https://docs.sprites.dev/concepts/services/ , https://docs.sprites.dev/concepts/connectors/ , https://docs.sprites.dev/integrations/claude-managed-agents/

---

## 8. Remote MCP 連携

- **MCP サーバ URL: `https://sprites.dev/mcp`**(REST の `api.sprites.dev` とは別)。
- **設定**: MCP クライアント(Claude 等)の connector 設定で remote/custom MCP を追加 → URL 入力 → Fly.io で OAuth → 対象 org 選択 → トークン制約を承認。
- **認証**: Fly.io OAuth。既定トークンは**名前が `mcp-` で始まる Sprite の作成に制限**され、作成数上限あり。セットアップ時に prefix 変更・上限調整・org 全権限化が可能。

### 公開ツール(CLI/API に対応)

**org レベル:**
- `list_sprites`(read-only)
- `create_sprite`(破壊的)
- `destroy_sprite`(破壊的)

**Sprite レベル**(Sprite 環境 API から生成):
- Exec: コマンド実行 / セッション一覧 / セッション kill
- Checkpoints: create / list / inspect / restore
- Network policy: outbound ルールの read / update
- Services: list / create / start / stop / inspect
- Service logs: 直近ログ取得

→ このセッションで利用可能な MCP ツール名(実際に露出しているもの): `list_sprites`, `create_sprite`, `destroy_sprite`, `exec`, `exec_list`, `exec_kill`, `service_create`, `service_get`, `service_list`, `service_start`, `service_stop`, `service_logs`, `checkpoint_create`, `checkpoint_get`, `checkpoint_list`, `checkpoint_restore`, `policy_network_get`, `policy_network_update`。

- **CLI/API との関係**: MCP は API reference にある機能を薄くラップしたもの。厳密なスキーマ/SDK/直接 REST が要るなら API reference を見る。
- ⚠️ 破壊的操作(削除・データ変更・checkpoint restore による巻き戻し・network policy 変更)は実影響があるので承認範囲に注意。

出典: https://docs.sprites.dev/integrations/remote-mcp/ , https://docs.sprites.dev/integrations/claude-managed-agents/

---

## 9. env / secret の扱い

- **exec で渡す**: `sprite exec --env ... -- <cmd>`(⚠️ 正確な書式は要 `--help` 確認、6 章参照)。one-off コマンドに一時的に渡す用途。
- **service で渡す**: `--env "K=v,K2=v2"`(**カンマ区切り**)。service プロセスの環境に入る。
- ⚠️ **カンマ問題**: `--env` はカンマ区切りのため、値自体にカンマを含むと壊れる。`SLACK_BOT_TOKEN` / `SLACK_SIGNING_SECRET` は通常カンマを含まないので概ね安全だが、任意値には注意。回避策として **`--dir` 配下に `.env` を置き、アプリ側(python-dotenv 等)で読み込む**方が堅牢(⚠️ これは推奨プラクティスであって Sprites 固有機能ではない)。
- **専用のシークレット vault は無い**。env は普通の環境変数として扱われる。
- ⚠️ **永続化の落とし穴**: env で渡した値や `.env` ファイルは **checkpoint / ディスクスナップショットの状態に含まれる**(ディスクに書いたものは snapshot に入るため)。secrets が checkpoint に残る点を認識しておくこと。ローテーション時は checkpoint も見直す。
- Managed Agents の実装では secrets を**プロセス引数ではなくファイル経由**で渡している(引数だと `ps` 等で見える)。同様に、**service の `--env` に長期 secret を直書きするより `.env` ファイル方式の方が漏洩面が小さい**。
- 組織横断で API 資格情報を安全に扱うなら **Connectors**(7・8 章)という選択肢もある(Slack トークンには非対応だが、GitHub 等の外部 API 呼び出しには有効)。

出典: https://docs.sprites.dev/concepts/services/ , https://docs.sprites.dev/concepts/checkpoints/ , https://docs.sprites.dev/integrations/claude-managed-agents/ , https://docs.sprites.dev/concepts/connectors/

---

## 10. この Slack bot を動かす手順(まとめ / runbook)

前提: ローカルに `sprite` CLI をインストール・認証済み(6 章)。リポジトリは git で clone できる状態。

```bash
# 1. Sprite 作成 & アクティブ化
sprite create tribunal
sprite use tribunal

# 2. リポジトリを clone(ディスクは永続するので exec でよい)
sprite exec -- bash -c "cd /home/sprite && git clone <REPO_URL> tribunal"

# 3. uv をインストール(未プリインストールの場合)
sprite exec -- bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
#    → uv は通常 ~/.local/bin/uv に入る

# 4. 依存を同期(結果は永続)
sprite exec -- bash -c "cd /home/sprite/tribunal && ~/.local/bin/uv sync"

# 5. uvicorn を常駐 service として作成(http-port 8080)
sprite-env services create slackbot \
  --cmd /home/sprite/.local/bin/uv \
  --args "run,uvicorn,tribunal.entrypoints.slack:app,--host,0.0.0.0,--port,8080" \
  --dir /home/sprite/tribunal \
  --env "SLACK_BOT_TOKEN=xoxb-...,SLACK_SIGNING_SECRET=..." \
  --http-port 8080
#    ⚠️ services create は Sprite 内で実行するコマンド。ローカルからは
#       `sprite exec -- sprite-env services create ...` の形にする(下記注記参照)。

# 6. URL を public に(slack_bolt の署名検証が前段認証になるため許容)
sprite config update --url-auth public

# 7. URL を取得
sprite info
#    → https://tribunal-<org-id>.sprites.app/

# 8. Slack アプリ設定で Request URL を設定
#    Event Subscriptions → Request URL:
#    https://tribunal-<org-id>.sprites.app/slack/events
#    (Slack の URL verification challenge に bot が応答する必要あり)

# 9. 動作確認
#    - Slack でメンション → inbound POST が Sprite を wake → 応答
#    - ログ確認:
sprite exec -- tail -n 50 /.sprite/logs/services/slackbot.log

# 10. sleep/wake 確認
#    - 30 秒放置で warm に落ちる
#    - 再度メンション → 100–500ms(warm)/ 1–2s(cold)で wake し応答
#    - service は cold wake でも自動再起動されるので手動操作不要
```

### 運用上の注意(この bot 固有)

- **service は 1 つだけ http-port を持てる** → 8080 を bot に割り当てればよい。
- **slack_bolt は即 ack する設計に**(wake レイテンシ + Slack の 3 秒制限対策)。lazy listener / `ack()` 先行。
- **quiet な service は Sprite を起こし続けない** → メンションが無い間は warm に落ちる=コスト最適。これは想定通りの挙動で問題なし。Tasks API は不要。
- **secrets は checkpoint に残る**(9 章)。ローテーション時は注意。
- ⚠️ 手順 5 の `sprite-env services create` は **Sprite 内部コマンド**。ローカルの `sprite` CLI から実行するには `sprite exec -- sprite-env services create ...` とラップするか、`sprite console` で入ってから実行する。ドキュメントでは `sprite-env services` と内部前提で書かれており、外部 CLI からの正確な呼び出し形は要検証(⚠️ 曖昧)。あるいは MCP の `service_create` / `service_start` を使うのが確実。

出典: 全ページ総合(特に §3, §4, §9)

---

## ⚠️ ドキュメントが曖昧/推測した点

- **`sprite exec --env` の正確なフラグ書式**が明記されていない(「environment variable support」のみ)。実機 `--help` 要確認。
- **`sprite-env services` を外部 CLI (`sprite`) からどう呼ぶか**が不明瞭。内部前提の記述。`sprite exec -- sprite-env ...` か MCP の `service_*` ツール利用が確実。
- **CLI 表記ゆれ**: `sprite checkpoint`(単数, 外部)vs `sprite-env checkpoints`(複数, 内部)。`sprite config update --url-auth` と `sprite url update` の関係も曖昧(commands ページに `sprite url [update]` の記載あり)。
- **REST API の詳細スキーマ**(exec / ports / filesystem)は概念ページに無く、公式 API reference に委譲。
- **`uv` / `uvicorn` がプリインストールか**は不明(Node/Python3/Go は確認済み)。上記 runbook では uv を明示インストールする前提にした。
- **アイドルタイムアウト 30 秒**は「about 30 seconds today」と将来変更含みの表現。
