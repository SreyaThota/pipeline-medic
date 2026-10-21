"""Format detection and per-format line parsing.

Each parser turns raw (already redacted) lines into `RawLine`s: the line
number is always the 1-based position in the submitted text, so later stages
can cite evidence that points back at the exact original line.

Supported:
- github_actions: `gh run view --log-failed` output (`job<TAB>step<TAB>ts text`)
  and the raw per-job log downloaded from the Actions UI (`ts text`).
- jenkins: console output with `[Pipeline]` markers and optional
  Timestamper prefixes.
- text: anything else.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from app.schemas.logs import LogFormat

_ANSI = re.compile(r"(?:\x1b|\^\[)\[[0-9;]*[A-Za-z]")
_ISO_TS = re.compile(r"^﻿?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?Z ?")
_GH_COLUMNS = re.compile(r"^([^\t]*)\t([^\t]*)\t")
_GH_MARKER = re.compile(r"^##\[(group|endgroup|error|warning|notice|debug|command)\]")
_JENKINS_TS = re.compile(r"^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?Z\] ")
_JENKINS_STAGE = re.compile(r"^\[Pipeline\] \{ \((.+)\)$")
_JENKINS_HINTS = re.compile(r"^\[Pipeline\] |^Started by |^Finished: (?:SUCCESS|FAILURE|UNSTABLE|ABORTED)$")


@dataclass
class RawLine:
    number: int
    text: str
    job: str | None = None
    step: str | None = None
    timestamp: datetime | None = None
    marker: str | None = None  # GitHub workflow command: error, warning, group, ...


def _timestamp(base: str, fraction: str | None) -> datetime:
    micro = (fraction or ".0")[1:7].ljust(6, "0")
    return datetime.fromisoformat(f"{base}.{micro}").replace(tzinfo=UTC)


def detect_format(lines: list[str]) -> LogFormat:
    sample = [line for line in lines[:500] if line.strip()]
    if not sample:
        return "text"
    gh = sum(
        1 for line in sample
        if _ISO_TS.match(_GH_COLUMNS.sub("", line, count=1)) or _GH_MARKER.match(line)
    )
    if gh / len(sample) >= 0.5:
        return "github_actions"
    if any(_JENKINS_HINTS.search(_JENKINS_TS.sub("", line)) for line in sample):
        return "jenkins"
    return "text"


def parse_github_actions(lines: list[str]) -> list[RawLine]:
    out = []
    for number, raw in enumerate(lines, start=1):
        job = step = None
        columns = _GH_COLUMNS.match(raw)
        text = raw
        if columns:
            job, step = columns.group(1) or None, columns.group(2) or None
            if step == "UNKNOWN STEP":
                step = None
            text = raw[columns.end():]
        timestamp = None
        ts = _ISO_TS.match(text)
        if ts:
            timestamp = _timestamp(ts.group(1), ts.group(2))
            text = text[ts.end():]
        text = _ANSI.sub("", text).rstrip()
        marker = None
        command = _GH_MARKER.match(text)
        if command:
            marker = command.group(1)
            text = text[command.end():].lstrip()
        out.append(RawLine(number, text, job, step, timestamp, marker))
    return out


def parse_jenkins(lines: list[str]) -> list[RawLine]:
    out = []
    stage: str | None = None
    for number, raw in enumerate(lines, start=1):
        text = raw
        timestamp = None
        ts = _JENKINS_TS.match(text)
        if ts:
            timestamp = _timestamp(ts.group(1), ts.group(2))
            text = text[ts.end():]
        text = _ANSI.sub("", text).rstrip()
        entered = _JENKINS_STAGE.match(text)
        if entered:
            stage = entered.group(1)
        out.append(RawLine(number, text, step=stage, timestamp=timestamp))
    return out


def parse_text(lines: list[str]) -> list[RawLine]:
    return [
        RawLine(number, _ANSI.sub("", raw).rstrip()) for number, raw in enumerate(lines, start=1)
    ]


PARSERS = {
    "github_actions": parse_github_actions,
    "jenkins": parse_jenkins,
    "text": parse_text,
}
