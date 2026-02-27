import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod

from src.config import NEEDS_ACTION


class BaseWatcher(ABC):
    """Abstract base class for all watchers."""

    def __init__(self, check_interval: int = 60):
        self.needs_action = NEEDS_ACTION
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        self.processed_ids: set[str] = set()

    @abstractmethod
    def check_for_updates(self) -> list:
        """Return list of new items to process."""
        pass

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """Create .md file in Needs_Action folder."""
        pass

    def is_duplicate(self, item_id: str) -> bool:
        """Check if item was already processed."""
        if item_id in self.processed_ids:
            self.logger.debug(f"Skipping duplicate: {item_id}")
            return True
        return False

    def mark_processed(self, item_id: str) -> None:
        """Mark an item as processed."""
        self.processed_ids.add(item_id)

    def run(self):
        """Main loop — poll for updates and create action files."""
        self.logger.info(f"Starting {self.__class__.__name__} (interval: {self.check_interval}s)")
        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    try:
                        self.create_action_file(item)
                    except Exception as e:
                        self.logger.error(f"Failed to create action file: {e}")
            except Exception as e:
                self.logger.error(f"Error checking updates: {e}")
            time.sleep(self.check_interval)
