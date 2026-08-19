from dataclasses import dataclass, field


@dataclass
class Source:
    """回答の出典 / citation。M1 では未使用だが I/F を先に定義しておく。"""

    title: str
    uri: str


@dataclass
class Answer:
    """Chat platform 非依存の回答表現。"""

    text: str
    sources: list[Source] = field(default_factory=list)
