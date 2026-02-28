"""Git-based vault sync between Cloud and Local agents."""

import subprocess
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SYNC_INTERVAL = int(__import__("os").getenv("SYNC_INTERVAL", "5"))


class VaultSync:
    """Syncs a vault working copy with the bare repo."""

    def __init__(self, vault_path: Path, agent_name: str):
        self.vault_path = vault_path
        self.agent_name = agent_name
        self._branch = None  # auto-detect on first use

    def _run_git(self, *args, timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=str(self.vault_path),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    @property
    def branch(self) -> str:
        """Auto-detect the current branch name (main or master)."""
        if self._branch is None:
            result = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
            self._branch = result.stdout.strip() if result.returncode == 0 else "main"
        return self._branch

    def _clean_git_state(self):
        """Abort any stuck rebase/merge before attempting git operations."""
        rebase_merge = self.vault_path / ".git" / "rebase-merge"
        rebase_apply = self.vault_path / ".git" / "rebase-apply"
        merge_head = self.vault_path / ".git" / "MERGE_HEAD"

        if rebase_merge.exists() or rebase_apply.exists():
            self._run_git("rebase", "--abort")
        if merge_head.exists():
            self._run_git("merge", "--abort")

    def pull(self) -> bool:
        """Pull latest changes from the bare repo."""
        self._clean_git_state()

        # Commit any uncommitted changes first so merge works
        self._run_git("add", "-A")
        status = self._run_git("status", "--porcelain")
        if status.stdout.strip():
            self._run_git("commit", "-m", f"[{self.agent_name}] pre-pull save")

        # Fetch
        fetch = self._run_git("fetch", "origin")
        if fetch.returncode != 0:
            # Retry once - ref lock errors are transient
            time.sleep(0.5)
            fetch = self._run_git("fetch", "origin")
            if fetch.returncode != 0:
                return False

        # Merge with auto-resolve (prefer ours for conflicts)
        remote_ref = f"origin/{self.branch}"
        result = self._run_git("merge", remote_ref, "-m", "sync merge",
                               "--strategy=recursive", "--strategy-option=ours",
                               "--no-edit")
        if result.returncode != 0:
            # If merge still fails, accept theirs entirely
            self._run_git("merge", "--abort")
            self._run_git("merge", remote_ref, "-m", "sync merge",
                          "--strategy=recursive", "--strategy-option=theirs",
                          "--no-edit")
        return True

    def push(self) -> bool:
        """Stage markdown changes and push."""
        self._clean_git_state()

        # Stage all changes
        self._run_git("add", "-A")

        # Check if anything to commit
        status = self._run_git("status", "--porcelain")
        if not status.stdout.strip():
            return True

        timestamp = time.strftime("%H:%M:%S")
        self._run_git("commit", "-m", f"[{self.agent_name}] sync {timestamp}")

        # Try push
        result = self._run_git("push")
        if result.returncode == 0:
            return True

        # Push failed — fetch, merge, push again
        self.pull()
        retry = self._run_git("push")
        if retry.returncode != 0:
            logger.warning(f"[{self.agent_name}] Push retry failed, will try next cycle")
            return False
        return True

    def sync(self) -> bool:
        """Full sync: pull then push."""
        pulled = self.pull()
        pushed = self.push()
        return pulled and pushed

    def run_sync_loop(self):
        """Continuous sync loop — run in a background thread."""
        logger.info(f"[{self.agent_name}] Sync loop started (interval: {SYNC_INTERVAL}s)")
        while True:
            try:
                self.sync()
            except Exception as e:
                logger.error(f"[{self.agent_name}] Sync error: {e}")
            time.sleep(SYNC_INTERVAL)
