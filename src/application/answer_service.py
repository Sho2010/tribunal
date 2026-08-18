from src.domain.answer import Answer

FIXED_REPLY = "🎲 boardgame-ai は準備中です。もう少しお待ちください。"


class AnswerService:
    """Chat platform に依存しない問い合わせ処理（plan.md §3.2）。

    M1 では固定応答を返すスタブ。
    将来ここに retrieval（方針A: Vector Store なし・直接 file input）を実装する。
    Chat Adapter はこの ask() のみを利用し、OpenAI/SQLite/R2 を直接触らない。
    """

    def ask(self, question: str, *, game_id: str | None = None) -> Answer:
        return Answer(text=FIXED_REPLY)
