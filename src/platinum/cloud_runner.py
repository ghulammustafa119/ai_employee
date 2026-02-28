"""Cloud Agent runner — draft-only, no send/approve authority."""

import os
import shutil
import time
import logging
from datetime import datetime
from pathlib import Path

from src.brain import call_llm, generate_plan, is_sensitive, log_action
from src.retry_handler import graceful_degrade
from src.platinum.agent_identity import AgentRole, require_permission
from src.platinum.vault_structure import ensure_platinum_vault_structure, DOMAINS
from src.platinum.vault_sync import VaultSync
from src.platinum.claim_manager import ClaimManager
from src.platinum.signal_bus import write_signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CLOUD] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

ROLE = AgentRole.CLOUD
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "10"))

EMAIL_DRAFT_PROMPT = """You are an AI Email Assistant. Given an incoming email, draft a professional reply.

Be polite, concise, and address the sender's questions or requests.
Output ONLY the reply text, nothing else.
"""

SOCIAL_DRAFT_PROMPT = """You are a Social Media Content Creator. Given a topic or request, draft a professional social media post.

Keep it engaging, concise, and include relevant hashtags.
Output ONLY the post text, nothing else.
"""

ACCOUNTING_DRAFT_PROMPT = """You are an Accounting Assistant. Given a financial task, draft the appropriate accounting entry or response.

Be precise with numbers and follow standard accounting practices.
Output the draft entry in clean markdown format.
"""


def write_draft_approval(vault_root: Path, claimed_file: Path, draft: str, domain: str) -> Path:
    """Write a draft + approval request to Pending_Approval/<domain>/."""
    task_name = claimed_file.stem
    approval_content = f"""---
type: {domain}_draft
original_task: {claimed_file.name}
created: {datetime.now().isoformat()}
status: pending_approval
drafted_by: cloud
---

## Original Task
{claimed_file.read_text()}

## Cloud Agent Draft
{draft}

## To Approve
Move this file to the `Approved/` folder.

## To Reject
Move this file to the `Rejected/` folder.
"""
    approval_dir = vault_root / "Pending_Approval" / domain
    approval_dir.mkdir(parents=True, exist_ok=True)
    approval_file = approval_dir / f"APPROVE_{task_name}.md"
    approval_file.write_text(approval_content)

    # Save plan
    plan_dir = vault_root / "Plans" / domain
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / f"PLAN_{task_name}.md").write_text(draft)

    # Move claimed file to Done (cloud's work is done)
    done_dir = vault_root / "Done"
    shutil.move(str(claimed_file), str(done_dir / claimed_file.name))

    log_action(task_name, "cloud_drafted", "pending_approval")
    return approval_file


def process_email_tasks(vault_root: Path, claim: ClaimManager):
    """Triage emails: generate draft replies."""
    email_dir = vault_root / "Needs_Action" / "email"
    if not email_dir.exists():
        return

    for task in email_dir.glob("*.md"):
        claimed = claim.try_claim(task)
        if not claimed:
            continue

        content = claimed.read_text()
        with graceful_degrade("cloud_email_draft"):
            draft = call_llm(EMAIL_DRAFT_PROMPT, f"Incoming email:\n{content}", max_tokens=1024)
            write_draft_approval(vault_root, claimed, draft, "email")
            write_signal(vault_root, "email_draft_ready", f"Draft reply for: {claimed.stem}")


def process_social_tasks(vault_root: Path, claim: ClaimManager):
    """Generate social media draft posts."""
    social_dir = vault_root / "Needs_Action" / "social"
    if not social_dir.exists():
        return

    for task in social_dir.glob("*.md"):
        claimed = claim.try_claim(task)
        if not claimed:
            continue

        content = claimed.read_text()
        with graceful_degrade("cloud_social_draft"):
            draft = call_llm(SOCIAL_DRAFT_PROMPT, f"Create a post about:\n{content}", max_tokens=1024)
            write_draft_approval(vault_root, claimed, draft, "social")
            write_signal(vault_root, "social_draft_ready", f"Draft post for: {claimed.stem}")


def process_accounting_tasks(vault_root: Path, claim: ClaimManager):
    """Generate accounting draft entries."""
    accounting_dir = vault_root / "Needs_Action" / "accounting"
    if not accounting_dir.exists():
        return

    for task in accounting_dir.glob("*.md"):
        claimed = claim.try_claim(task)
        if not claimed:
            continue

        content = claimed.read_text()
        with graceful_degrade("cloud_accounting_draft"):
            draft = call_llm(ACCOUNTING_DRAFT_PROMPT, f"Accounting task:\n{content}", max_tokens=1024)
            write_draft_approval(vault_root, claimed, draft, "accounting")


def process_general_tasks(vault_root: Path, claim: ClaimManager):
    """Process general tasks — execute non-sensitive, draft sensitive."""
    general_dir = vault_root / "Needs_Action" / "general"
    if not general_dir.exists():
        return

    for task in general_dir.glob("*.md"):
        claimed = claim.try_claim(task)
        if not claimed:
            continue

        content = claimed.read_text()
        with graceful_degrade("cloud_general"):
            plan = generate_plan(content, claimed.stem)

            if is_sensitive(content):
                write_draft_approval(vault_root, claimed, plan, "general")
                write_signal(vault_root, "sensitive_task_drafted", f"Needs approval: {claimed.stem}")
            else:
                # Non-sensitive: execute directly
                from src.brain import execute_task
                output = execute_task(content, plan)
                (vault_root / "Done" / f"OUTPUT_{claimed.stem}.md").write_text(output)
                shutil.move(str(claimed), str(vault_root / "Done" / claimed.name))
                log_action(claimed.stem, "cloud_executed", "success")


def main():
    vault_root = Path(os.getenv("VAULT_PATH", "vault_cloud")).resolve()
    if not vault_root.is_absolute():
        vault_root = Path.cwd() / vault_root

    ensure_platinum_vault_structure(vault_root)
    sync = VaultSync(vault_root, "cloud")
    claim = ClaimManager(vault_root, "cloud")

    logger.info(f"Cloud Agent started (vault: {vault_root})")
    logger.info(f"Checking every {CHECK_INTERVAL} seconds")

    while True:
        sync.pull()

        with graceful_degrade("cloud_email"):
            process_email_tasks(vault_root, claim)

        with graceful_degrade("cloud_social"):
            process_social_tasks(vault_root, claim)

        with graceful_degrade("cloud_accounting"):
            process_accounting_tasks(vault_root, claim)

        with graceful_degrade("cloud_general"):
            process_general_tasks(vault_root, claim)

        sync.push()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
