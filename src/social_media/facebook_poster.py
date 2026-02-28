import logging
import random
import shutil
from datetime import datetime
from pathlib import Path

from src.config import PENDING_APPROVAL, DONE, META_ACCESS_TOKEN, META_PAGE_ID
from src.brain import call_llm, log_action

logger = logging.getLogger(__name__)

FACEBOOK_POST_PROMPT = """You are a professional Facebook content creator for a business page.

Generate a Facebook post that:
- Is engaging and conversational
- Promotes business expertise and services
- Includes relevant hashtags (3-5)
- Is 100-250 words
- Has a compelling opening line
- Ends with a call-to-action or question to boost engagement

Topic/context will be provided by the user.
Output ONLY the post text, nothing else.
"""


class MockFacebookAPI:
    """Mock Meta Graph API for Facebook. Replace with real API calls later."""

    def __init__(self, access_token: str = "", page_id: str = ""):
        self.access_token = access_token or META_ACCESS_TOKEN
        self.page_id = page_id or META_PAGE_ID
        self._posts: list[dict] = []

    def publish_post(self, message: str, image_url: str | None = None) -> dict:
        """Mock: Publish a post to a Facebook page."""
        post_id = f"{self.page_id}_{random.randint(100000, 999999)}"
        post = {
            "id": post_id,
            "message": message,
            "image_url": image_url,
            "created_time": datetime.now().isoformat(),
            "status": "published",
        }
        self._posts.append(post)
        return post

    def get_page_insights(self) -> dict:
        """Mock: Return page engagement metrics."""
        return {
            "page_fans": random.randint(500, 5000),
            "page_views": random.randint(100, 1000),
            "post_engagements": random.randint(50, 500),
            "page_impressions": random.randint(1000, 10000),
            "period": "last_7_days",
        }

    def get_recent_posts(self, limit: int = 10) -> list[dict]:
        """Mock: Return recent posts with engagement data."""
        posts = []
        for i in range(min(limit, 5)):
            posts.append({
                "id": f"{self.page_id}_{random.randint(100000, 999999)}",
                "message": f"Mock post {i + 1}",
                "likes": random.randint(5, 100),
                "comments": random.randint(0, 30),
                "shares": random.randint(0, 20),
                "reach": random.randint(100, 2000),
            })
        return posts


_api = MockFacebookAPI()


def generate_facebook_post(topic: str) -> str:
    """Use AI to generate a Facebook post."""
    return call_llm(
        FACEBOOK_POST_PROMPT,
        f"Generate a Facebook post about: {topic}",
        max_tokens=1024,
    )


def create_facebook_post_for_approval(topic: str) -> Path:
    """Generate a Facebook post and send to approval queue."""
    post_content = generate_facebook_post(topic)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    approval_content = f"""---
type: facebook_post
created: {datetime.now().isoformat()}
status: pending_approval
topic: {topic}
---

## Facebook Post (Pending Approval)

{post_content}

## Instructions
- **To approve and post:** Move this file to `Approved/` folder
- **To reject:** Move this file to `Rejected/` folder
- **To edit:** Modify the post content above, then move to `Approved/`
"""
    filepath = PENDING_APPROVAL / f"FACEBOOK_{timestamp}.md"
    filepath.write_text(approval_content)
    log_action(f"facebook_{timestamp}", "post_generated", "pending_approval")
    logger.info(f"Facebook post created for approval: {filepath.name}")
    return filepath


def post_to_facebook(post_text: str, image_url: str | None = None) -> bool:
    """Post to Facebook using the mock API."""
    try:
        result = _api.publish_post(post_text, image_url)
        logger.info(f"Facebook post published: {result['id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to post to Facebook: {e}")
        return False


def get_facebook_summary() -> str:
    """Generate a summary of Facebook activity."""
    insights = _api.get_page_insights()
    posts = _api.get_recent_posts(5)

    total_likes = sum(p["likes"] for p in posts)
    total_comments = sum(p["comments"] for p in posts)
    total_shares = sum(p["shares"] for p in posts)

    return f"""### Facebook Summary
- **Page Fans:** {insights['page_fans']}
- **Page Views (7d):** {insights['page_views']}
- **Post Engagements (7d):** {insights['post_engagements']}
- **Recent Posts:** {len(posts)}
  - Total Likes: {total_likes}
  - Total Comments: {total_comments}
  - Total Shares: {total_shares}
"""


def process_approved_facebook_post(approved_file: Path) -> None:
    """Execute an approved Facebook post."""
    content = approved_file.read_text()
    task_name = approved_file.stem

    lines = content.split("\n")
    post_lines = []
    in_post = False
    for line in lines:
        if line.startswith("## Facebook Post"):
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

    success = post_to_facebook(post_text)
    if success:
        log_action(task_name, "facebook_posted", "success")
        shutil.move(str(approved_file), str(DONE / approved_file.name))
    else:
        log_action(task_name, "facebook_post_failed", "error")
