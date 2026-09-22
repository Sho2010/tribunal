# Sprites の pause と非同期処理 — Slack bot が「返事を返さない」問題

調査日: 2026-09-22 / 対象: Fly.io Sprites 上で動く slack_bolt bot（service 名 `tribunal`）

## 要約

**Sprites の service は、処理中であっても Sprite を起きたままにしない。**
Slack の 3 秒 ack を lazy listener で回避しても、ack 後に走る回答生成が 30 秒ほどで
pause に巻き込まれ、プロセスごと凍結する。次に何かが Sprite を起こすまで回答は投稿されない。

**対策は Tasks API。** 処理中だけ task を登録して pause を止める。
実測で 150 秒の処理が中断なく完走することを確認した。

## 症状

Slack で mention しても回答が返らない。あるいは数分〜数十分遅れて返る。
service は `running` のままで、エラーログも出ない。

紛らわしいのは **`sprite exec` でログを見に行くと動き出す**こと。
調査するたびに wake させてしまうので、「遅いけど動いている」ようにしか見えない。

## 原因

Fly.io スタッフ（bglw）による「アクティブ」の定義:

> "Activity" here means an attached session, a command run through `exec` that is producing
> logs, or network requests to proxied ports or the public url.

そして:

> **services won't prevent the Sprite from sleeping**

lazy listener が OpenAI のレスポンスを待っている間、Sprite から見た状態はこうなる。

- inbound request は既に完了している（ack 200 を返し終わっている）
- 動いているのは service 内のスレッドだけ → **カウントされない**
- pause。OpenAI 待ちのまま凍結

公式ドキュメントは service と task の関係をこう説明している。

> A Service is a long-running process managed by the Sprite runtime: it auto-starts on boot,
> keeps running through a warm wake (the process is frozen, not terminated), and restarts
> automatically on a cold wake. Tasks keep the current run alive. They compose: a Service
> launches the agent, the agent registers a task while it's working.

## 3 秒 ack 自体は問題ない

切り分けとして重要な点。**Slack の 3 秒ルールには一度も引っかかっていない。**

- ack は 2〜7ms で返っている
- リトライ（`X-Slack-Retry-Num`）は全期間でゼロ。
  現状 retry を弾く実装がないので、来ていれば重複投稿として現れるはずだが痕跡がない
- Sprite の wake は HTTP レイヤの手前で吸収され、uvicorn から見ると常に warm

**入口（ack）は Sprites が守ってくれるが、出口（ack 後の非同期処理）は守られない。**

## 実測

検証用に `/debug/probe?sec=N` を用意した。ack を即返し、裏のスレッドが 1 秒ごとに
「経過した wall clock と monotonic」を記録する。ループが 1 周するのにかかった時間を見れば、
凍結していた区間が分かる。

### 1. 何もしない — 38 秒で pause

```
tick=38  20:54:15.487  wall=38.0s   mono=38.0s
tick=39  20:58:05.355  wall=267.9s  mono=267.9s   ← exec を打った 0.9 秒後
```

1 秒のループが 1 周するのに 230 秒かかっている。
`exec`（20:58:04.439）の **0.9 秒後**に再開しているので、wake で動き出したことが分かる。

### 2. 外部から 20 秒おきに GET — ほぼ無意味

```
21:02:19 tick=1   wall=5.8
21:02:41 tick=2   wall=27.1   (+21.3s)
21:03:02 tick=3   wall=48.7   (+21.6s)
21:03:24 tick=4   wall=70.4   (+21.7s)
```

keep-alive の間隔（20 秒）と tick 間隔（21 秒）が一致する。
**1 リクエストにつき 1 tick しか進まない。** つまり inbound request は「その瞬間だけ起こす」もので、
30 秒の猶予を与えるわけではない。この方式では 150 秒の処理に 50 分以上かかる。

### 3. 接続を開いたまま — 効くが脆い

`/debug/hold?sec=150` で接続を保持したまま probe を回すと、
120 秒の処理が `wall=120.1s` で完走した（tick が 1 秒刻みで連続）。

ただし公式は接続方式を推奨していない。

> Open TCP connections drop on the pause, even on warm.

一度でも pause すれば接続は切れるので、切れた瞬間に無防備になる。

### 4. Tasks API — これが正解

```
21:17:33  task hold acquired: debug-task-probe
21:17:34  tick=1    wall=1.0s
   ...     （150 tick すべて 1 秒刻み、空白なし）
21:20:03  tick=150  wall=150.1s
21:20:03  done seconds=150
```

起動後 3 分半、外から一切触れずに完走した。

## monotonic は pause を検知できない

設計上の注意点。`wall` と `mono` が**常に一致**していた。

```
tick=39  wall=267.9s  mono=267.9s
```

`CLOCK_MONOTONIC` は suspend 中に止まると予想していたが、実際は進んでいる。
Sprites の pause がプロセスの SIGSTOP ではなく VM ごとのサスペンド/復元で、
復元時に時計が現実時間へ同期されるため。

**アプリ側から「自分が凍結されていた」ことを時計で検知できない。**
`time.monotonic()` による経過時間の判定は、pause 中の時間を素通りで加算する。
タイムアウト判定を monotonic に頼っている箇所は、pause をタイムアウトと誤認する。

## Tasks API

`/.sprite/api.sock`（unix domain socket）上の HTTP/JSON。TCP では listen していない。

```
POST   /v1/tasks            {"name":"...","expire":"5m"}  → 201（名前が衝突すると 409）
PUT    /v1/tasks/<name>     {"expire":"5m"}               → 200（延長）
GET    /v1/tasks                                          → 一覧
DELETE /v1/tasks/<name>                                   → 204
```

