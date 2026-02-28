"""Claim-by-move mechanism for preventing double-work between agents."""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ClaimManager:
    """Atomically claim tasks so only one agent works on each."""

    def __init__(self, vault_root: Path, agent_name: str):
        self.vault_root = vault_root
        self.agent_name = agent_name
        self.in_progress_dir = vault_root / "In_Progress" / agent_name
        self.in_progress_dir.mkdir(parents=True, exist_ok=True)

    def try_claim(self, task_file: Path) -> Path | None:
        """Atomically claim a task. Returns new path if claimed, None if already taken."""
        dest = self.in_progress_dir / task_file.name
        try:
            os.rename(str(task_file), str(dest))
            logger.info(f"[{self.agent_name}] Claimed: {task_file.name}")
            return dest
        except FileNotFoundError:
            logger.debug(f"[{self.agent_name}] Already claimed by other agent: {task_file.name}")
            return None
        except OSError as e:
            logger.warning(f"[{self.agent_name}] Claim failed for {task_file.name}: {e}")
            return None

    def get_my_claims(self) -> list[Path]:
        """List all files currently claimed by this agent."""
        return [f for f in self.in_progress_dir.iterdir() if f.suffix == ".md"]

    def release_claim(self, claimed_file: Path, target_folder: Path) -> Path:
        """Move a claimed file to its final destination (Done, Pending_Approval, etc.)."""
        target_folder.mkdir(parents=True, exist_ok=True)
        dest = target_folder / claimed_file.name
        os.rename(str(claimed_file), str(dest))
        logger.info(f"[{self.agent_name}] Released: {claimed_file.name} → {target_folder.name}/")
        return dest
