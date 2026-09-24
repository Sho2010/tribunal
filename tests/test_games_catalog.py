from pathlib import Path

import pytest

from tribunal.domain.game import Game, GameStores
from tribunal.knowledge.games import DEFAULT_GAMES_FILE, load_games

IDENTITY = "name: Catan\n    aliases: [カタン]\n    identifying_terms: [盗賊]"
STORES = "stores:\n      rule: vs_rule\n      strategy: ''"


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "games.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_reads_game(tmp_path: Path) -> None:
    path = _write(tmp_path, f"games:\n  - id: catan\n    {IDENTITY}\n    {STORES}\n")

    assert load_games(path) == {
        "catan": Game(
            id="catan",
            name="Catan",
            aliases=("カタン",),
            identifying_terms=("盗賊",),
            stores=GameStores(rule="vs_rule", strategy=""),
        )
    }


@pytest.mark.parametrize(
    "stores",
    [
        "",
        "stores:",
        "stores:\n      rule: vs_rule",
        "stores:\n      rule: vs_rule\n      strategy: null",
        "stores:\n      rule: vs_rule\n      strategy: ''\n      supply: vs_supply",
    ],
    ids=["no-stores", "null-stores", "missing-kind", "null-value", "unknown-kind"],
)
def test_invalid_stores_are_rejected(tmp_path: Path, stores: str) -> None:
    path = _write(tmp_path, f"games:\n  - id: catan\n    {IDENTITY}\n    {stores}\n")

    with pytest.raises(ValueError):
        load_games(path)


@pytest.mark.parametrize(
    "identity",
    [
        "aliases: []\n    identifying_terms: []",
        "name: Catan\n    identifying_terms: []",
        "name: Catan\n    aliases: null\n    identifying_terms: []",
        "name: Catan\n    aliases: [1]\n    identifying_terms: []",
    ],
    ids=["no-name", "no-aliases", "null-aliases", "non-string-alias"],
)
def test_invalid_identity_is_rejected(tmp_path: Path, identity: str) -> None:
    path = _write(tmp_path, f"games:\n  - id: catan\n    {identity}\n    {STORES}\n")

    with pytest.raises(ValueError):
        load_games(path)


def test_repository_catalog_loads() -> None:
    assert load_games(Path(__file__).parents[1] / DEFAULT_GAMES_FILE)
