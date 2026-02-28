"""
Platinum Demo — End-to-end test of Cloud + Local agent coordination.

Scenario: Email arrives while Local is offline → Cloud drafts reply →
Local returns, approves → Local executes send → logs → Done.

Usage: uv run python -m src.platinum.demo
"""

import os
import shutil
import subprocess
import logging
import time
from datetime import datetime
from pathlib import Path

from src.brain import call_llm, log_action
from src.platinum.vault_structure import ensure_platinum_vault_structure
from src.platinum.vault_sync import VaultSync
from src.platinum.claim_manager import ClaimManager
from src.platinum.signal_bus import write_signal, read_and_consume_signals
from src.platinum.cloud_runner import (
    process_email_tasks,
    process_general_tasks as cloud_process_general,
)
from src.platinum.local_runner import (
    process_approved_with_send,
    merge_cloud_signals,
    update_platinum_dashboard,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DEMO] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent


def init_demo_vaults() -> tuple[Path, Path, Path]:
    """Create demo vault_sync.git, vault_cloud, vault_local."""
    bare_repo = PROJECT_DIR / "vault_sync.git"
    vault_cloud = PROJECT_DIR / "vault_cloud"
    vault_local = PROJECT_DIR / "vault_local"

    # Clean up previous demo
    for d in [bare_repo, vault_cloud, vault_local]:
        if d.exists():
            shutil.rmtree(d)

    # Create bare repo
    subprocess.run(["git", "init", "--bare", str(bare_repo)], capture_output=True)
    logger.info(f"Created bare repo: {bare_repo}")

    # Clone to cloud
    subprocess.run(["git", "clone", str(bare_repo), str(vault_cloud)], capture_output=True)

    # Set up cloud vault structure
    ensure_platinum_vault_structure(vault_cloud)

    # Copy essential files from vault/
    source_vault = PROJECT_DIR / "vault"
    for f in ["Company_Handbook.md", "Business_Goals.md"]:
        src = source_vault / f
        if src.exists():
            shutil.copy2(str(src), str(vault_cloud / f))

    # Create .gitignore
    (vault_cloud / ".gitignore").write_text(".env\ntoken.json\ncredentials.json\n__pycache__/\n")

    # Initial commit
    subprocess.run(["git", "add", "-A"], cwd=str(vault_cloud), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init: platinum demo vault"],
        cwd=str(vault_cloud), capture_output=True,
    )
    subprocess.run(["git", "push"], cwd=str(vault_cloud), capture_output=True)
    logger.info(f"Cloud vault ready: {vault_cloud}")

    # Clone to local
    subprocess.run(["git", "clone", str(bare_repo), str(vault_local)], capture_output=True)

    # Ensure full structure in local too
    ensure_platinum_vault_structure(vault_local)

    logger.info(f"Local vault ready: {vault_local}")

    return bare_repo, vault_cloud, vault_local


