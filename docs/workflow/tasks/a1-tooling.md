# A1 (残り): lint / format / type check / test

worktree: `../tribunal-a1-tooling` / branch: `a1-tooling`（作成済み）

## スコープ

tasks.md A1 のうち、Python プロジェクト作成・ディレクトリ骨組み・Sprites 最小構成は済んでいる。
**残りは lint / format / type check / test の導入**。

このタスクの成果物は全 worktree に効くので、**A1 をマージしてから A2 / B / C を切る**（branching.md）。

## 現状

- `pyproject.toml` に dev 依存も tool 設定も無い（`[project]` / `[build-system]` / `[tool.hatch...]` のみ）
- `tests/` ディレクトリ無し
- `.github/workflows/` 無し
- 既存コードは 12 ファイル。`src/tribunal/{domain,application,adapters/slack,entrypoints}` + `app_factory.py` + `main.py`

## やること

1. **dev 依存を `[dependency-groups]` の `dev` に入れる**（uv のネイティブな置き場所。`[project.optional-dependencies]` ではない）
2. **lint / format** — ruff 1 つで両方賄う
3. **type check** — mypy。strict で始める。コード量が少ない今なら通せる
4. **test** — pytest。最低限のスモークテストを書く
5. **CI** — GitHub Actions で lint / typecheck / test を回す
6. **README か CLAUDE.md にコマンドを追記**（CLAUDE.md の「テスト / lint / formatter はまだ導入されていない」という記述を実態に合わせる）

## 判断が要るところ

以下は arch doc に書かれていないので、**自分で決めて PR 本文に理由を書く**（confirm 不要）。

- **mypy を strict にするか。** slack_bolt は型スタブを同梱しないので `ignore_missing_imports` の
  override が要る。全体を緩めるのではなく module 単位で許容する
- **ruff の rule set。** 最低でも `E` / `F` / `I`（isort）。レイヤ規約（arch §38）を守らせたいので
  相対 import 禁止（`TID252`）は検討の価値がある
- **line-length。** 既存コードに合わせる
- **テストで何を検証するか。** 意味のあるスモークとして:
  - `create_app(["slack"])` が `/` health を返す
  - `create_app(["unknown"])` が `ValueError`
  - `AnswerService.ask()` が `Answer` を返す
  - `_strip_mention()` が `<@U123>` を落とす
  
  ただし **`adapters/slack/app.py` は import 時に `os.environ["SLACK_BOT_TOKEN"]` を読む**（CLAUDE.md
  に明記）。テストで環境変数を用意するか、この設計自体を直すかは判断して PR に書く。**直す場合は
  app_factory の遅延 import の意図（有効化していない platform の env を要求しない）を壊さないこと**

## 完了条件

- `uv run ruff check .` / `uv run ruff format --check .` / `uv run mypy` / `uv run pytest` が全部通る
- CI で同じものが回る
- CLAUDE.md のコマンド節が実態と一致している

## 参照

- arch §38（ディレクトリ構成、レイヤの依存方向、port を切るのは retrieval だけ）
- CLAUDE.md「コマンド」節
