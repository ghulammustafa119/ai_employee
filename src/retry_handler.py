import time
import logging
from enum import Enum
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    TRANSIENT = "transient"
    AUTHENTICATION = "authentication"
    LOGIC = "logic"
    DATA = "data"
    SYSTEM = "system"


class TransientError(Exception):
    """Retriable error (network timeout, API rate limit)."""
    pass


class AuthenticationError(Exception):
    """Credential/token error — alert human."""
    pass


class DataError(Exception):
    """Corrupted or missing data — quarantine."""
    pass


def categorize_error(error: Exception) -> ErrorCategory:
    """Classify an exception into an error category."""
    if isinstance(error, TransientError):
        return ErrorCategory.TRANSIENT
    if isinstance(error, AuthenticationError):
        return ErrorCategory.AUTHENTICATION
    if isinstance(error, DataError):
        return ErrorCategory.DATA
    if isinstance(error, (FileNotFoundError, KeyError, ValueError)):
        return ErrorCategory.DATA
    if isinstance(error, (ConnectionError, TimeoutError, OSError)):
        return ErrorCategory.TRANSIENT
    return ErrorCategory.SYSTEM


def with_retry(max_attempts: int = 3, base_delay: float = 1, max_delay: float = 60):
    """Decorator: retry on TransientError with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (TransientError, ConnectionError, TimeoutError) as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    time.sleep(delay)
        return wrapper
    return decorator


@contextmanager
def graceful_degrade(service_name: str, fallback_fn=None):
    """Context manager: catch errors and optionally run a fallback."""
    try:
        yield
    except AuthenticationError as e:
        logger.error(f"[{service_name}] Auth error — pausing service: {e}")
        if fallback_fn:
            fallback_fn(service_name, e)
    except TransientError as e:
        logger.warning(f"[{service_name}] Transient error — will retry later: {e}")
        if fallback_fn:
            fallback_fn(service_name, e)
    except DataError as e:
        logger.error(f"[{service_name}] Data error — quarantining: {e}")
        if fallback_fn:
            fallback_fn(service_name, e)
    except Exception as e:
        category = categorize_error(e)
        logger.error(f"[{service_name}] {category.value} error: {e}")
        if fallback_fn:
            fallback_fn(service_name, e)
