import json
import logging
import time
from datetime import datetime
from pathlib import Path

from src.config import LOGS

logger = logging.getLogger(__name__)


class AuditLogger:
    """Structured audit logging with performance metrics."""

    def __init__(self, logs_dir: Path | None = None):
        self.logs_dir = logs_dir or LOGS

    def log_event(
        self,
        action_type: str,
        actor: str = "claude_code",
        target: str = "",
        parameters: dict | None = None,
        approval_status: str = "",
        approved_by: str = "",
        result: str = "success",
        duration_ms: float | None = None,
        details: str = "",
    ) -> dict:
        """Log a structured audit event."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": actor,
            "target": target,
            "parameters": parameters or {},
            "approval_status": approval_status,
            "approved_by": approved_by,
            "result": result,
        }
        if duration_ms is not None:
            entry["duration_ms"] = round(duration_ms, 2)
        if details:
            entry["details"] = details

        self._write(entry)
        return entry

    def timed_event(self, action_type: str, **kwargs):
        """Context-manager that measures duration and logs on exit."""
        return _TimedEvent(self, action_type, kwargs)

    def _write(self, entry: dict) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        audit_file = self.logs_dir / f"audit_{today}.json"

        entries = []
        if audit_file.exists():
            try:
                entries = json.loads(audit_file.read_text())
            except json.JSONDecodeError:
                logger.warning(f"Corrupted audit log: {audit_file}, starting fresh")
        entries.append(entry)
        audit_file.write_text(json.dumps(entries, indent=2))

    def get_monthly_summary(self, year: int, month: int) -> dict:
        """Generate a summary of actions for a given month."""
        prefix = f"audit_{year}-{month:02d}"
        entries = []
        for f in self.logs_dir.glob(f"{prefix}-*.json"):
            try:
                entries.extend(json.loads(f.read_text()))
            except (json.JSONDecodeError, Exception):
                continue

        summary = {
            "period": f"{year}-{month:02d}",
            "total_events": len(entries),
            "by_action": {},
            "by_result": {},
            "avg_duration_ms": 0,
        }
        durations = []
        for e in entries:
            action = e.get("action_type", "unknown")
            result = e.get("result", "unknown")
            summary["by_action"][action] = summary["by_action"].get(action, 0) + 1
            summary["by_result"][result] = summary["by_result"].get(result, 0) + 1
            if "duration_ms" in e:
                durations.append(e["duration_ms"])

        if durations:
            summary["avg_duration_ms"] = round(sum(durations) / len(durations), 2)
        return summary


class _TimedEvent:
    """Helper context-manager for AuditLogger.timed_event()."""

    def __init__(self, logger_instance: AuditLogger, action_type: str, kwargs: dict):
        self.logger_instance = logger_instance
        self.action_type = action_type
        self.kwargs = kwargs
        self.start = 0.0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start) * 1000
        if exc_type:
            self.kwargs["result"] = "error"
            self.kwargs["details"] = str(exc_val)
        self.logger_instance.log_event(
            self.action_type, duration_ms=duration_ms, **self.kwargs
        )
        return False


audit = AuditLogger()
