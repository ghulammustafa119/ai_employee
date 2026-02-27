from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.watchers.base_watcher import BaseWatcher
from src.config import WHATSAPP_SESSION_PATH, WHATSAPP_CHECK_INTERVAL, WHATSAPP_KEYWORDS


class WhatsAppWatcher(BaseWatcher):
    """Watches WhatsApp Web for unread messages with keywords."""

    def __init__(self):
        super().__init__(check_interval=WHATSAPP_CHECK_INTERVAL)
        self.session_path = Path(WHATSAPP_SESSION_PATH)
        self.keywords = [kw.strip().lower() for kw in WHATSAPP_KEYWORDS]
        self.playwright = None
        self.browser = None
        self.page = None

    def _ensure_browser(self):
        """Launch or reuse persistent browser session."""
        if self.page is None:
            self.logger.info("Launching WhatsApp Web browser...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch_persistent_context(
                str(self.session_path),
                headless=False,  # Need visible browser for QR scan
            )
            self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
            self.page.goto("https://web.whatsapp.com")
            self.logger.info("Waiting for WhatsApp Web to load (scan QR if first time)...")
            self.page.wait_for_selector('[data-testid="chat-list"]', timeout=120000)
            self.logger.info("WhatsApp Web connected!")

    def check_for_updates(self) -> list:
        """Find unread chats with keyword matches."""
        self._ensure_browser()
        messages = []

        try:
            # Find all unread chat items
            unread_chats = self.page.query_selector_all(
                'div[data-testid="cell-frame-container"] span[aria-label*="unread"]'
            )

            for badge in unread_chats:
                try:
                    # Navigate up to the chat container
                    chat = badge.evaluate_handle(
                        "el => el.closest('[data-testid=\"cell-frame-container\"]')"
                    )
                    if not chat:
                        continue

                    # Get chat name and last message preview
                    name_el = chat.as_element().query_selector("span[title]")
                    preview_el = chat.as_element().query_selector("span[class*='matched-text']")

                    name = name_el.get_attribute("title") if name_el else "Unknown"
                    preview = preview_el.inner_text() if preview_el else ""

                    chat_id = f"wa_{name}_{datetime.now().strftime('%Y%m%d%H%M')}"

                    if self.is_duplicate(chat_id):
                        continue

                    # Check if message contains keywords
                    text_lower = f"{name} {preview}".lower()
                    matched_keywords = [kw for kw in self.keywords if kw in text_lower]

                    if matched_keywords:
                        messages.append({
                            "id": chat_id,
                            "name": name,
                            "preview": preview,
                            "keywords": matched_keywords,
                        })
                except Exception as e:
                    self.logger.debug(f"Error reading chat: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error scanning chats: {e}")

        return messages

    def create_action_file(self, item) -> Path:
        """Create .md action file from WhatsApp message."""
        content = f"""---
type: whatsapp
from: {item['name']}
received: {datetime.now().isoformat()}
keywords: {', '.join(item['keywords'])}
priority: high
status: pending
---

## WhatsApp Message from {item['name']}

**Preview:** {item['preview']}

**Matched Keywords:** {', '.join(item['keywords'])}

## Suggested Actions
- [ ] Reply to {item['name']}
- [ ] Forward to relevant party
- [ ] Mark as handled
"""
        safe_name = "".join(c if c.isalnum() else "_" for c in item["name"])[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.needs_action / f"WHATSAPP_{safe_name}_{timestamp}.md"
        filepath.write_text(content)
        self.mark_processed(item["id"])
        self.logger.info(f"WhatsApp action created: {item['name']} ({item['keywords']})")
        return filepath

    def cleanup(self):
        """Close browser on shutdown."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    watcher = WhatsAppWatcher()
    try:
        watcher.run()
    except KeyboardInterrupt:
        watcher.cleanup()
