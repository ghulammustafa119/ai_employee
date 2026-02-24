import json
import shutil
import logging
from datetime import datetime
from pathlib import Path

from groq import Groq

from src.config import NEEDS_ACTION, PLANS, DONE, LOGS, GROQ_API_KEY, DRY_RUN

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
        # Skip if already processed (plan or output exists)
        if (PLANS / f"PLAN_{f.stem}.md").exists():
            logger.debug(f"Skipping duplicate: {f.name} (already processed)")
            continue
        if (DONE / f.name).exists():
            logger.debug(f"Skipping duplicate: {f.name} (already in Done)")
            continue
        tasks.append(f)
    return tasks


def call_llm(system_prompt: str, user_message: str, max_tokens: int = 2048) -> str:
    """Call Groq LLM with given prompts."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise


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


def log_action(task_name: str, action: str, result: str, details: str = "") -> None:
    """Log an action to the Logs folder as JSON."""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS / f"{today}.json"

    entry = {
        "timestamp": datetime.now().isoformat(),
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


def process_task(task_file: Path) -> None:
    """Process a single task: read → plan → execute → save → log."""
    task_name = task_file.stem
    logger.info(f"Processing task: {task_name}")

    # DRY RUN mode — log but don't actually call LLM or move files
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

    # 2. Generate plan
    try:
        plan = generate_plan(task_content, task_name)
    except Exception as e:
        log_action(task_name, "plan_failed", "error", str(e))
        raise

    plan_file = PLANS / f"PLAN_{task_name}.md"
    plan_file.write_text(plan)
    logger.info(f"Plan saved: {plan_file.name}")

    # 3. Execute task — produce actual deliverable
    try:
        output = execute_task(task_content, plan)
    except Exception as e:
        log_action(task_name, "execute_failed", "error", str(e))
        raise

    output_file = DONE / f"OUTPUT_{task_name}.md"
    output_file.write_text(output)
    logger.info(f"Output saved: {output_file.name}")

    # 4. Move original task to Done
    done_file = DONE / task_file.name
    shutil.move(str(task_file), str(done_file))
    logger.info(f"Task moved to Done: {task_file.name}")

    # 5. Log action
    log_action(task_name, "task_processed", "success")
    logger.info(f"Task completed: {task_name}")
