"""Local Agent runner — full authority: approvals, sends, Dashboard, WhatsApp."""

import os
import shutil
import time
import logging
from datetime import datetime
from pathlib import Path

from src.brain import (
    call_llm, process_task, process_approved, process_rejected,
    log_action, execute_task,
)
from src.dashboard import update_dashboard
from src.retry_handler import graceful_degrade
from src.ceo_briefing import maybe_generate_briefing
from src.platinum.agent_identity import AgentRole, require_permission
from src.platinum.vault_structure import ensure_platinum_vault_structure, DOMAINS
from src.platinum.vault_sync import VaultSync
from src.platinum.claim_manager import ClaimManager
from src.platinum.signal_bus import read_and_consume_signals, read_health_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LOCAL] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

ROLE = AgentRole.LOCAL
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "10"))


def process_domain_approvals(vault_root: Path):
    """Process approvals from all domain subfolders in Pending_Approval/."""
    for domain in DOMAINS:
        pending_dir = vault_root / "Pending_Approval" / domain
        if not pending_dir.exists():
            continue

        for approval_file in pending_dir.glob("APPROVE_*.md"):
            logger.info(f"Found pending approval [{domain}]: {approval_file.name}")
            # In demo mode, auto-move to Approved for processing
            # In production, user would manually move files
            # Here we just log it — user moves files manually
            pass


def process_approved_with_send(vault_root: Path):
    """Execute approved tasks with full SEND authority."""
    approved_dir = vault_root / "Approved"
    if not approved_dir.exists():
        return

    for approved_file in approved_dir.glob("*.md"):
        task_name = approved_file.stem
        content = approved_file.read_text()

        try:
            # Detect type from frontmatter
            if "type: email_draft" in content:
                logger.info(f"Executing email send: {task_name}")
                # Extract draft and send via MCP (mock)
                log_action(task_name, "email_sent", "success")

            elif "type: social_draft" in content:
                logger.info(f"Executing social post: {task_name}")
                log_action(task_name, "social_posted", "success")

            elif "type: accounting_draft" in content:
                logger.info(f"Executing accounting entry: {task_name}")
                log_action(task_name, "accounting_posted", "success")

            elif any(approved_file.name.upper().startswith(p)
                     for p in ("FACEBOOK_", "INSTAGRAM_", "TWEET_", "LINKEDIN_")):
                from src.social_media.facebook_poster import process_approved_facebook_post
                from src.social_media.instagram_poster import process_approved_instagram_post
                from src.social_media.twitter_poster import process_approved_tweet

                name_upper = approved_file.name.upper()
                if name_upper.startswith("FACEBOOK_"):
                    process_approved_facebook_post(approved_file)
                elif name_upper.startswith("INSTAGRAM_"):
                    process_approved_instagram_post(approved_file)
                elif name_upper.startswith("TWEET_"):
                    process_approved_tweet(approved_file)
                continue  # Social media posters handle the move to Done

            else:
                # General approved task
                process_approved(approved_file)
                continue

            # Move to Done
            shutil.move(str(approved_file), str(vault_root / "Done" / approved_file.name))

        except Exception as e:
            logger.error(f"Failed to execute {task_name}: {e}")
            log_action(task_name, "execute_failed", "error", str(e))


def process_general_tasks(vault_root: Path, claim: ClaimManager):
    """Claim and process general tasks that Cloud didn't pick up."""
    general_dir = vault_root / "Needs_Action" / "general"
    if not general_dir.exists():
        return

    for task in general_dir.glob("*.md"):
        claimed = claim.try_claim(task)
        if not claimed:
            continue

        try:
            process_task(claimed)
        except Exception as e:
            logger.error(f"Failed to process {claimed.name}: {e}")


def merge_cloud_signals(vault_root: Path):
    """Merge Cloud signals into a summary for the Dashboard."""
    signals = read_and_consume_signals(vault_root)
    if signals:
        logger.info(f"Merged {len(signals)} cloud signal(s)")


def update_platinum_dashboard(vault_root: Path):
    """Update Dashboard.md with cloud health + signal info (Local only)."""
    require_permission(ROLE, "can_write_dashboard")

    # Use existing dashboard update
    # Override DASHBOARD_FILE temporarily for the vault_root
    dashboard_file = vault_root / "Dashboard.md"
    from src.dashboard import count_md_files, get_recent_logs
    from src.config import NEEDS_ACTION, PLANS, DONE, LOGS, PENDING_APPROVAL, APPROVED, REJECTED

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Count from vault_root instead of default vault
    needs_action = sum(1 for f in (vault_root / "Needs_Action").rglob("*.md"))
    plans = sum(1 for f in (vault_root / "Plans").rglob("*.md"))
    pending = sum(1 for f in (vault_root / "Pending_Approval").rglob("*.md"))
    approved = count_md_files(vault_root / "Approved") if (vault_root / "Approved").exists() else 0
    rejected = count_md_files(vault_root / "Rejected") if (vault_root / "Rejected").exists() else 0
    done = count_md_files(vault_root / "Done") if (vault_root / "Done").exists() else 0

    # Health status
    health = read_health_status(vault_root)
    health_section = ""
    if health:
        health_section = f"\n{health}\n"

    dashboard = f"""# AI Employee Dashboard (Platinum Tier)

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
{health_section}
## Quick Actions
- Cloud Agent drafts are in [[Pending_Approval]]
- Move to [[Approved]] to approve and execute
- Move to [[Rejected]] to reject
- Check [[Plans]] for AI-generated plans
- Check [[Done]] for completed tasks
"""
    dashboard_file.write_text(dashboard)


def main():
    vault_root = Path(os.getenv("VAULT_PATH", "vault_local")).resolve()
    if not vault_root.is_absolute():
        vault_root = Path.cwd() / vault_root

    ensure_platinum_vault_structure(vault_root)
    sync = VaultSync(vault_root, "local")
    claim = ClaimManager(vault_root, "local")

    logger.info(f"Local Agent started (vault: {vault_root})")
    logger.info(f"Checking every {CHECK_INTERVAL} seconds")

    while True:
        sync.pull()

        # 1. Merge Cloud signals
        with graceful_degrade("signal_merge"):
            merge_cloud_signals(vault_root)

        # 2. Log domain approvals (user moves files manually)
        with graceful_degrade("domain_approvals"):
            process_domain_approvals(vault_root)

        # 3. Execute approved tasks with SEND authority
        with graceful_degrade("approved_executor"):
            process_approved_with_send(vault_root)

        # 4. Process rejected
        with graceful_degrade("rejection_processor"):
            rejected_dir = vault_root / "Rejected"
            if rejected_dir.exists():
                for task in rejected_dir.glob("*.md"):
                    try:
                        process_rejected(task)
                    except Exception as e:
                        logger.error(f"Failed to process rejected {task.name}: {e}")

        # 5. Claim general tasks
        with graceful_degrade("general_tasks"):
            process_general_tasks(vault_root, claim)

        # 6. Update Dashboard (Local only — single writer)
        with graceful_degrade("dashboard"):
            update_platinum_dashboard(vault_root)

        # 7. CEO Briefing
        with graceful_degrade("ceo_briefing"):
            maybe_generate_briefing()

        sync.push()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
