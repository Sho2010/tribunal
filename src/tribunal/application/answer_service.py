from tribunal.domain.answer import Answer

FIXED_REPLY = "🎲 tribunal は準備中です。もう少しお待ちください。"


class AnswerService:
    """Chat platform に依存しない問い合わせ処理（docs の Query Orchestrator に相当）。

    M1 では固定応答を返すスタブ。
    将来ここに retrieval を実装する: Rule 質問は Rule Store を File Search で検索し、
    Rule Adjudicator Protocol（docs のアーキテクチャドキュメント §9）を通して裁定する。
    Chat Adapter はこの ask() のみを利用し、OpenAI/R2 を直接触らない。
    """

    def ask(self, question: str, *, game_id: str | None = None) -> Answer:
        return Answer(text=FIXED_REPLY)
