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

# Vault files
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
HANDBOOK_FILE = VAULT_PATH / "Company_Handbook.md"

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

# Sensitive action keywords (trigger approval)
SENSITIVE_KEYWORDS = [
    "payment", "invoice", "transfer", "send money",
    "delete", "remove", "cancel",
    "reply", "respond", "message",
    "post", "publish", "share",
]
