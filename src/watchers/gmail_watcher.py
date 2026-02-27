import base64
from datetime import datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from src.watchers.base_watcher import BaseWatcher
from src.config import GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, GMAIL_CHECK_INTERVAL

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailWatcher(BaseWatcher):
    """Watches Gmail for unread important emails and creates action files."""

    def __init__(self):
        super().__init__(check_interval=GMAIL_CHECK_INTERVAL)
        self.service = self._authenticate()

    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
        creds = None
        token_path = Path(GMAIL_TOKEN_PATH)
        creds_path = Path(GMAIL_CREDENTIALS_PATH)

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not creds_path.exists():
                    self.logger.error(
                        f"Gmail credentials file not found: {creds_path}\n"
                        "Download it from Google Cloud Console → APIs → Credentials"
                    )
                    raise FileNotFoundError(f"Missing {creds_path}")
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)

            token_path.write_text(creds.to_json())
            self.logger.info("Gmail authentication successful")

        return build("gmail", "v1", credentials=creds)

    def check_for_updates(self) -> list:
        """Fetch unread important emails."""
        results = self.service.users().messages().list(
            userId="me", q="is:unread is:important", maxResults=10
        ).execute()
        messages = results.get("messages", [])
        return [m for m in messages if not self.is_duplicate(m["id"])]

    def create_action_file(self, message) -> Path:
        """Create .md action file from email."""
        msg = self.service.users().messages().get(
            userId="me", id=message["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        sender = headers.get("From", "Unknown")
        subject = headers.get("Subject", "No Subject")
        date = headers.get("Date", "")
        snippet = msg.get("snippet", "")

        # Try to get body text
        body = snippet
        if "parts" in msg["payload"]:
            for part in msg["payload"]["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break

        content = f"""---
type: email
from: {sender}
subject: {subject}
received: {datetime.now().isoformat()}
priority: high
status: pending
---

## Email from {sender}

**Subject:** {subject}
**Date:** {date}

## Content
{body}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing
"""
        safe_id = message["id"][:16]
        filepath = self.needs_action / f"EMAIL_{safe_id}.md"
        filepath.write_text(content)
        self.mark_processed(message["id"])
        self.logger.info(f"Email action created: {subject} from {sender}")
        return filepath


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    watcher = GmailWatcher()
    watcher.run()
