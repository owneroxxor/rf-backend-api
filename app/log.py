import sys
import threading
from logging import StreamHandler, Logger, getLogger

from json_log_formatter import VerboseJSONFormatter
from useful.logs.exception_hooks import (
    except_logging,
    threading_except_logging,
    unraisable_logging,
)


def get_logger(name: str = None) -> Logger:
    """Use this to log inside application modules."""
    if not sys.excepthook is except_logging:
        # hook root logger
        logger = getLogger()
        logger.setLevel("INFO")
        logger.handlers
        log_handlers = [
            StreamHandler(sys.stdout),
        ]
        for handler in log_handlers:
            handler.setFormatter(VerboseJSONFormatter())
            handler.setLevel("INFO")
        # hook exception handlers
        logger.handlers = log_handlers
        sys.excepthook = except_logging
        sys.unraisablehook = unraisable_logging
        if sys.version_info >= (3, 8, 0):
            threading.excepthook = threading_except_logging
    return getLogger(name)
