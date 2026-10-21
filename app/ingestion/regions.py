"""Severity classification and failure-region extraction.

A failure region is a contiguous block of evidence: a stack trace, an error
line with its context, a test-run summary, or an exit status. Regions keep
the original line numbers so a diagnosis can cite them.
"""

import re
from dataclasses import dataclass

from app.ingestion.formats import RawLine
from app.schemas.logs import RegionKind, Severity

_ERROR = re.compile(
    r"^(?:FATAL|FAILED|FAIL)\b|\bERROR\b|^Error:|\berror(?:\[E\d{4}\])?:|"
    r"\b[A-Z][A-Za-z]*(?:Error|Exception)\b(?::|$)|npm ERR!|[✘✗❌]|✖ \d+ problem|"
    r"\b[1-9]\d* (?:failed|failures?|errors?)\b|\bwould (?:reformat|be reformatted)\b|"
    r"\bBUILD FAILURE\b|^Finished: FAILURE$|exited with (?:code )?[1-9]|"
    r"exit code [1-9]|returned exit code [1-9]|\bcommand not found\b"
)
_WARNING = re.compile(r"^(?:WARNING|WARN)\b|\bwarning:|\[warn\]", re.IGNORECASE)
_TRACEBACK_START = re.compile(r"^Traceback \(most recent call last\):")
_TRACE_FRAME = re.compile(r"^\s+(?:at |File \"|\.\.\.)|^\s{2,}\S|^Caused by: |^\tat ")
_EXCEPTION_LINE = re.compile(r"^[A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt)\b")
_TEST_SUMMARY = re.compile(
    r"=+ .*\b\d+ (?:failed|passed|errors?)\b.*=+|^Tests:\s+\d+|^Test Suites:\s+\d+|"
    r"test result: (?:ok|FAILED)\.|^Tests run: \d+, Failures: \d+"
)
_EXIT_CODE = re.compile(
    r"(?:exit code:?|exited with(?: code)?|returned exit code|FAIL code|failed with code) (\d{1,3})\b"
)
_POST_JOB = re.compile(r"^Post job cleanup\.$")

MAX_REGIONS = 20


@dataclass
class _Span:
    kind: RegionKind
    start: int  # index into the line list
    end: int    # inclusive
    anchor: int


def severity(line: RawLine) -> Severity:
    if line.marker == "error" or _ERROR.search(line.text):
        return "error"
    if line.marker == "warning" or _WARNING.search(line.text):
        return "warning"
    return "info"


def noise_mask(lines: list[RawLine]) -> list[bool]:
    """True for post-job cleanup lines: runner boilerplate after the failure,
    near-identical across repos. A new job (GitHub column) ends the section."""
    mask, job, in_cleanup = [], object(), False
    for line in lines:
        if line.job != job:
            job, in_cleanup = line.job, False
        if _POST_JOB.match(line.text):
            in_cleanup = True
        mask.append(in_cleanup)
    return mask


def exit_codes(lines: list[RawLine]) -> list[tuple[int, int]]:
    found = []
    for line in lines:
        for code in _EXIT_CODE.findall(line.text):
            found.append((line.number, int(code)))
    return found


def _clip(span: _Span, noise: list[bool]) -> _Span:
    """Shrink a context window so it never reaches into noise lines."""
    while span.end > span.anchor and noise[span.end]:
        span.end -= 1
    while span.start < span.anchor and noise[span.start]:
        span.start += 1
    return span


def find_spans(lines: list[RawLine], severities: list[Severity], noise: list[bool],
               context: int) -> tuple[list[_Span], bool]:
    """Return failure spans (merged, in log order) and whether any were dropped."""
    spans: list[_Span] = []
    i = 0
    while i < len(lines):
        if noise[i]:
            i += 1
            continue
        text = lines[i].text
        if _TRACEBACK_START.match(text):
            j = i + 1
            while j < len(lines) and (_TRACE_FRAME.match(lines[j].text) or not lines[j].text):
                j += 1
            end = j if j < len(lines) and _EXCEPTION_LINE.match(lines[j].text) else j - 1
            spans.append(_Span("stack_trace", i, end, end))
            i = end + 1
            continue
        if _TEST_SUMMARY.search(text):
            spans.append(_Span("test_summary", i, i, i))
        elif _EXIT_CODE.search(text):
            spans.append(_clip(_Span("exit_code", max(0, i - context), i, i), noise))
        elif severities[i] == "error":
            end = min(len(lines) - 1, i + context)
            spans.append(_clip(_Span("error", max(0, i - context), end, i), noise))
        i += 1

    merged: list[_Span] = []
    for span in spans:
        last = merged[-1] if merged else None
        if last and span.start <= last.end + 1 and last.kind == span.kind:
            last.end = max(last.end, span.end)
        else:
            merged.append(span)
    dropped = len(merged) > MAX_REGIONS
    # Keep the last regions: in CI logs the decisive failure is usually near the end.
    return merged[-MAX_REGIONS:], dropped
