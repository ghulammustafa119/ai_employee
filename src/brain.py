import json
import shutil
import logging
from datetime import datetime
from pathlib import Path

from groq import Groq

from src.config import (
    NEEDS_ACTION, PLANS, DONE, LOGS, PENDING_APPROVAL, APPROVED, REJECTED,
    GROQ_API_KEY, DRY_RUN, SENSITIVE_KEYWORDS,
)
from src.retry_handler import with_retry, graceful_degrade
from src.audit_logger import audit

logger = logging.getLogger(__name__)
client = Groq(api_key=GROQ_API_KEY)

PLAN_PROMPT = """You are an AI Employee task planner. Given a task description, create a clear action plan.

Output format:
---
task: <original task title>
status: planned
created: <current timestamp>
---

## Plan
- Step-by-step actions to complete this task

## Notes
- Any important considerations
"""

EXECUTE_PROMPT = """You are an AI Employee that EXECUTES tasks. You don't just plan — you DO the actual work.

Given a task and its plan, produce the ACTUAL deliverable/output.

Examples:
- If task says "write a blog post" → Write the full blog post
- If task says "draft an email" → Write the complete email
- If task says "summarize this data" → Provide the summary
- If task says "create a report" → Write the full report

Output the final deliverable in clean markdown format. Do the actual work, not just describe it.
"""


def get_pending_tasks() -> list[Path]:
    """Get all .md files from Needs_Action folder, skip already processed ones."""
    tasks = []
    for f in NEEDS_ACTION.iterdir():
        if f.suffix != ".md":
            continue
        if (PLANS / f"PLAN_{f.stem}.md").exists():
            logger.debug(f"Skipping duplicate: {f.name} (already processed)")
            continue
        if (DONE / f.name).exists():
            logger.debug(f"Skipping duplicate: {f.name} (already in Done)")
            continue
        tasks.append(f)
    return tasks


def get_approved_tasks() -> list[Path]:
    """Get all .md files from Approved folder ready for execution."""
    return [f for f in APPROVED.iterdir() if f.suffix == ".md"]


def get_rejected_tasks() -> list[Path]:
    """Get new .md files from Rejected folder (skip already processed)."""
    return [f for f in REJECTED.iterdir() if f.suffix == ".md" and not f.name.startswith("REJECTED_")]


def process_rejected(rejected_file: Path) -> None:
    """Log rejected task — file stays in Rejected folder."""
    task_name = rejected_file.stem.replace("APPROVE_", "")
    logger.info(f"Task rejected: {task_name}")
    log_action(task_name, "rejected", "rejected_by_human")
    # Mark as processed by renaming with REJECTED_ prefix
    processed_name = f"REJECTED_{rejected_file.name}" if not rejected_file.name.startswith("REJECTED_") else rejected_file.name
    processed_path = REJECTED / processed_name
    if processed_path != rejected_file:
        shutil.move(str(rejected_file), str(processed_path))
    logger.info(f"Task rejected and kept in Rejected/: {processed_name}")


@with_retry(max_attempts=3, base_delay=2)
def call_llm(system_prompt: str, user_message: str, max_tokens: int = 2048) -> str:
    """Call Groq LLM with given prompts (with automatic retry on transient errors)."""
    with audit.timed_event("llm_call", actor="groq", target="llama-3.3-70b-versatile"):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content


def generate_plan(task_content: str, task_name: str) -> str:
    """Step 1: Generate a plan for the task."""
    return call_llm(
        PLAN_PROMPT,
        f"Task file: {task_name}\n\nTask content:\n{task_content}",
    )


def execute_task(task_content: str, plan: str) -> str:
    """Step 2: Execute the task — produce the actual deliverable."""
    return call_llm(
        EXECUTE_PROMPT,
        f"Original task:\n{task_content}\n\nPlan:\n{plan}\n\nNow execute this task and produce the actual output.",
        max_tokens=4096,
    )


def is_sensitive(task_content: str) -> bool:
    """Check if task contains sensitive keywords requiring approval."""
    content_lower = task_content.lower()
    return any(kw in content_lower for kw in SENSITIVE_KEYWORDS)


def send_to_approval(task_file: Path, plan: str) -> None:
    """Move task to Pending_Approval with plan attached."""
    task_content = task_file.read_text()
    task_name = task_file.stem

    approval_content = f"""---
type: approval_request
original_task: {task_file.name}
created: {datetime.now().isoformat()}
status: pending_approval
---

## Original Task
{task_content}

## AI Generated Plan
{plan}

## To Approve
Move this file to the `Approved/` folder.

## To Reject
Move this file to the `Rejected/` folder.
"""
    approval_file = PENDING_APPROVAL / f"APPROVE_{task_name}.md"
    approval_file.write_text(approval_content)

    # Also save the plan
    plan_file = PLANS / f"PLAN_{task_name}.md"
    plan_file.write_text(plan)

    # Move original to Pending_Approval too
    shutil.move(str(task_file), str(PENDING_APPROVAL / task_file.name))

    logger.info(f"Sent to approval: {task_name}")
    log_action(task_name, "sent_to_approval", "pending")


