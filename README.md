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
| `TRIBUNAL_RULE_VECTOR_STORE_ID` | (required) Rule Store の Vector Store ID | `vs_your-vector-store-id` |
| `TRIBUNAL_STRATEGY_VECTOR_STORE_ID` | (optional) Strategy Store の Vector Store ID。未設定なら Strategy 側の retriever を mount しない（Rule 側へ fallback はしない） | `vs_your-strategy-store-id` |
| `TRIBUNAL_MODEL` | (optional) 回答生成に使うモデル。省略時は `gpt-5` | `gpt-5` |

### PDFの下処理（`scripts/rag-preprocess/`）:

| Name | Description | Example |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | required when `claude`, Anthropic API key | `sk-ant-your-api-key` |
| `OPENAI_API_KEY` | required when `openai` OpenAI API key | `sk-your-api-key` |
| `TRIBUNAL_CLAUDE_MODEL` | (optional) 省略時は `claude-opus-5` | `claude-opus-5` |
| `TRIBUNAL_LLM` | (required) 照合に使う LLM。`claude` または `openai` | `claude` |
| `TRIBUNAL_OPENAI_MODEL` | (optional) 省略時は `gpt-5` | `gpt-5` |


### trivia

- [The Six Hammers](https://wiki.project1999.com/The_Tribunal)
