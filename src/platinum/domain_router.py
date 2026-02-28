"""Route tasks to the correct domain subfolder."""

from pathlib import Path


def detect_platinum_domain(task_content: str, filename: str = "") -> str:
    """Map task to a Platinum domain subfolder name."""
    content_lower = task_content.lower()
    name_lower = filename.lower()

    # Filename prefix takes priority
    if name_lower.startswith("email_"):
        return "email"
    if any(name_lower.startswith(p) for p in ("facebook_", "instagram_", "tweet_", "linkedin_")):
        return "social"
    if any(name_lower.startswith(p) for p in ("invoice_", "payment_", "accounting_")):
        return "accounting"

    # Content keyword matching
    if any(kw in content_lower for kw in ("invoice", "payment", "accounting", "budget", "expense")):
        return "accounting"
    if any(kw in content_lower for kw in ("email", "reply", "respond", "forward", "inbox")):
        return "email"
    if any(kw in content_lower for kw in ("post", "publish", "schedule", "social", "tweet", "linkedin")):
        return "social"

    return "general"


def route_to_domain_folder(base_folder: Path, task_content: str, filename: str) -> Path:
    """Return the domain subfolder path under a workflow directory."""
    domain = detect_platinum_domain(task_content, filename)
    target = base_folder / domain
    target.mkdir(parents=True, exist_ok=True)
    return target
