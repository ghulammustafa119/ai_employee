import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
VAULT_PATH = BASE_DIR / os.getenv("VAULT_PATH", "vault")

# Vault folders
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
PLANS = VAULT_PATH / "Plans"
DONE = VAULT_PATH / "Done"
LOGS = VAULT_PATH / "Logs"
INBOX = VAULT_PATH / "Inbox"
PENDING_APPROVAL = VAULT_PATH / "Pending_Approval"
APPROVED = VAULT_PATH / "Approved"
REJECTED = VAULT_PATH / "Rejected"
BRIEFINGS = VAULT_PATH / "Briefings"
ACCOUNTING = VAULT_PATH / "Accounting"

# Vault files
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
HANDBOOK_FILE = VAULT_PATH / "Company_Handbook.md"
BUSINESS_GOALS_FILE = VAULT_PATH / "Business_Goals.md"

# General settings
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "10"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Gmail Watcher settings
GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "token.json")
GMAIL_CHECK_INTERVAL = int(os.getenv("GMAIL_CHECK_INTERVAL", "120"))

# WhatsApp Watcher settings
WHATSAPP_SESSION_PATH = os.getenv("WHATSAPP_SESSION_PATH", ".whatsapp_session")
WHATSAPP_CHECK_INTERVAL = int(os.getenv("WHATSAPP_CHECK_INTERVAL", "30"))
WHATSAPP_KEYWORDS = os.getenv(
    "WHATSAPP_KEYWORDS", "urgent,asap,invoice,payment,help"
).split(",")

# LinkedIn settings
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# Facebook / Instagram (Meta Graph API) settings
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_PAGE_ID = os.getenv("META_PAGE_ID", "")
META_INSTAGRAM_ACCOUNT_ID = os.getenv("META_INSTAGRAM_ACCOUNT_ID", "")

# Twitter / X API settings
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")

# Odoo Community (JSON-RPC) settings
ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")

# CEO Briefing settings
BRIEFING_DAY = os.getenv("BRIEFING_DAY", "Monday")

# Platinum Tier settings
AGENT_ROLE = os.getenv("AGENT_ROLE", "local")
VAULT_CLOUD_PATH = BASE_DIR / os.getenv("VAULT_CLOUD_PATH", "vault_cloud")
VAULT_LOCAL_PATH = BASE_DIR / os.getenv("VAULT_LOCAL_PATH", "vault_local")
VAULT_SYNC_PATH = BASE_DIR / os.getenv("VAULT_SYNC_PATH", "vault_sync.git")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "5"))
WATCHDOG_INTERVAL = int(os.getenv("WATCHDOG_INTERVAL", "30"))
DOMAINS = ["email", "social", "accounting", "general"]

# Sensitive action keywords (trigger approval)
SENSITIVE_KEYWORDS = [
    "payment", "invoice", "transfer", "send money",
    "delete", "remove", "cancel",
    "reply", "respond", "message",
    "post", "publish", "share",
]


def ensure_vault_structure() -> None:
    """Create all required vault folders if they don't exist."""
    folders = [
        NEEDS_ACTION, PLANS, DONE, LOGS, INBOX,
        PENDING_APPROVAL, APPROVED, REJECTED,
        BRIEFINGS, ACCOUNTING,
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
