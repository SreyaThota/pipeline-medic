"""Log ingestion: redact, detect format, parse, extract failure evidence.

    parse_log(text) -> ParsedLog

Order matters: secrets are redacted first, so nothing after this point
(parsing, storage, model prompts, API responses) ever sees them.
"""

from app.ingestion.formats import PARSERS, RawLine, detect_format
from app.ingestion.regions import exit_codes, find_spans, noise_mask, severity
from app.redaction import redact_lines
from app.schemas.logs import (
    ExitCode,
    FailureRegion,
    LogFormat,
    LogLine,
    ParsedLog,
    RedactionReport,
)

MAX_LINE_CHARS = 2_000  # minified bundles can put megabytes on one line


def _split(text: str) -> tuple[list[str], bool]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    clipped = any(len(line) > MAX_LINE_CHARS for line in lines)
    return [line[:MAX_LINE_CHARS] for line in lines], clipped


def _to_model(line: RawLine, sev: str, noise: bool) -> LogLine:
    return LogLine(
        number=line.number, job=line.job, step=line.step, timestamp=line.timestamp,
        severity=sev, text=line.text, noise=noise,  # type: ignore[arg-type]
    )


def parse_log(
    text: str,
    fmt: LogFormat | None = None,
    tail_lines: int = 15,
    context: int = 3,
) -> ParsedLog:
    """Parse a raw CI log into redacted, line-referenced evidence.

    tail_lines keeps the v0.2 retrieval window (last 15 lines) reproducible.
    """
    raw_lines, clipped = _split(text)
    redaction = redact_lines(raw_lines)
    detected = fmt is None
    log_format: LogFormat = detect_format(redaction.lines) if fmt is None else fmt
    lines = PARSERS[log_format](redaction.lines)

    severities = [severity(line) for line in lines]
    noise = noise_mask(lines)
    spans, dropped = find_spans(lines, severities, noise, context)

    def model(i: int) -> LogLine:
        return _to_model(lines[i], severities[i], noise[i])

    regions = [
        FailureRegion(
            kind=span.kind,
            start_line=lines[span.start].number,
            end_line=lines[span.end].number,
            anchor_line=lines[span.anchor].number,
            lines=[model(i) for i in range(span.start, span.end + 1)],
        )
        for span in spans
    ]
    signal = [i for i in range(len(lines)) if not noise[i] and lines[i].text]
    tail = [model(i) for i in signal[-tail_lines:]] if tail_lines > 0 else []

    jobs = list(dict.fromkeys(line.job for line in lines if line.job))
    failed_steps = list(dict.fromkeys(
        line.step or line.job or "" for line, sev in zip(lines, severities)
        if sev == "error" and (line.step or line.job)
    ))

    flags = []
    if not any(r.kind in ("error", "stack_trace") for r in regions):
        flags.append("no_error_markers_found")
    if dropped:
        flags.append("regions_truncated")
    if clipped:
        flags.append("long_lines_truncated")
    if not detected:
        flags.append("format_forced")

    return ParsedLog(
        format=log_format,
        format_detected=detected,
        line_count=len(lines),
        jobs=jobs,
        failed_steps=failed_steps,
        exit_codes=[ExitCode(line=n, code=c) for n, c in exit_codes(lines)],
        regions=regions,
        tail=tail,
        redaction=RedactionReport(
            total=len(redaction.findings),
            by_kind=redaction.by_kind,
            lines=sorted({n for n, _ in redaction.findings}),
        ),
        flags=flags,
    )
