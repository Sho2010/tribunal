from dataclasses import dataclass


@dataclass(frozen=True)
class GameStores:
    """ゲームごとの区分別 Vector Store ID。Store 未作成は空文字。"""

    rule: str
    strategy: str


@dataclass(frozen=True)
class GameIdentity:
    """質問からゲームを特定するための名前と語彙。"""

    name: str
    aliases: tuple[str, ...]
    identifying_terms: tuple[str, ...]
