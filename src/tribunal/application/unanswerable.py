class Unanswerable(Exception):
    """回答を生成せずに、理由をユーザーへ返す。"""


class GameUnresolved(Unanswerable):
    """質問の対象ゲームを 1 つに決められない。"""


class RuleUnavailable(Unanswerable):
    """対象ゲームの Rule Store が設定されていない。"""


class StrategyUnavailable(Unanswerable):
    """そのゲームの Strategy Store が設定されていない。"""
