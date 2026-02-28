import logging
import random
import shutil
from datetime import datetime
from pathlib import Path

from src.config import (
    PENDING_APPROVAL, DONE,
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET,
)
from src.brain import call_llm, log_action

logger = logging.getLogger(__name__)

TWEET_PROMPT = """You are a professional Twitter/X content creator for a business.

Generate a tweet that:
- Is under 280 characters (STRICT limit)
- Is punchy and engaging
- Includes 1-3 relevant hashtags
- Has a clear message or call-to-action
- Uses professional but approachable tone

Topic/context will be provided by the user.
Output ONLY the tweet text, nothing else. Must be under 280 characters.
"""


class MockTwitterAPI:
    """Mock Twitter/X API v2. Replace with real API calls later."""

    def __init__(self):
        self._tweets: list[dict] = []

    def create_tweet(self, text: str) -> dict:
        """Mock: Post a tweet."""
        if len(text) > 280:
            text = text[:277] + "..."
        tweet_id = str(random.randint(1000000000, 9999999999))
        tweet = {
            "id": tweet_id,
            "text": text,
            "created_at": datetime.now().isoformat(),
            "status": "published",
        }
        self._tweets.append(tweet)
        return tweet

    def get_tweet_analytics(self, tweet_id: str = "") -> dict:
        """Mock: Return tweet engagement metrics."""
        return {
            "impressions": random.randint(100, 5000),
            "likes": random.randint(5, 100),
            "retweets": random.randint(0, 30),
            "replies": random.randint(0, 20),
            "clicks": random.randint(10, 200),
        }

    def get_account_metrics(self) -> dict:
        """Mock: Return account-level metrics."""
        return {
            "followers": random.randint(200, 5000),
            "following": random.randint(100, 1000),
            "tweet_count": random.randint(50, 500),
            "impressions_28d": random.randint(5000, 50000),
        }


_api = MockTwitterAPI()


def generate_tweet(topic: str) -> str:
    """Use AI to generate a tweet."""
    return call_llm(
        TWEET_PROMPT,
        f"Generate a tweet about: {topic}",
        max_tokens=256,
    )


def create_tweet_for_approval(topic: str) -> Path:
    """Generate a tweet and send to approval queue."""
    tweet_content = generate_tweet(topic)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    approval_content = f"""---
type: tweet
created: {datetime.now().isoformat()}
status: pending_approval
topic: {topic}
char_count: {len(tweet_content)}
---

## Tweet (Pending Approval)

{tweet_content}

## Instructions
- **To approve and post:** Move this file to `Approved/` folder
- **To reject:** Move this file to `Rejected/` folder
- **To edit:** Modify the tweet above (keep under 280 chars), then move to `Approved/`
"""
    filepath = PENDING_APPROVAL / f"TWEET_{timestamp}.md"
    filepath.write_text(approval_content)
    log_action(f"tweet_{timestamp}", "tweet_generated", "pending_approval")
    logger.info(f"Tweet created for approval: {filepath.name}")
    return filepath


def post_tweet(text: str) -> bool:
    """Post a tweet using the mock API."""
    try:
        result = _api.create_tweet(text)
        logger.info(f"Tweet posted: {result['id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to post tweet: {e}")
        return False


def get_twitter_summary() -> str:
    """Generate a summary of Twitter activity."""
    metrics = _api.get_account_metrics()

    return f"""### Twitter/X Summary
- **Followers:** {metrics['followers']}
- **Following:** {metrics['following']}
- **Total Tweets:** {metrics['tweet_count']}
- **Impressions (28d):** {metrics['impressions_28d']}
"""


def process_approved_tweet(approved_file: Path) -> None:
    """Execute an approved tweet."""
    content = approved_file.read_text()
    task_name = approved_file.stem

    lines = content.split("\n")
    tweet_lines = []
    in_tweet = False
    for line in lines:
        if line.startswith("## Tweet"):
            in_tweet = True
            continue
        if line.startswith("## Instructions"):
            break
        if in_tweet:
            tweet_lines.append(line)

    tweet_text = "\n".join(tweet_lines).strip()
    if not tweet_text:
        logger.error(f"No tweet content found in {approved_file.name}")
        return

    success = post_tweet(tweet_text)
    if success:
        log_action(task_name, "tweet_posted", "success")
        shutil.move(str(approved_file), str(DONE / approved_file.name))
    else:
        log_action(task_name, "tweet_post_failed", "error")
