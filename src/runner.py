import time
import logging

from src.config import CHECK_INTERVAL, ensure_vault_structure
from src.brain import (
    get_pending_tasks, get_approved_tasks, get_rejected_tasks,
    process_task, process_approved, process_rejected,
)
from src.dashboard import update_dashboard
from src.retry_handler import graceful_degrade
from src.ceo_briefing import maybe_generate_briefing
from src.social_media.facebook_poster import process_approved_facebook_post
from src.social_media.instagram_poster import process_approved_instagram_post
from src.social_media.twitter_poster import process_approved_tweet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def process_social_media_approvals(approved_files):
    """Route approved social media posts to their respective handlers."""
    for task in approved_files:
        name = task.name.upper()
        try:
            if name.startswith("FACEBOOK_"):
                process_approved_facebook_post(task)
            elif name.startswith("INSTAGRAM_"):
                process_approved_instagram_post(task)
            elif name.startswith("TWEET_"):
                process_approved_tweet(task)
        except Exception as e:
            logger.error(f"Failed to process social media post {task.name}: {e}")


def main():
    ensure_vault_structure()
    logger.info("AI Employee Runner started (Gold Tier)")
    logger.info(f"Checking every {CHECK_INTERVAL} seconds")

    while True:
        # 1. Process new tasks from Needs_Action
        with graceful_degrade("task_processor"):
            tasks = get_pending_tasks()
            if tasks:
                logger.info(f"Found {len(tasks)} new task(s)")
                for task in tasks:
                    try:
                        process_task(task)
                    except Exception as e:
                        logger.error(f"Failed to process {task.name}: {e}")

        # 2. Process approved tasks from Approved
        with graceful_degrade("approval_processor"):
            approved = get_approved_tasks()
            if approved:
                logger.info(f"Found {len(approved)} approved task(s)")

                # Separate social media posts from general tasks
                social_posts = [t for t in approved if any(
                    t.name.upper().startswith(p)
                    for p in ("FACEBOOK_", "INSTAGRAM_", "TWEET_", "LINKEDIN_")
                )]
                general_tasks = [t for t in approved if t not in social_posts]

                # Process general approved tasks
                for task in general_tasks:
                    try:
                        process_approved(task)
                    except Exception as e:
                        logger.error(f"Failed to execute approved {task.name}: {e}")

                # Process social media posts
                process_social_media_approvals(social_posts)

                # Handle LinkedIn posts (existing flow)
                for task in social_posts:
                    if task.name.upper().startswith("LINKEDIN_"):
                        try:
                            from src.linkedin_poster import process_approved_linkedin_post
                            process_approved_linkedin_post(task)
                        except Exception as e:
                            logger.error(f"Failed to post LinkedIn {task.name}: {e}")

        # 3. Process rejected tasks from Rejected
        with graceful_degrade("rejection_processor"):
            rejected = get_rejected_tasks()
            if rejected:
                logger.info(f"Found {len(rejected)} rejected task(s)")
                for task in rejected:
                    try:
                        process_rejected(task)
                    except Exception as e:
                        logger.error(f"Failed to process rejected {task.name}: {e}")

        # 4. Update dashboard
        with graceful_degrade("dashboard"):
            update_dashboard()

        # 5. CEO Briefing (runs on scheduled day only)
        with graceful_degrade("ceo_briefing"):
            briefing = maybe_generate_briefing()
            if briefing:
                logger.info(f"CEO Briefing generated: {briefing}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
