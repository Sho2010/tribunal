import os
from typing import Any

from openai import OpenAI
from openai.types.responses import FileSearchToolParam
from openai.types.shared_params import ComparisonFilter

from tribunal.domain.answer import Answer, Source

DEFAULT_MODEL = "gpt-5"
MAX_NUM_RESULTS = 20


class OpenAIRuleRetriever:
    """Rule Store を File Search で引いて回答を生成する。"""

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
    def from_env(cls, instructions: str, *, client: OpenAI | None = None) -> "OpenAIRuleRetriever":
        """TRIBUNAL_RULE_VECTOR_STORE_ID / TRIBUNAL_MODEL から組み立てる。"""
        return cls(
            os.environ["TRIBUNAL_RULE_VECTOR_STORE_ID"],
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
