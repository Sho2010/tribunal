from pathlib import Path

import yaml

from tribunal.domain.game import Game, GameStores
from tribunal.knowledge.games_schema import CatalogSchema, GameSchema

DEFAULT_GAMES_FILE = Path("games/games.yaml")


def load_games(path: Path = DEFAULT_GAMES_FILE) -> dict[str, Game]:
    """games.yaml を schema で検証し、game_id ごとの Game にする。"""
    catalog = CatalogSchema.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    # game id の一意性は JSON Schema で表現できない。
    ids = [game.id for game in catalog.games]
    duplicated = sorted({i for i in ids if ids.count(i) > 1})
    if duplicated:
        raise ValueError(f"duplicated game id: {duplicated}")
    return {game.id: _to_domain(game) for game in catalog.games}


def _to_domain(game: GameSchema) -> Game:
    return Game(
        id=game.id,
        name=game.name,
        aliases=tuple(game.aliases),
        identifying_terms=tuple(game.identifying_terms),
        stores=GameStores(rule=game.stores.rule, strategy=game.stores.strategy),
    )
