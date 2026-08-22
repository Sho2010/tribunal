import logging

# 後方互換シム。platform を選ぶなら tribunal.entrypoints.<platform>:app を直接指定する。
from tribunal.entrypoints.slack import app  # noqa: F401

logging.basicConfig(level=logging.INFO)
