from types import SimpleNamespace
from typing import Any

from tribunal.infra.openai.file_search_retriever import FileSearchRetriever


class RecordingResponses:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        return SimpleNamespace(output_text="answer", output=[])


def test_answer_searches_the_given_store_only() -> None:
    responses = RecordingResponses()
    client: Any = SimpleNamespace(responses=responses)
    retriever = FileSearchRetriever("instructions", client=client, model="m")

    retriever.answer("q", vector_store_id="vs_rule")

    (tool,) = responses.kwargs["tools"]
    assert tool["vector_store_ids"] == ["vs_rule"]
    assert responses.kwargs["instructions"] == "instructions"