- **`expire` の上限は 1 時間。** それ以上保持するには PUT で延長し続ける
- task が 1 つでも live なら Sprite は pause しない
- プロセスが落ちても expire で自動解放される

Sprite 内部からしか叩けない（public REST API には task のエンドポイントがない）ので、
**外部から寝ている Sprite を起こす用途には使えない**。起こすのは inbound request の役割。

### hold は ack ハンドラで取る（重要）

**lazy listener の中で hold を取っても間に合わない。**

```
app_mention received  22:06:47.278
task hold acquired    22:07:27.373   ← 40 秒後（exec で起こすまで凍結）
```

ack を返し終えると inbound request が切れた扱いになり、その時点から idle の計測が始まる。
lazy listener は ack の後に動くので、socket に繋ぐ前に pause に入りうる。

**ack ハンドラの中（inbound request が生きている間）で取る。**

```python
def ack_and_hold(ack: Ack, event: dict[str, Any]) -> None:
    task_hold.acquire(_hold_name(event))
    ack()


bolt_app.event("app_mention")(ack=ack_and_hold, lazy=[respond_to_mention])
```

解放は lazy listener の `finally`。ack と lazy は別文脈なので、context manager ではなく
`acquire()` / `release()` に分けている。

### 実装

`src/tribunal/infra/sprites/task_hold.py`。

- `expire=300` で登録し、60 秒ごとに PUT で延長
- **task 名は `[a-z0-9-]` のみ。** Slack の `thread_ts`（`1790113918.270029`）は
  ドットを含むので、そのまま渡すと `400 task name must contain only lowercase letters,
  numbers, and dashes`。`sanitize_name()` で置換する
- **409 は成功扱い。** 同じ thread への重複配信で、既にある hold をそのまま使う
- **Tasks API の呼び出しを 1 本のロックで直列化する。** DELETE が登録中の POST を
  追い越すと、消したはずの task が残って expire まで課金が続く
- **PUT が 404 なら POST で再登録する。** cold boot と spritesd の再起動で task は消える
- **Sprites 以外では no-op** — socket が無ければ素通りする（ローカル開発・test で壊れない）

### 実測（対策後）

```
22:19:31.412  app_mention received
22:19:31.414  POST /slack/events 200 OK        ← ack 2ms
22:19:31.418  task hold acquired                ← 6ms
22:19:31.761  accepted reply posted in 0.35s
22:20:20.852  OpenAI 200 OK                     ← 49 秒の生成が中断なく完走
22:20:21.456  answer generated: 2317 chars
22:20:48.101  task hold released
```

`say()` は 0.35 秒。受付メッセージが遅く見えていたのは `say()` が遅いのではなく、
その手前で pause していたため。

### 残っているレース

**ack を返してから task を登録するまでの窓は、仕様上は保証されていない。**
ドキュメントにもスタッフ発言にも順序・原子性の記述がなく、
「task を登録したのに pause した」という報告も見つからない。

実用上の余裕は大きい。idle の窓が約 30 秒あるのに対し、登録は unix socket への
POST で実測 6ms。ただし構造的にレースであることは変わらない。

消したい場合は、リクエストごとに登録するのをやめて
**supervisor が長命の lease を 1 本持つ**形にする（進行中の仕事を数え、
0 になったら失効させる）。コミュニティの実装はすべてこの形を採っている。

## cron / scheduled wakeup は存在しない

[wishlist スレッド](https://community.fly.io/t/sprite-cron-scheduled-wakeup/26829) はスタッフの
応答がないまま自動クローズされた。`sprite config` のような idle timeout の設定コマンドも無い。

外部から定期的に起こす必要がある場合は、GitHub Actions や Fly の
[Cron Manager](https://github.com/fly-apps/cron-manager) など外部スケジューラから
public URL を叩く。ただし **mention で起きる用途では不要**。

## 公式 Slack bot 記事はこの問題を扱っていない

[Slack Bots on Sprites](https://fly.io/sprites-blog/slack-bots-on-sprites/) は OAuth と
トークン保存の話のみで、ack 後の非同期処理が pause で止まる点への言及がない。
例が即応答する slash command なので、この落とし穴を踏まない。

## 調査中に踏んだ落とし穴

**ログのフラッシュが遅れる。** 最終行が数分遅れて現れることがある。
tail した時点で止まって見えても、処理が失敗したとは限らない。

**`exec` するたびに wake する。** 調査行為そのものが対象の状態を変える。
「wake していないのでは」を検証したいなら `exec` を打ってはいけない、というジレンマがある。
手元の時計とログのタイムスタンプを突き合わせて回避した。

## 残っている宿題

- **回答生成そのものが遅い** — 実測でルール照会 45〜50 秒、戦略質問は 270 秒。
  出力量と経過時間が逆相関するので、生成ではなく `file_search` の探索が効いていそう
- **retrieval と生成の切り分け** — mention 受信と OpenAI 200 の 2 点しかログがないので、
  遅さの内訳（retrieval / 生成）が分からない
- **`chat.update`** — レイテンシ対策ではなく、
  `🎲 調べています…` と本回答が 2 投稿残る問題の解決として別途

## 参照

- [Keeping a Sprite Running (Tasks API)](https://docs.sprites.dev/keeping-sprites-running/)
- [Lifecycle and Persistence](https://docs.sprites.dev/concepts/lifecycle/)
- [Working with Sprites / Idle Detection](https://docs.sprites.dev/working-with-sprites/)
- [sprites not shutting off — Fly.io Community](https://community.fly.io/t/sprites-not-shutting-off/26793)
- [Sprite Cron / Scheduled wakeup?（wishlist）](https://community.fly.io/t/sprite-cron-scheduled-wakeup/26829)
- [Slack Bots on Sprites](https://fly.io/sprites-blog/slack-bots-on-sprites/)
