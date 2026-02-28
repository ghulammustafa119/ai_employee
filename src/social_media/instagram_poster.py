import logging
import random
import shutil
from datetime import datetime
from pathlib import Path

from src.config import PENDING_APPROVAL, DONE, META_ACCESS_TOKEN, META_INSTAGRAM_ACCOUNT_ID
from src.brain import call_llm, log_action

logger = logging.getLogger(__name__)

INSTAGRAM_POST_PROMPT = """You are a professional Instagram content creator for a business account.

Generate an Instagram caption that:
- Is visually descriptive and engaging
- Uses line breaks for readability
- Includes relevant hashtags (5-10) at the end
- Is 100-200 words (excluding hashtags)
- Has a compelling hook in the first line
- Includes a call-to-action

Topic/context will be provided by the user.
Output ONLY the caption text, nothing else.
"""


class MockInstagramAPI:
    """Mock Instagram Graph API. Replace with real API calls later."""

    def __init__(self, access_token: str = "", account_id: str = ""):
        self.access_token = access_token or META_ACCESS_TOKEN
        self.account_id = account_id or META_INSTAGRAM_ACCOUNT_ID
        self._posts: list[dict] = []

    def publish_post(self, caption: str, image_url: str = "") -> dict:
        """Mock: Publish a post to Instagram."""
        post_id = f"ig_{random.randint(1000000, 9999999)}"
        post = {
            "id": post_id,
            "caption": caption,
            "image_url": image_url,
            "created_time": datetime.now().isoformat(),
            "status": "published",
        }
        self._posts.append(post)
        return post

    def get_insights(self) -> dict:
        """Mock: Return account engagement metrics."""
        return {
            "followers": random.randint(500, 10000),
            "reach": random.randint(1000, 15000),
            "impressions": random.randint(2000, 20000),
            "profile_views": random.randint(50, 500),
            "period": "last_7_days",
        }

    def get_recent_media(self, limit: int = 10) -> list[dict]:
        """Mock: Return recent media with engagement data."""
        media = []
        for i in range(min(limit, 5)):
            media.append({
                "id": f"ig_{random.randint(1000000, 9999999)}",
                "caption": f"Mock post {i + 1}",
                "likes": random.randint(10, 200),
                "comments": random.randint(0, 50),
                "saves": random.randint(0, 30),
                "reach": random.randint(200, 3000),
            })
        return media


_api = MockInstagramAPI()


def generate_instagram_post(topic: str) -> str:
    """Use AI to generate an Instagram caption."""
    return call_llm(
        INSTAGRAM_POST_PROMPT,
        f"Generate an Instagram caption about: {topic}",
        max_tokens=1024,
    )


def create_instagram_post_for_approval(topic: str) -> Path:
    """Generate an Instagram post and send to approval queue."""
    post_content = generate_instagram_post(topic)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    approval_content = f"""---
type: instagram_post
created: {datetime.now().isoformat()}
status: pending_approval
topic: {topic}
---

## Instagram Post (Pending Approval)

{post_content}

## Instructions
- **To approve and post:** Move this file to `Approved/` folder
- **To reject:** Move this file to `Rejected/` folder
- **To edit:** Modify the caption above, then move to `Approved/`
"""
    filepath = PENDING_APPROVAL / f"INSTAGRAM_{timestamp}.md"
    filepath.write_text(approval_content)
    log_action(f"instagram_{timestamp}", "post_generated", "pending_approval")
    logger.info(f"Instagram post created for approval: {filepath.name}")
    return filepath


def post_to_instagram(caption: str, image_url: str = "") -> bool:
    """Post to Instagram using the mock API."""
    try:
        result = _api.publish_post(caption, image_url)
        logger.info(f"Instagram post published: {result['id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to post to Instagram: {e}")
        return False


def get_instagram_summary() -> str:
    """Generate a summary of Instagram activity."""
    insights = _api.get_insights()
    media = _api.get_recent_media(5)

    total_likes = sum(m["likes"] for m in media)
    total_comments = sum(m["comments"] for m in media)
    total_saves = sum(m["saves"] for m in media)

    return f"""### Instagram Summary
- **Followers:** {insights['followers']}
- **Reach (7d):** {insights['reach']}
- **Impressions (7d):** {insights['impressions']}
- **Recent Posts:** {len(media)}
  - Total Likes: {total_likes}
  - Total Comments: {total_comments}
  - Total Saves: {total_saves}
"""


def process_approved_instagram_post(approved_file: Path) -> None:
    """Execute an approved Instagram post."""
    content = approved_file.read_text()
    task_name = approved_file.stem

    lines = content.split("\n")
    post_lines = []
    in_post = False
    for line in lines:
        if line.startswith("## Instagram Post"):
            in_post = True
            continue
        if line.startswith("## Instructions"):
            break
        if in_post:
            post_lines.append(line)

    caption = "\n".join(post_lines).strip()
    if not caption:
        logger.error(f"No caption found in {approved_file.name}")
        return

    success = post_to_instagram(caption)
    if success:
        log_action(task_name, "instagram_posted", "success")
        shutil.move(str(approved_file), str(DONE / approved_file.name))
    else:
        log_action(task_name, "instagram_post_failed", "error")
