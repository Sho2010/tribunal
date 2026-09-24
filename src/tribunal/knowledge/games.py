from pathlib import Path
from typing import Any

import yaml

from tribunal.domain.game import Game, GameStores

DEFAULT_GAMES_FILE = Path("games/games.yaml")

STORE_KINDS = frozenset({"rule", "strategy"})


def load_games(path: Path = DEFAULT_GAMES_FILE) -> dict[str, Game]:
    """games.yaml から game_id ごとの Game を読む。"""
    catalog = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {game["id"]: _game_of(game) for game in catalog["games"]}


def _game_of(game: dict[str, Any]) -> Game:
    name = game.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"{game['id']}: name must be a non-empty string")
    return Game(
        id=game["id"],
        name=name,
        aliases=_strings_of(game, "aliases"),
        identifying_terms=_strings_of(game, "identifying_terms"),
        stores=_stores_of(game),
    )


def _strings_of(game: dict[str, Any], key: str) -> tuple[str, ...]:
    values = game.get(key)
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        raise ValueError(f"{game['id']}: {key} must be a list of strings")
    return tuple(values)


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
