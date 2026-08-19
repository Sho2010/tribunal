from dotenv import load_dotenv

# Slack adapter は import 時に環境変数を読むため、app 生成前に .env を読み込む（ローカル用）
load_dotenv()

from tribunal.app_factory import create_app  # noqa: E402

# uvicorn の起動対象: `uv run uvicorn tribunal.entrypoints.slack:app`
app = create_app(["slack"])
