import os
import logging
from logging.handlers import RotatingFileHandler

_LOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_FILE_PATH = os.path.join(_LOG_DIR, "error_log.txt")

# Create logger
logger = logging.getLogger("rag_backend_errors")
logger.setLevel(logging.ERROR)

# Ensure rotating handler is added only once
if not logger.handlers:
    handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def log_error(msg: str, exc: Exception = None):
    """
    Log an error message to error_log.txt with rotating file handler.
    """
    if exc:
        logger.error(msg, exc_info=exc)
    else:
        logger.error(msg)
