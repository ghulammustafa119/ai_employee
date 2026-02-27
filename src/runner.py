import time
import logging

from src.config import CHECK_INTERVAL
from src.brain import get_pending_tasks, get_approved_tasks, get_rejected_tasks, process_task, process_approved, process_rejected
from src.dashboard import update_dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("AI Employee Runner started")
    logger.info(f"Checking every {CHECK_INTERVAL} seconds")

    while True:
        # 1. Process new tasks from Needs_Action
        tasks = get_pending_tasks()
        if tasks:
            logger.info(f"Found {len(tasks)} new task(s)")
            for task in tasks:
                try:
                    process_task(task)
                except Exception as e:
                    logger.error(f"Failed to process {task.name}: {e}")

        # 2. Process approved tasks from Approved
        approved = get_approved_tasks()
        if approved:
            logger.info(f"Found {len(approved)} approved task(s)")
            for task in approved:
                try:
                    process_approved(task)
                except Exception as e:
                    logger.error(f"Failed to execute approved {task.name}: {e}")

        # 3. Process rejected tasks from Rejected
        rejected = get_rejected_tasks()
        if rejected:
            logger.info(f"Found {len(rejected)} rejected task(s)")
            for task in rejected:
                try:
                    process_rejected(task)
                except Exception as e:
                    logger.error(f"Failed to process rejected {task.name}: {e}")

        # 4. Update dashboard
        try:
            update_dashboard()
        except Exception as e:
            logger.error(f"Failed to update dashboard: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
