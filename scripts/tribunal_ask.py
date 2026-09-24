"""games.yaml にあるゲームの Rule Store を単独で叩く動作確認スクリプト。

usage:
    uv run --env-file .env python scripts/tribunal_ask.py 'ノースフィヨルドの勝者を教えて' nusfjord
"""

import sys

from tribunal.application.rule.protocol import adjudicator_prompt
from tribunal.infra.openai.file_search_retriever import FileSearchRetriever
from tribunal.knowledge.games import load_game_stores


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2

    question, game_id = sys.argv[1], sys.argv[2]
    store_id = load_game_stores()[game_id].rule
    if not store_id:
        print(f"{game_id}: rule store が未設定", file=sys.stderr)
        return 1

    retriever = FileSearchRetriever(adjudicator_prompt())
    print(f"question: {question!r}  game_id: {game_id!r}  store: {store_id}")
    print("=" * 60)

    answer = retriever.answer(question, vector_store_id=store_id)

    print(answer.text)
    print("-" * 60)
    if answer.sources:
        for source in answer.sources:
            print(f"  {source.title}  ({source.uri})")
    else:
        print("  (citation なし)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
