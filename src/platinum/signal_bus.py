"""Signal bus: Cloud writes signals, Local merges them into Dashboard."""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def write_signal(vault_root: Path, signal_type: str, details: str) -> Path:
    """Cloud writes a signal file to Signals/ folder."""
    signals_dir = vault_root / "Signals"
    signals_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    signal_file = signals_dir / f"{signal_type}_{timestamp}.md"
    signal_file.write_text(f"""---
signal: {signal_type}
created: {datetime.now().isoformat()}
agent: cloud
---

{details}
""")
    logger.info(f"Signal written: {signal_file.name}")
    return signal_file


def read_and_consume_signals(vault_root: Path) -> list[str]:
    """Local reads all signals, returns entries, deletes consumed signals."""
    signals_dir = vault_root / "Signals"
    if not signals_dir.exists():
        return []

    entries = []
    for sig in sorted(signals_dir.glob("*.md")):
        content = sig.read_text()
        # Extract the body (after the second ---)
        parts = content.split("---")
        body = parts[-1].strip() if len(parts) >= 3 else content.strip()
        entries.append(f"- **{sig.stem}**: {body[:100]}")
        sig.unlink()
        logger.debug(f"Signal consumed: {sig.name}")

    return entries


def read_health_status(vault_root: Path) -> str:
    """Read the health status file from Updates/."""
    health_file = vault_root / "Updates" / "health_status.md"
    if health_file.exists():
        return health_file.read_text()
    return ""
