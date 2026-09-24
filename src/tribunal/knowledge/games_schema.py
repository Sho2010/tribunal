# 生成物。直接編集しない。
# games/schema/games.schema.json を変えて `uv run datamodel-codegen` で再生成する。

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class Stores(BaseModel):
    """
    区分ごとの Vector Store ID。空文字は Store 未作成。キー欠落・null・未知の区分キーは不可。
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    rule: StrictStr
    strategy: StrictStr


class Game(BaseModel):
    """
    ゲーム 1 つ。宣言していないキー（editions など）は検証しない。
    """

    id: Annotated[StrictStr, Field(min_length=1)]
    name: Annotated[StrictStr, Field(min_length=1)]
    aliases: list[StrictStr]
    identifying_terms: list[StrictStr]
    stores: Stores


class Catalog(BaseModel):
    """
    games.yaml 全体。
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    version: Literal[1]
    games: list[Game]
