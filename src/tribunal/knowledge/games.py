from pathlib import Path
from typing import Any

import yaml

from tribunal.domain.game import GameStores

DEFAULT_GAMES_FILE = Path("games/games.yaml")

STORE_KINDS = frozenset({"rule", "strategy"})


def load_game_stores(path: Path = DEFAULT_GAMES_FILE) -> dict[str, GameStores]:
    """games.yaml から game_id ごとの Store ID を読む。"""
    catalog = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {game["id"]: _stores_of(game) for game in catalog["games"]}


def _stores_of(game: dict[str, Any]) -> GameStores:
    stores = game.get("stores")
    if not isinstance(stores, dict):
        raise ValueError(f"{game['id']}: stores must be a mapping")
    if set(stores) != STORE_KINDS:
        raise ValueError(
            f"{game['id']}: stores must have exactly {sorted(STORE_KINDS)}, got {sorted(stores)}"
        )
    for kind, store_id in stores.items():
        if not isinstance(store_id, str):
            raise ValueError(f"{game['id']}: stores.{kind} must be a string")
    return GameStores(rule=stores["rule"], strategy=stores["strategy"])
