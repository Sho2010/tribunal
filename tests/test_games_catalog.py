from pathlib import Path

import pytest

from tribunal.domain.game import GameStores
from tribunal.knowledge.games import DEFAULT_GAMES_FILE, load_game_stores


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
      strategy: null
  - id: agricola
""",
    )

    assert load_game_stores(path) == {
        "catan": GameStores(rule="vs_rule"),
        "agricola": GameStores(),
    }


def test_unknown_store_kind_is_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
games:
  - id: dominion
    stores:
      rule: vs_rule
      supply: vs_supply
""",
    )

    with pytest.raises(ValueError, match="supply"):
        load_game_stores(path)


def test_repository_catalog_loads() -> None:
    assert load_game_stores(Path(__file__).parents[1] / DEFAULT_GAMES_FILE)
