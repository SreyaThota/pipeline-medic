"""Secret redaction, applied before a log is stored, parsed or sent to a model.

Each rule replaces the secret part of a match with `[REDACTED:<kind>]`. Lines
are never added or removed, so line numbers stay valid as evidence
references. The report records which kinds were found on which lines, never
the values.

Limits: this is pattern matching. It catches common token formats and
`key=value` style secrets, but not a secret with no recognisable shape. There
is deliberately no generic "long random string" rule: commit SHAs, digests
and IDs would be wiped out with it.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

# (kind, pattern, group): `group` is the regex group that holds the secret;
# 0 means the whole match.
_RULES: list[tuple[str, re.Pattern[str], int]] = [
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})"), 0),
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), 0),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), 0),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"), 0),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), 0),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b"), 0),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), 0),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/=-]{16,})"), 1),
    ("url_credentials", re.compile(r"\b[a-z][a-z0-9+.-]*://([^\s:/@]+:[^\s@/]+)@"), 1),
]

# `NAME=value` / `NAME: value` where NAME ends in a secret-ish keyword.
# - An optional prefix is allowed (DB_PASSWORD, GITHUB_TOKEN); the keyword must
#   end the name, so PASSWORD_FILE=/path is not treated as a secret.
# - Values masked by GitHub (`***`, `ghs_****`) or already redacted are skipped.
# - With `:` (also common in prose, e.g. "New password: Retype ...") the value
#   must contain a non-letter character; with `=` any value of 4+ chars counts.
_ASSIGNED = re.compile(
    r"(?i)(?<![A-Za-z0-9])[A-Za-z0-9_]*?(?:password|passwd|pwd|secret|token"
    r"|api[_-]?key|access[_-]?key|client[_-]?secret|private[_-]?key)\b[\"']?\s*([:=])\s*[\"']?"
    r"(?![^\s\"',;&]*\*\*\*|\[REDACTED:)([^\s\"',;&]{4,})"
)


def _redact_assigned(line: str, kinds: list[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        separator, value = match.group(1), match.group(2)
        if separator == ":" and value.rstrip(":.!?").isalpha():
            return match.group(0)
        kinds.append("assigned_secret")
        offset = match.start()
        start, end = match.span(2)
        whole = match.group(0)
        return whole[: start - offset] + _mask("assigned_secret") + whole[end - offset :]

    return _ASSIGNED.sub(replace, line)
_KEY_BEGIN = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
_KEY_END = re.compile(r"-----END [A-Z0-9 ]*PRIVATE KEY-----")


@dataclass
class RedactionResult:
    lines: list[str]
    # (line number starting at 1, kind) for every redaction made
    findings: list[tuple[int, str]] = field(default_factory=list)

    @property
    def by_kind(self) -> dict[str, int]:
        return dict(Counter(kind for _, kind in self.findings))


def _mask(kind: str) -> str:
    return f"[REDACTED:{kind}]"


def redact_line(line: str) -> tuple[str, list[str]]:
    """Redact one line; return the new line and the kinds found in it."""
    kinds: list[str] = []
    for kind, pattern, group in _RULES:

        def replace(match: re.Match[str], kind: str = kind, group: int = group) -> str:
            kinds.append(kind)
            if group == 0:
                return _mask(kind)
            start, end = match.span(group)
            offset = match.start()
            whole = match.group(0)
            return whole[: start - offset] + _mask(kind) + whole[end - offset :]

        line = pattern.sub(replace, line)
    return _redact_assigned(line, kinds), kinds


def redact_lines(lines: list[str]) -> RedactionResult:
    """Redact every line; whole private-key blocks become one marker per line."""
    result = RedactionResult(lines=[])
    in_key = False
    for number, line in enumerate(lines, start=1):
        if in_key or _KEY_BEGIN.search(line):
            if not in_key:
                result.findings.append((number, "private_key"))
            in_key = not _KEY_END.search(line)
            result.lines.append(_mask("private_key"))
            continue
        new_line, kinds = redact_line(line)
        result.lines.append(new_line)
        result.findings.extend((number, kind) for kind in kinds)
    return result
