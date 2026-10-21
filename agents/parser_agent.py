"""Log Parser Agent: raw CI log → redacted, line-referenced evidence.

A thin wrapper over the v0.2.6 parser (`app/ingestion`). It is deterministic
on purpose: the first stage of the graph should never depend on a model.
"""

from app.ingestion import parse_log
from app.schemas.logs import ParsedLog


class ParserAgent:
    def __init__(self, tail_lines: int = 15):
        self.tail_lines = tail_lines

    def run(self, log_text: str) -> ParsedLog:
        return parse_log(log_text, tail_lines=self.tail_lines)
