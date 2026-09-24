from pathlib import Path

import pytest

from tribunal.domain.game import GameIdentity, GameStores
from tribunal.knowledge.games import DEFAULT_GAMES_FILE, load_game_identities, load_game_stores


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "games.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_reads_stores_per_game(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
games:
  - id: catan
    stores:
      rule: vs_rule
      strategy: ""
""",
    )

    assert load_game_stores(path) == {"catan": GameStores(rule="vs_rule", strategy="")}


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
    path = _write(tmp_path, f"games:\n  - id: catan\n    {stores}\n")

    with pytest.raises(ValueError):
        load_game_stores(path)


def test_repository_catalog_loads() -> None:
    assert load_game_stores(Path(__file__).parents[1] / DEFAULT_GAMES_FILE)


def test_reads_identity_per_game(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
games:
  - id: catan
    name: Catan
    aliases: [カタン]
    identifying_terms: [盗賊]
""",
    )

    assert load_game_identities(path) == {
        "catan": GameIdentity(name="Catan", aliases=("カタン",), identifying_terms=("盗賊",))
    }


@pytest.mark.parametrize(
    "body",
    [
        "aliases: []\n    identifying_terms: []",
        "name: Catan\n    identifying_terms: []",
        "name: Catan\n    aliases: null\n    identifying_terms: []",
        "name: Catan\n    aliases: [1]\n    identifying_terms: []",
    ],
    ids=["no-name", "no-aliases", "null-aliases", "non-string-alias"],
)
def test_invalid_identity_is_rejected(tmp_path: Path, body: str) -> None:
    path = _write(tmp_path, f"games:\n  - id: catan\n    {body}\n")

    with pytest.raises(ValueError):
        load_game_identities(path)


def test_repository_catalog_identities_load() -> None:
    assert load_game_identities(Path(__file__).parents[1] / DEFAULT_GAMES_FILE)
