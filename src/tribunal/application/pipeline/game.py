from collections.abc import Mapping
from typing import Protocol

from tribunal.application.unanswerable import GameUnresolved
from tribunal.domain.game import Game

GAME_UNRESOLVED = "どのゲームについての質問か特定できないため回答できません。"
GAME_AMBIGUOUS = (
    "どのゲームについての質問か特定できません（候補: {names}）。ゲーム名を添えて質問してください。"
)


class GameResolver(Protocol):
    """質問の対象ゲームを 1 つに決める。決められなければ GameUnresolved。"""

    def resolve(self, question: str, *, game_id: str | None = None) -> Game: ...


class CatalogGameResolver:
    """catalog のゲーム名 / alias / identifying term が質問文に含まれるかで決める。"""

    def __init__(self, games: Mapping[str, Game]) -> None:
        self._games = games

    def resolve(self, question: str, *, game_id: str | None = None) -> Game:
        if game_id is not None:
            game = self._games.get(game_id)
            if game is None:
                raise GameUnresolved(GAME_UNRESOLVED)
            return game

        candidates = self._candidates(question)
        if len(candidates) > 1:
            names = " / ".join(game.name for game in candidates)
            raise GameUnresolved(GAME_AMBIGUOUS.format(names=names))
        if candidates:
            return candidates[0]

        with_rule = [game for game in self._games.values() if game.stores.rule]
        if len(with_rule) != 1:
            raise GameUnresolved(GAME_UNRESOLVED)
        return with_rule[0]

    def _candidates(self, question: str) -> list[Game]:
        """名前か alias で当たればそれだけ、無ければ identifying term で当たったものを返す。"""
        text = question.lower()
        by_name = [
            game for game in self._games.values() if _contains_any(text, (game.name, *game.aliases))
        ]
        if by_name:
            return by_name
        return [
            game for game in self._games.values() if _contains_any(text, game.identifying_terms)
        ]


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word.lower() in text for word in words if word)
