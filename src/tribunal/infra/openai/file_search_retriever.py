import os
from typing import Any

from openai import OpenAI
from openai.types.responses import FileSearchToolParam

from tribunal.domain.answer import Answer, Source

DEFAULT_MODEL = "gpt-5"
MAX_NUM_RESULTS = 20


class FileSearchRetriever:
    """Vector Store を File Search で引いて回答を生成する。"""

    def __init__(
        self,
        instructions: str,
        *,
        client: OpenAI | None = None,
        model: str | None = None,
    ) -> None:
        self._instructions = instructions
        self._client = client or OpenAI()
        self._model = model or os.environ.get("TRIBUNAL_MODEL", DEFAULT_MODEL)

    def answer(self, question: str, *, vector_store_id: str) -> Answer:
        tool = FileSearchToolParam(
            type="file_search",
            vector_store_ids=[vector_store_id],
            max_num_results=MAX_NUM_RESULTS,
        )
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
