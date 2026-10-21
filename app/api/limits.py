"""Input checks shared by every endpoint that accepts a log."""

from app.config import Settings
from app.errors import EmptyLog, LogTooLarge


def check_log(log_text: str, settings: Settings) -> None:
    if not log_text.strip():
        raise EmptyLog("log_text must contain non-whitespace characters.")
    if len(log_text) > settings.max_log_chars:
        raise LogTooLarge(
            f"Log is {len(log_text):,} characters; the limit is {settings.max_log_chars:,}."
        )