def process_approved(approved_file: Path) -> None:
    """Execute an approved task."""
    task_name = approved_file.stem.replace("APPROVE_", "")
    logger.info(f"Executing approved task: {task_name}")

    content = approved_file.read_text()

    # Extract original task content from the approval file
    # Look for the plan in Plans/
    plan_file = PLANS / f"PLAN_{task_name}.md"
    plan = plan_file.read_text() if plan_file.exists() else ""

    # Execute the task
    try:
        output = execute_task(content, plan)
    except Exception as e:
        log_action(task_name, "execute_failed", "error", str(e))
        raise

    output_file = DONE / f"OUTPUT_{task_name}.md"
    output_file.write_text(output)
    logger.info(f"Output saved: {output_file.name}")

    # Move approved file to Done
    shutil.move(str(approved_file), str(DONE / approved_file.name))

    # Also move original task if it's still in Pending_Approval
    original_in_pending = PENDING_APPROVAL / f"{task_name}.md"
    if original_in_pending.exists():
        shutil.move(str(original_in_pending), str(DONE / f"{task_name}.md"))

    log_action(task_name, "approved_and_executed", "success")
    logger.info(f"Approved task completed: {task_name}")


def log_action(task_name: str, action: str, result: str, details: str = "") -> None:
    """Log an action to the Logs folder as JSON + readable .md."""
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now()
    timestamp = now.isoformat()
    time_str = now.strftime("%H:%M:%S")

    # 1. JSON log
    log_file = LOGS / f"{today}.json"
    entry = {
        "timestamp": timestamp,
        "task": task_name,
        "action": action,
        "result": result,
    }
    if details:
        entry["details"] = details

    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text())
        except json.JSONDecodeError:
            logger.warning(f"Corrupted log file: {log_file}, starting fresh")
            entries = []
    entries.append(entry)
    log_file.write_text(json.dumps(entries, indent=2))

    # 2. Readable .md log
    md_file = LOGS / f"{today}.md"
    details_col = f" | {details}" if details else ""

    if not md_file.exists():
        md_file.write_text(f"""# Activity Log — {today}

| Time | Task | Action | Result |
|------|------|--------|--------|
""")

    line = f"| {time_str} | {task_name} | {action} | {result}{details_col} |\n"
    with open(md_file, "a") as f:
        f.write(line)


def detect_domain(task_content: str) -> str:
    """Detect if a task is personal or business domain."""
    business_keywords = ["invoice", "client", "revenue", "project", "budget", "payment", "contract", "proposal"]
    personal_keywords = ["email", "whatsapp", "message", "appointment", "reminder", "personal"]
    content_lower = task_content.lower()
    biz_score = sum(1 for kw in business_keywords if kw in content_lower)
    personal_score = sum(1 for kw in personal_keywords if kw in content_lower)
    return "business" if biz_score > personal_score else "personal"


def process_task(task_file: Path) -> None:
    """Process a single task: read → plan → (approve or execute) → log."""
    task_name = task_file.stem
    logger.info(f"Processing task: {task_name}")

    if DRY_RUN:
        logger.info(f"[DRY RUN] Would process: {task_name}")
        log_action(task_name, "dry_run", "skipped", "DRY_RUN mode enabled")
        return

    # 1. Read task
    task_content = task_file.read_text()
    if not task_content.strip():
        logger.warning(f"Empty task file: {task_file.name}, skipping")
        log_action(task_name, "task_skipped", "empty_file")
        return

    # 1b. Detect domain (personal vs business)
    domain = detect_domain(task_content)
    logger.info(f"Task domain: {domain}")
    audit.log_event("task_classified", target=task_name, parameters={"domain": domain})

    # 2. Generate plan
    try:
        plan = generate_plan(task_content, task_name)
    except Exception as e:
        log_action(task_name, "plan_failed", "error", str(e))
        raise

    # 3. Check if sensitive → send to approval
    if is_sensitive(task_content):
        logger.info(f"Sensitive task detected: {task_name} → sending to approval")
        send_to_approval(task_file, plan)
        return

    # 4. Not sensitive → execute directly
    plan_file = PLANS / f"PLAN_{task_name}.md"
    plan_file.write_text(plan)
    logger.info(f"Plan saved: {plan_file.name}")

    try:
        output = execute_task(task_content, plan)
    except Exception as e:
        log_action(task_name, "execute_failed", "error", str(e))
        raise

    output_file = DONE / f"OUTPUT_{task_name}.md"
    output_file.write_text(output)
    logger.info(f"Output saved: {output_file.name}")

    # 5. Move original task to Done
    shutil.move(str(task_file), str(DONE / task_file.name))
    logger.info(f"Task moved to Done: {task_file.name}")

    # 6. Log
    log_action(task_name, "task_processed", "success")
    logger.info(f"Task completed: {task_name}")
