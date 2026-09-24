from pathlib import Path

import pytest

from tribunal.domain.game import Game, GameStores
from tribunal.knowledge.games import DEFAULT_GAMES_FILE, load_games

IDENTITY = "name: Catan\n    aliases: [カタン]\n    identifying_terms: [盗賊]"
STORES = "stores:\n      rule: vs_rule\n      strategy: ''"
CATAN = f"  - id: catan\n    {IDENTITY}\n    {STORES}\n"


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "games.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def _catalog(tmp_path: Path, game: str) -> Path:
    return _write(tmp_path, f"version: 1\ngames:\n{game}")


def test_reads_game(tmp_path: Path) -> None:
    path = _catalog(tmp_path, CATAN)

    assert load_games(path) == {
        "catan": Game(
            id="catan",
            name="Catan",
            aliases=("カタン",),
            identifying_terms=("盗賊",),
            stores=GameStores(rule="vs_rule", strategy=""),
        )
    }


def test_undeclared_game_keys_are_ignored(tmp_path: Path) -> None:
    path = _catalog(tmp_path, f"{CATAN}    editions:\n      - id: base\n")

    assert set(load_games(path)) == {"catan"}


@pytest.mark.parametrize(
    "stores",
    [
        "",
        "stores:",
        "stores:\n      rule: vs_rule",
        "stores:\n      rule: vs_rule\n      strategy: null",
        "stores:\n      rule: vs_rule\n      strategy: 1",
        "stores:\n      rule: vs_rule\n      strategy: ''\n      supply: vs_supply",
    ],
    ids=["no-stores", "null-stores", "missing-kind", "null-value", "non-string", "unknown-kind"],
)
def test_invalid_stores_are_rejected(tmp_path: Path, stores: str) -> None:
    path = _catalog(tmp_path, f"  - id: catan\n    {IDENTITY}\n    {stores}\n")

    with pytest.raises(ValueError):
        load_games(path)


@pytest.mark.parametrize(
    "identity",
    [
        "aliases: []\n    identifying_terms: []",
        "name: ''\n    aliases: []\n    identifying_terms: []",
        "name: Catan\n    identifying_terms: []",
        "name: Catan\n    aliases: null\n    identifying_terms: []",
        "name: Catan\n    aliases: [1]\n    identifying_terms: []",
    ],
    ids=["no-name", "empty-name", "no-aliases", "null-aliases", "non-string-alias"],
)
def test_invalid_identity_is_rejected(tmp_path: Path, identity: str) -> None:
    path = _catalog(tmp_path, f"  - id: catan\n    {identity}\n    {STORES}\n")

    with pytest.raises(ValueError):
        load_games(path)


@pytest.mark.parametrize(
    "header",
    ["games:\n", "version: 2\ngames:\n", "version: 1\nunknown: x\ngames:\n"],
    ids=["no-version", "unknown-version", "unknown-top-level-key"],
)
def test_invalid_top_level_is_rejected(tmp_path: Path, header: str) -> None:
    path = _write(tmp_path, f"{header}{CATAN}")

    with pytest.raises(ValueError):
        load_games(path)


def test_duplicated_game_id_is_rejected(tmp_path: Path) -> None:
    path = _catalog(tmp_path, CATAN + CATAN)

    with pytest.raises(ValueError, match="duplicated game id"):
        load_games(path)


def test_repository_catalog_loads() -> None:
    assert load_games(Path(__file__).parents[1] / DEFAULT_GAMES_FILE)
