"""Extended vault folder structure for Platinum tier."""

from pathlib import Path

DOMAINS = ["email", "social", "accounting", "general"]
WORKFLOW_DIRS = ["Needs_Action", "Plans", "Pending_Approval"]
AGENTS = ["cloud", "local"]


def ensure_platinum_vault_structure(vault_root: Path) -> None:
    """Create the full Platinum vault folder tree."""
    # Standard folders
    for folder in [
        "Needs_Action", "Plans", "Done", "Logs", "Inbox",
        "Pending_Approval", "Approved", "Rejected",
        "Briefings", "Accounting",
    ]:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)

    # Domain subfolders under workflow dirs
    for workflow_dir in WORKFLOW_DIRS:
        for domain in DOMAINS:
            (vault_root / workflow_dir / domain).mkdir(parents=True, exist_ok=True)

    # Agent-specific In_Progress
    for agent in AGENTS:
        (vault_root / "In_Progress" / agent).mkdir(parents=True, exist_ok=True)

    # Signal/Update directories
    (vault_root / "Updates").mkdir(parents=True, exist_ok=True)
    (vault_root / "Signals").mkdir(parents=True, exist_ok=True)
