"""Health monitoring watchdog for Platinum tier agents."""

import os
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WATCHDOG] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

WATCHDOG_INTERVAL = int(os.getenv("WATCHDOG_INTERVAL", "30"))
PID_DIR = Path("/tmp")


def is_process_running(pid_file: Path) -> bool:
    """Check if a process is alive by its PID file."""
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # Signal 0 = check existence
        return True
    except (ProcessLookupError, ValueError, PermissionError):
        return False


def check_sync_freshness(vault_path: Path) -> bool:
    """Check that the vault was synced recently (within 120s)."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%ct", "-1"],
            cwd=str(vault_path),
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return False
        last_commit = int(result.stdout.strip())
        age = time.time() - last_commit
        return age < 120
    except Exception:
        return False


def write_health_report(vault_root: Path, cloud_ok: bool, local_ok: bool, sync_ok: bool):
    """Write health status to Updates/ for Dashboard consumption."""
    updates_dir = vault_root / "Updates"
    updates_dir.mkdir(parents=True, exist_ok=True)

    report = updates_dir / "health_status.md"
    report.write_text(f"""---
updated: {datetime.now().isoformat()}
---

## System Health
| Component | Status |
|-----------|--------|
| Cloud Agent | {"UP" if cloud_ok else "DOWN"} |
| Local Agent | {"UP" if local_ok else "DOWN"} |
| Vault Sync | {"OK" if sync_ok else "STALE"} |
""")


def main():
    vault_cloud = Path(os.getenv("VAULT_CLOUD_PATH", "vault_cloud")).resolve()
    vault_local = Path(os.getenv("VAULT_LOCAL_PATH", "vault_local")).resolve()

    cloud_pid = PID_DIR / "ai_employee_cloud.pid"
    local_pid = PID_DIR / "ai_employee_local.pid"

    logger.info(f"Watchdog started (interval: {WATCHDOG_INTERVAL}s)")

    while True:
        cloud_ok = is_process_running(cloud_pid)
        local_ok = is_process_running(local_pid)
        sync_ok = check_sync_freshness(vault_cloud)

        status = f"Cloud={'UP' if cloud_ok else 'DOWN'} Local={'UP' if local_ok else 'DOWN'} Sync={'OK' if sync_ok else 'STALE'}"
        logger.info(f"Health: {status}")

        # Write health to both vaults
        for vault in [vault_cloud, vault_local]:
            if vault.exists():
                write_health_report(vault, cloud_ok, local_ok, sync_ok)

        if not cloud_ok:
            logger.warning("Cloud Agent is DOWN!")
        if not local_ok:
            logger.warning("Local Agent is DOWN!")
        if not sync_ok:
            logger.warning("Vault sync is STALE!")

        time.sleep(WATCHDOG_INTERVAL)


if __name__ == "__main__":
    main()
