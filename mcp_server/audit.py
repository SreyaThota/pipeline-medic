"""Append-only audit trail for tool calls (CLAUDE.md 2F).

Every tool call writes a `proposed` entry *before* anything happens, then one
outcome entry (`dry_run`, `executed`, `rejected` or `failed`). Arguments are
stored after redaction, never raw.
"""

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

AUDIT_FILE = "audit.jsonl"


class AuditLog:
    def __init__(self, runtime_dir: str | Path):
        self.path = Path(runtime_dir) / AUDIT_FILE
        self._lock = threading.Lock()

    def record(self, action_id: str, tool: str, phase: str, **fields: Any) -> dict[str, Any]:
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "action_id": action_id,
            "tool": tool,
            "phase": phase,
            **fields,
        }
        line = json.dumps(entry, ensure_ascii=False, default=str)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        return entry

    def entries(self, action_id: str | None = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
        return [r for r in rows if action_id is None or r["action_id"] == action_id]
