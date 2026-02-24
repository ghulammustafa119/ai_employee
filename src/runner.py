import time
import logging

from src.config import CHECK_INTERVAL
from src.brain import get_pending_tasks, process_task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("AI Employee Runner started")
    logger.info(f"Checking every {CHECK_INTERVAL} seconds")

    while True:
        tasks = get_pending_tasks()
        if tasks:
            logger.info(f"Found {len(tasks)} task(s)")
            for task in tasks:
                try:
                    process_task(task)
                except Exception as e:
                    logger.error(f"Failed to process {task.name}: {e}")
        else:
            logger.debug("No tasks found")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
