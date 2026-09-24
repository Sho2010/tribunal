# tribunal

Slack からボードゲームのルール / 戦略を質問できる RAG chatbot。Rule については厳密な裁定者、Strategy については根拠を持った分析者として振る舞うことを目指す。

## Dependencies

- [sprite](https://docs.sprites.dev/cli/installation/) - sprites.dev CLI
- [rclone](https://github.com/rclone/rclone)
- uv

### PDFの下処理（`scripts/rag-preprocess/`）:

- [ocrmypdf](https://github.com/ocrmypdf/ocrmypdf) - tesseract の日本語データ（`jpn`）も要る
- [docling](https://docling.ai/) - `uv tool install docling` で入れる。`docling-markdown.sh` は同じ環境の `python` を使う
- [poppler](https://poppler.freedesktop.org/) - `pdffonts` / `pdftoppm` / `pdftotext`
- [qpdf](https://github.com/qpdf/qpdf)
- [mupdf-tools](https://mupdf.com/) - `mutool`

## Environment Variables

| Name | Description | Example |
| --- | --- | --- |
| `SLACK_BOT_TOKEN` | (required) Slack App の Bot User OAuth Token | `xoxb-your-bot-token` |
| `SLACK_SIGNING_SECRET` | (required) Slack リクエストの署名検証 | `your-signing-secret` |
| `OPENAI_API_KEY` | (required) OpenAI API key | `sk-your-api-key` |
| `TRIBUNAL_MODEL` | (optional) 回答生成に使うモデル。省略時は `gpt-5` | `gpt-5` |

Vector Store ID は env ではなく `games/games.yaml` の各ゲームの `stores` に書く。

```yaml
- id: nusfjord
  stores:
    rule: vs_xxx       # null のゲームには回答しない。1 つも無ければ起動に失敗する
    strategy: null     # null なら戦略の質問に「未整備」と返す（rule Store では代替しない）
```

登録ゲーム（rule が設定されたゲーム）が 1 つならそのゲームとして答える。
複数あるときは、ゲームを特定する手段がまだ無いため回答できない。

### PDFの下処理（`scripts/rag-preprocess/`）:

| Name | Description | Example |
| --- | --- | --- |
| `TRIBUNAL_ANTHROPIC_API_KEY` | required when `claude`, Anthropic API key | `sk-ant-your-api-key` |
| `OPENAI_API_KEY` | required when `openai` OpenAI API key | `sk-your-api-key` |
| `TRIBUNAL_CLAUDE_MODEL` | (optional) 省略時は `claude-opus-5` | `claude-opus-5` |
| `TRIBUNAL_LLM` | (required) 照合に使う LLM。`claude` または `openai` | `claude` |
| `TRIBUNAL_OPENAI_MODEL` | (optional) 省略時は `gpt-5` | `gpt-5` |


### trivia

- [The Six Hammers](https://wiki.project1999.com/The_Tribunal)
