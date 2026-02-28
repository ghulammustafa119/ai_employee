import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from src.config import (
    DONE, LOGS, BRIEFINGS, BUSINESS_GOALS_FILE,
)
from src.brain import call_llm, log_action
from src.odoo_client import OdooClient
from src.social_media.facebook_poster import get_facebook_summary
from src.social_media.instagram_poster import get_instagram_summary
from src.social_media.twitter_poster import get_twitter_summary

logger = logging.getLogger(__name__)

CEO_BRIEFING_PROMPT = """You are an AI Executive Assistant generating a Monday Morning CEO Briefing.

Given the following business data, produce a professional briefing in markdown format with these sections:

## Executive Summary
(2-3 sentence overview of the week)

## Revenue
- This Week: $X
- MTD: $X (Y% of target)
- Trend: On track / Behind / Ahead

## Completed Tasks
(List of completed tasks this week)

## Bottlenecks
(Table of delayed tasks with expected vs actual time)

## Proactive Suggestions
### Cost Optimization
(Any subscription or cost savings recommendations)

### Upcoming Deadlines
(Next 2 weeks of deadlines)

Be concise, data-driven, and actionable. Use the actual numbers provided.
"""


def get_completed_tasks_this_week() -> list[str]:
    """Get tasks completed in the last 7 days from Done folder."""
    tasks = []
    if not DONE.exists():
        return tasks

    cutoff = datetime.now() - timedelta(days=7)
    for f in DONE.iterdir():
        if f.suffix != ".md":
            continue
        try:
            stat = f.stat()
            modified = datetime.fromtimestamp(stat.st_mtime)
            if modified >= cutoff:
                tasks.append(f.stem)
        except Exception:
            continue
    return tasks


def get_recent_log_summary(days: int = 7) -> dict:
    """Summarize activity logs for the past N days."""
    summary = {"total_actions": 0, "successes": 0, "errors": 0, "by_action": {}}

    if not LOGS.exists():
        return summary

    cutoff = datetime.now() - timedelta(days=days)
    for log_file in LOGS.glob("*.json"):
        if log_file.name.startswith("audit_"):
            continue
        try:
            date_str = log_file.stem
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff:
                continue
        except ValueError:
            continue

        try:
            entries = json.loads(log_file.read_text())
            for entry in entries:
                summary["total_actions"] += 1
                result = entry.get("result", "")
                if result == "success":
                    summary["successes"] += 1
                elif result == "error":
                    summary["errors"] += 1
                action = entry.get("action", "unknown")
                summary["by_action"][action] = summary["by_action"].get(action, 0) + 1
        except (json.JSONDecodeError, Exception):
            continue

    return summary


def get_business_goals() -> str:
    """Read Business_Goals.md content."""
    if BUSINESS_GOALS_FILE.exists():
        return BUSINESS_GOALS_FILE.read_text()
    return "No business goals file found."


def generate_weekly_audit() -> str:
    """Collect all data and generate the CEO Briefing."""
    logger.info("Generating weekly CEO briefing...")

    # 1. Gather data
    completed_tasks = get_completed_tasks_this_week()
    log_summary = get_recent_log_summary(7)
    business_goals = get_business_goals()

    # 2. Odoo financial data
    odoo = OdooClient()
    financial = odoo.get_financial_summary("this_month")
    balance = odoo.get_account_balance()

    # 3. Social media summaries
    fb_summary = get_facebook_summary()
    ig_summary = get_instagram_summary()
    tw_summary = get_twitter_summary()

    # 4. Build context for LLM
    data_context = f"""## Business Goals
{business_goals}

## Financial Data (from Odoo)
- Total Invoiced: ${financial['total_invoiced']:.2f}
- Total Paid: ${financial['total_paid']:.2f}
- Open Invoices: ${financial['total_open']:.2f}
- Collection Rate: {financial['collection_rate']:.1f}%
- Bank Balance: ${balance['bank_balance']:.2f}
- Accounts Receivable: ${balance['accounts_receivable']:.2f}

## Completed Tasks This Week ({len(completed_tasks)})
{chr(10).join(f'- {t}' for t in completed_tasks) if completed_tasks else '- No tasks completed this week'}

## Activity Summary (7 days)
- Total Actions: {log_summary['total_actions']}
- Successes: {log_summary['successes']}
- Errors: {log_summary['errors']}

## Social Media Performance
{fb_summary}
{ig_summary}
{tw_summary}
"""

    # 5. Generate briefing with AI
    briefing_body = call_llm(CEO_BRIEFING_PROMPT, data_context, max_tokens=4096)

    # 6. Wrap with metadata
    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday() + 1)).strftime("%Y-%m-%d")
    week_end = (today - timedelta(days=today.weekday() + 1) + timedelta(days=6)).strftime("%Y-%m-%d")

    briefing = f"""---
generated: {today.isoformat()}
period: {week_start} to {week_end}
---

# Monday Morning CEO Briefing

{briefing_body}

---
*Generated by AI Employee v0.2 (Gold Tier)*
"""
    return briefing


def save_briefing() -> Path:
    """Generate and save the CEO Briefing to vault/Briefings/."""
    BRIEFINGS.mkdir(parents=True, exist_ok=True)

    briefing = generate_weekly_audit()
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = BRIEFINGS / f"{today}_Monday_Briefing.md"
    filepath.write_text(briefing)

    log_action(f"ceo_briefing_{today}", "briefing_generated", "success")
    logger.info(f"CEO Briefing saved: {filepath}")
    return filepath


def is_briefing_day() -> bool:
    """Check if today is the scheduled briefing day."""
    from src.config import BRIEFING_DAY
    return datetime.now().strftime("%A") == BRIEFING_DAY


def maybe_generate_briefing() -> Path | None:
    """Generate briefing if today is the scheduled day and it hasn't been generated yet."""
    if not is_briefing_day():
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    existing = BRIEFINGS / f"{today}_Monday_Briefing.md"
    if existing.exists():
        logger.debug("Briefing already generated today")
        return None

    return save_briefing()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    path = save_briefing()
    print(f"Briefing generated: {path}")
