import os
from typing import Any

from openai import OpenAI
from openai.types.responses import FileSearchToolParam
from openai.types.shared_params import ComparisonFilter

from tribunal.domain.answer import Answer, Source

DEFAULT_MODEL = "gpt-5"
MAX_NUM_RESULTS = 20

RULE_STORE_ENV = "TRIBUNAL_RULE_VECTOR_STORE_ID"
STRATEGY_STORE_ENV = "TRIBUNAL_STRATEGY_VECTOR_STORE_ID"


class FileSearchRetriever:
    """Vector Store を File Search で引いて回答を生成する。"""

    def __init__(
        self,
        vector_store_id: str,
        instructions: str,
        *,
        client: OpenAI | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self._vector_store_id = vector_store_id
        self._instructions = instructions
        self._client = client or OpenAI()
        self._model = model

    @classmethod
    def for_rule(cls, instructions: str, *, client: OpenAI | None = None) -> "FileSearchRetriever":
        """Rule Store の retriever を env から組み立てる。"""
        return cls._from_env(RULE_STORE_ENV, instructions, client=client)

    @classmethod
    def for_strategy(
        cls, instructions: str, *, client: OpenAI | None = None
    ) -> "FileSearchRetriever":
        """Strategy Store の retriever を env から組み立てる。"""
        return cls._from_env(STRATEGY_STORE_ENV, instructions, client=client)

    @classmethod
    def _from_env(
        cls, store_env: str, instructions: str, *, client: OpenAI | None = None
    ) -> "FileSearchRetriever":
        # Store ID 未設定は KeyError にする。別 Store へ fallback すると Rule 資料で
        # strategy を答える（またはその逆）経路ができる。
        return cls(
            os.environ[store_env],
            instructions,
            client=client,
            model=os.environ.get("TRIBUNAL_MODEL", DEFAULT_MODEL),
        )

    def answer(self, question: str, *, game_id: str | None = None) -> Answer:
        tool = FileSearchToolParam(
            type="file_search",
            vector_store_ids=[self._vector_store_id],
            max_num_results=MAX_NUM_RESULTS,
        )
        if game_id is not None:
            tool["filters"] = ComparisonFilter(type="eq", key="game_id", value=game_id)

        response = self._client.responses.create(
            model=self._model,
            instructions=self._instructions,
            input=question,
            tools=[tool],
        )
        return Answer(text=response.output_text, sources=_sources_of(response))


def _sources_of(response: Any) -> list[Source]:
    """output text の file_citation annotation を Source に変換する（file_id で重複排除）。"""
    sources: dict[str, Source] = {}
    for item in response.output:
        for content in getattr(item, "content", None) or []:
            for annotation in getattr(content, "annotations", None) or []:
                if getattr(annotation, "type", None) != "file_citation":
                    continue
                sources.setdefault(
                    annotation.file_id,
                    Source(title=annotation.filename, uri=f"openai-file://{annotation.file_id}"),
                )
    return list(sources.values())
