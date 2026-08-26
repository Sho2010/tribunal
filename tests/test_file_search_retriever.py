import pytest

from tribunal.infra.openai.file_search_retriever import FileSearchRetriever


def test_for_rule_and_for_strategy_read_separate_stores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("TRIBUNAL_RULE_VECTOR_STORE_ID", "vs_rule")
    monkeypatch.setenv("TRIBUNAL_STRATEGY_VECTOR_STORE_ID", "vs_strategy")

    assert FileSearchRetriever.for_rule("r")._vector_store_id == "vs_rule"
    assert FileSearchRetriever.for_strategy("s")._vector_store_id == "vs_strategy"


def test_for_strategy_requires_its_own_store_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strategy Store 未設定時に Rule Store へ fallback しない（arch §8 の trust boundary）。"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("TRIBUNAL_RULE_VECTOR_STORE_ID", "vs_rule")
    monkeypatch.delenv("TRIBUNAL_STRATEGY_VECTOR_STORE_ID", raising=False)

    with pytest.raises(KeyError):
        FileSearchRetriever.for_strategy("s")
