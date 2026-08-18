import logging

# デフォルト起動対象（Slack 先行）。platform 別に動かすときは
# `src.entrypoints.slack:app` のように entrypoint を直接指定する。
from src.entrypoints.slack import app  # noqa: F401

logging.basicConfig(level=logging.INFO)
