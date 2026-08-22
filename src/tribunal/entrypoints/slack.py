from dotenv import load_dotenv

# Slack adapter は import 時に env を読む。この import より前に .env を読まないと KeyError。
load_dotenv()

from tribunal.app_factory import create_app  # noqa: E402

app = create_app(["slack"])
