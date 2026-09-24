from collections.abc import Mapping

from tribunal.domain.game import GameIdentity


class GameResolver:
    """質問文に含まれるゲーム名 / alias / identifying term から候補の game_id を返す。"""

    def __init__(self, identities: Mapping[str, GameIdentity]) -> None:
        self._identities = identities

    def candidates(self, question: str) -> list[str]:
        """名前か alias で当たればそれだけ、無ければ identifying term で当たったものを返す。"""
        text = question.lower()
        by_name = [
            game_id
            for game_id, identity in self._identities.items()
            if _contains_any(text, (identity.name, *identity.aliases))
        ]
        if by_name:
            return by_name
        return [
            game_id
            for game_id, identity in self._identities.items()
            if _contains_any(text, identity.identifying_terms)
        ]

    def name_of(self, game_id: str) -> str:
        identity = self._identities.get(game_id)
        return identity.name if identity else game_id


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word.lower() in text for word in words if word)
