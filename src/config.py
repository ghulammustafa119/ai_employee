import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
VAULT_PATH = BASE_DIR / os.getenv("VAULT_PATH", "vault")

NEEDS_ACTION = VAULT_PATH / "Needs_Action"
PLANS = VAULT_PATH / "Plans"
DONE = VAULT_PATH / "Done"
LOGS = VAULT_PATH / "Logs"

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "10"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
