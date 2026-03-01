import json
import logging
from datetime import datetime

from src.config import (
    NEEDS_ACTION, PLANS, DONE, LOGS, PENDING_APPROVAL, APPROVED, REJECTED,
    DASHBOARD_FILE,
)

logger = logging.getLogger(__name__)


def count_md_files(folder) -> int:
    """Count .md files in a folder (excluding .gitkeep)."""
    if not folder.exists():
        return 0
    return len([f for f in folder.iterdir() if f.suffix == ".md"])


def get_recent_logs(limit: int = 10) -> list[dict]:
    """Get the most recent log entries."""
    if not LOGS.exists():
        return []

    log_files = sorted(LOGS.glob("*.json"), reverse=True)
    entries = []

    for log_file in log_files:
        try:
            data = json.loads(log_file.read_text())
            entries.extend(data)
        except (json.JSONDecodeError, Exception):
            continue
        if len(entries) >= limit:
            break

    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return entries[:limit]


def update_dashboard() -> None:
    """Generate and write Dashboard.md with current system status."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    needs_action = count_md_files(NEEDS_ACTION)
    plans = count_md_files(PLANS)
    pending = count_md_files(PENDING_APPROVAL)
    approved = count_md_files(APPROVED)
    rejected = count_md_files(REJECTED)
    done = count_md_files(DONE)

    recent = get_recent_logs(10)
    activity_lines = []
    if recent:
        for entry in recent:
            ts = entry.get("timestamp", "?")[:19]
            task = entry.get("task", "?")
            action = entry.get("action", "?")
            result = entry.get("result", "?")
            activity_lines.append(f"| {ts} | {task} | {action} | {result} |")
    else:
        activity_lines.append("| — | No recent activity | — | — |")

    activity_table = "\n".join(activity_lines)

    dashboard = f"""# AI Employee Dashboard

> Last updated: {now}

## Task Summary
| Folder | Count |
|--------|-------|
| [[Needs_Action]] | {needs_action} |
| [[Plans]] | {plans} |
| [[Pending_Approval]] | {pending} |
| [[Approved]] | {approved} |
| [[Rejected]] | {rejected} |
| [[Done]] | {done} |

## Recent Activity
| Timestamp | Task | Action | Result |
|-----------|------|--------|--------|
{activity_table}

## Quick Actions
- Drop `.md` files in [[Needs_Action]] to create tasks
- Move files from [[Pending_Approval]] to [[Approved]] to approve
- Move files from [[Pending_Approval]] to [[Rejected]] to reject
- Check [[Plans]] for AI-generated plans
- Check [[Done]] for completed tasks
"""

    DASHBOARD_FILE.write_text(dashboard)
    logger.debug("Dashboard updated")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    update_dashboard()
    print(f"Dashboard updated: {DASHBOARD_FILE}")
