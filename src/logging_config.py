"""Logging setup shared by the API, bot, and scraper."""

import logging
from pathlib import Path

from src.config import BASE_DIR

LOG_DIR = BASE_DIR / "logs"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def _ensure_log_file(relative_path: str) -> Path:
    """Create the log directory and return the absolute log file path."""
    log_path = LOG_DIR / relative_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path


def configure_logging(service_name: str, log_file: str) -> logging.Logger:
    """Configure root logging for a runnable service."""
    service_log = _ensure_log_file(log_file)
    error_log = _ensure_log_file("errors/errors.log")

    formatter = logging.Formatter(LOG_FORMAT)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    service_handler = logging.FileHandler(service_log, encoding="utf-8")
    service_handler.setFormatter(formatter)

    error_handler = logging.FileHandler(error_log, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(service_handler)
    root_logger.addHandler(error_handler)

    return logging.getLogger(service_name)


def get_component_logger(name: str, log_file: str) -> logging.Logger:
    """Return a component logger that also writes to its own log file."""
    logger = logging.getLogger(name)
    log_path = _ensure_log_file(log_file)

    if not any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename) == log_path
        for handler in logger.handlers
    ):
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)

    logger.setLevel(logging.INFO)
    logger.propagate = True
    return logger
