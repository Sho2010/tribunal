from dotenv import load_dotenv

# create_app() が env を読む。それより前に .env を読まないと KeyError。
load_dotenv()

from tribunal.app_factory import create_app  # noqa: E402

app = create_app(["slack"])