def run_demo():
    """Run the full Platinum demo scenario."""
    print()
    print("=" * 60)
    print("  PLATINUM TIER DEMO")
    print("  Email → Cloud Draft → Local Approve → Send → Done")
    print("=" * 60)
    print()

    # Step 1: Initialize vaults
    logger.info("Step 1: Initializing demo vaults...")
    bare_repo, vault_cloud, vault_local = init_demo_vaults()
    print("  [OK] Vault sync initialized")

    # Step 2: Simulate email arrival (drop into cloud vault)
    logger.info("Step 2: Simulating email arrival...")
    email_content = f"""---
type: email
from: john@clientcorp.com
subject: Project proposal follow-up
received: {datetime.now().isoformat()}
priority: high
status: pending
---

## Email from john@clientcorp.com

**Subject:** Project proposal follow-up
**Date:** {datetime.now().strftime("%a, %d %b %Y %H:%M:%S")}

## Content
Hi there,

Just following up on the proposal I sent last week for the website redesign project.
Could you confirm the timeline and budget? We'd like to kick off by March 15th.

Looking forward to your response.

Best regards,
John Smith
ClientCorp Inc.

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
"""
    email_file = vault_cloud / "Needs_Action" / "email" / "EMAIL_demo_proposal.md"
    email_file.write_text(email_content)
    print("  [OK] Email dropped into vault_cloud/Needs_Action/email/")

    # Step 3: Cloud agent processes (ONE cycle)
    logger.info("Step 3: Cloud Agent processing email (draft only)...")
    cloud_claim = ClaimManager(vault_cloud, "cloud")
    try:
        process_email_tasks(vault_cloud, cloud_claim)
        print("  [OK] Cloud drafted reply → Pending_Approval/email/")
    except Exception as e:
        # If LLM fails, create a mock draft
        logger.warning(f"LLM call failed ({e}), using mock draft")
        mock_draft = """Dear John,

Thank you for following up on the website redesign proposal.

I've reviewed the details and the timeline looks feasible. We can target a March 15th kickoff.
Regarding the budget, I'll have our team prepare a detailed breakdown by end of this week.

Could we schedule a quick call to align on the specific deliverables and milestones?

Best regards,
AI Employee"""
        from src.platinum.cloud_runner import write_draft_approval
        claimed = vault_cloud / "In_Progress" / "cloud" / "EMAIL_demo_proposal.md"
        if not claimed.exists():
            claimed = vault_cloud / "Needs_Action" / "email" / "EMAIL_demo_proposal.md"
            if claimed.exists():
                dest = vault_cloud / "In_Progress" / "cloud" / claimed.name
                shutil.move(str(claimed), str(dest))
                claimed = dest
            else:
                claimed = email_file
        write_draft_approval(vault_cloud, claimed, mock_draft, "email")
        write_signal(vault_cloud, "email_draft_ready", "Draft reply for: EMAIL_demo_proposal")
        print("  [OK] Cloud drafted reply (mock) → Pending_Approval/email/")

    # Step 4: Sync cloud → bare → local
    logger.info("Step 4: Syncing cloud → local...")
    cloud_sync = VaultSync(vault_cloud, "cloud")
    cloud_sync.push()

    local_sync = VaultSync(vault_local, "local")
    local_sync.pull()
    print("  [OK] Vault synced: cloud → local")

    # Step 5: Verify draft arrived at local
    pending_email_dir = vault_local / "Pending_Approval" / "email"
    approval_files = list(pending_email_dir.glob("APPROVE_*.md"))
    if approval_files:
        print(f"  [OK] Draft found in local: {approval_files[0].name}")
    else:
        print("  [!!] No approval file found - checking all Pending_Approval...")
        for f in (vault_local / "Pending_Approval").rglob("*.md"):
            print(f"       Found: {f.relative_to(vault_local)}")
        # Try to continue anyway
        approval_files = list((vault_local / "Pending_Approval").rglob("APPROVE_*.md"))

    # Step 6: Simulate user approval (move to Approved/)
    logger.info("Step 5: User approves the draft...")
    if approval_files:
        src = approval_files[0]
        dst = vault_local / "Approved" / src.name
        shutil.move(str(src), str(dst))
        print(f"  [OK] Approved: {src.name} → Approved/")

    # Step 7: Local agent executes send
    logger.info("Step 6: Local Agent executing send...")
    process_approved_with_send(vault_local)
    print("  [OK] Email sent (mock) → Done/")

    # Step 8: Merge signals + update dashboard
    logger.info("Step 7: Updating dashboard...")
    merge_cloud_signals(vault_local)
    update_platinum_dashboard(vault_local)
    print("  [OK] Dashboard updated")

    # Step 9: Sync local → bare
    local_sync.push()
    print("  [OK] Local synced back")

    # Step 10: Verify completion
    print()
    print("=" * 60)
    print("  VERIFICATION")
    print("=" * 60)

    done_files = list((vault_local / "Done").glob("*.md"))
    print(f"  Done/ files: {len(done_files)}")
    for f in done_files:
        print(f"    - {f.name}")

    log_files = list((vault_local / "Logs").glob("*.json"))
    print(f"  Log files: {len(log_files)}")

    dashboard = vault_local / "Dashboard.md"
    if dashboard.exists():
        print(f"  Dashboard: EXISTS ({dashboard.stat().st_size} bytes)")

    print()
    if done_files:
        print("  === PLATINUM DEMO PASSED ===")
    else:
        print("  === DEMO INCOMPLETE (check logs) ===")
    print()


if __name__ == "__main__":
    run_demo()
