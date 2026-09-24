from dataclasses import dataclass


@dataclass(frozen=True)
class GameStores:
    """ゲームごとの区分別 Vector Store ID。未設定は空文字。"""

    rule: str = ""
    strategy: str = ""
