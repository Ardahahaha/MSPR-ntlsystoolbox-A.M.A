from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

_STATUS_TO_EXIT = {
    "SUCCESS": 0,
    "WARNING": 1,
    "CRITICAL": 2,
    "ERROR": 3,
    "UNKNOWN": 4,
}

def status_from_two_flags(a_ok: bool, b_ok: bool) -> str:
    if a_ok and b_ok:
        return "SUCCESS"
    if (a_ok and not b_ok) or (b_ok and not a_ok):
        return "WARNING"
    return "ERROR"

@dataclass
class ModuleResult:
    module: str = "module"
    status: str = "UNKNOWN"
    summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None

    def finish(self) -> "ModuleResult":
        if not self.finished_at:
            self.finished_at = datetime.now().isoformat(timespec="seconds")
        st = (self.status or "UNKNOWN").upper()
        self.status = st
        if self.exit_code is None:
            self.exit_code = _STATUS_TO_EXIT.get(st, 4)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module,
            "status": self.status,
            "exit_code": self.exit_code,
            "summary": self.summary,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "details": self.details or {},
            "artifacts": self.artifacts or {},
        }
