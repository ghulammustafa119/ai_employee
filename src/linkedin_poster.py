import logging
import shutil
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.config import (
    PENDING_APPROVAL, APPROVED, DONE, LOGS,
    LINKEDIN_EMAIL, LINKEDIN_PASSWORD, GROQ_API_KEY,
)
from src.brain import call_llm, log_action

logger = logging.getLogger(__name__)

LINKEDIN_POST_PROMPT = """You are a professional LinkedIn content creator for a business.

Generate a LinkedIn post that:
- Is professional and engaging
- Promotes business expertise and services
- Includes relevant hashtags (3-5)
- Is 150-300 words
- Has a compelling hook in the first line
- Ends with a call-to-action

Topic/context will be provided by the user.
Output ONLY the post text, nothing else.
"""


def generate_linkedin_post(topic: str) -> str:
    """Use AI to generate a LinkedIn post."""
    return call_llm(
        LINKEDIN_POST_PROMPT,
        f"Generate a LinkedIn post about: {topic}",
        max_tokens=1024,
    )


def create_post_for_approval(topic: str) -> Path:
    """Generate a LinkedIn post and send to approval queue."""
    post_content = generate_linkedin_post(topic)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    approval_content = f"""---
type: linkedin_post
created: {datetime.now().isoformat()}
status: pending_approval
topic: {topic}
---

## LinkedIn Post (Pending Approval)

{post_content}

## Instructions
- **To approve and post:** Move this file to `Approved/` folder
- **To reject:** Move this file to `Rejected/` folder
- **To edit:** Modify the post content above, then move to `Approved/`
"""
    filepath = PENDING_APPROVAL / f"LINKEDIN_{timestamp}.md"
    filepath.write_text(approval_content)
    log_action(f"linkedin_{timestamp}", "post_generated", "pending_approval")
    logger.info(f"LinkedIn post created for approval: {filepath.name}")
    return filepath


def post_to_linkedin(post_text: str) -> bool:
    """Post to LinkedIn using Playwright browser automation."""
    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        logger.error("LinkedIn credentials not set in .env")
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # Login to LinkedIn
            page.goto("https://www.linkedin.com/login")
            page.fill("#username", LINKEDIN_EMAIL)
            page.fill("#password", LINKEDIN_PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url("**/feed/**", timeout=30000)
            logger.info("LinkedIn login successful")

            # Create a new post
            page.click('button:has-text("Start a post")')
            page.wait_for_selector('div[role="textbox"]', timeout=10000)
            page.click('div[role="textbox"]')
            page.keyboard.type(post_text, delay=20)
            page.wait_for_timeout(1000)

            # Click Post button
            post_btn = page.locator('button.share-actions__primary-action')
            if not post_btn.is_visible():
                post_btn = page.locator('button:has-text("Post")')
            post_btn.click()

            # Wait for post modal to close (confirms post was submitted)
            try:
                page.wait_for_selector('div[role="textbox"]', state="hidden", timeout=15000)
                logger.info("Post modal closed - post submitted")
            except Exception:
                logger.info("Waiting extra time for post to submit...")
            page.wait_for_timeout(10000)

            browser.close()
            logger.info("LinkedIn post published successfully!")
            return True

    except Exception as e:
        logger.error(f"Failed to post to LinkedIn: {e}")
        return False


def process_approved_linkedin_post(approved_file: Path) -> None:
    """Execute an approved LinkedIn post."""
    content = approved_file.read_text()
    task_name = approved_file.stem

    # Extract post text (between the header and instructions)
    lines = content.split("\n")
    post_lines = []
    in_post = False
    for line in lines:
        if line.startswith("## LinkedIn Post"):
            in_post = True
            continue
        if line.startswith("## Instructions"):
            break
        if in_post:
            post_lines.append(line)

    post_text = "\n".join(post_lines).strip()

    if not post_text:
        logger.error(f"No post content found in {approved_file.name}")
        return

    success = post_to_linkedin(post_text)

    if success:
        log_action(task_name, "linkedin_posted", "success")
        shutil.move(str(approved_file), str(DONE / approved_file.name))
    else:
        log_action(task_name, "linkedin_post_failed", "error")


if __name__ == "__main__":
    import shutil
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Generate a test post
    topic = "How AI is transforming small businesses in 2026"
    create_post_for_approval(topic)
    print(f"Post generated! Check vault/Pending_Approval/ for the post.")
