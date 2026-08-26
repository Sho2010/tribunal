"""Rule Store を単独で叩く動作確認スクリプト。

usage:
    uv run --env-file .env python tribunal_ask.py 'ノースフィヨルドの勝者を教えて' [game_id]
"""

import sys

from tribunal.application.rule.protocol import adjudicator_prompt
from tribunal.infra.openai.file_search_retriever import FileSearchRetriever


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2

    question = sys.argv[1]
    game_id = sys.argv[2] if len(sys.argv) > 2 else None

    retriever = FileSearchRetriever.for_rule(adjudicator_prompt())
    print(f"question: {question!r}  game_id: {game_id!r}")
    print("=" * 60)

    answer = retriever.answer(question, game_id=game_id)

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
