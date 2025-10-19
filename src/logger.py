import sys
from contextvars import ContextVar
from typing import Optional
from uuid import uuid4

from loguru import logger

from src.config import config

# Context variable to store request UUID across async contexts
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> str:
    """Get the current request ID, or generate a new one if not set."""
    request_id = request_id_var.get()
    if request_id is None:
        request_id = str(uuid4())
        request_id_var.set(request_id)
    return request_id


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context."""
    request_id_var.set(request_id)


def reset_request_id() -> None:
    """Reset the request ID (useful for cleanup)."""
    request_id_var.set(None)


def format_log(record: dict) -> str:
    """Custom log format that includes request ID."""
    request_id = request_id_var.get()
    if request_id:
        # Include request ID in the log format
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>req:{extra[request_id]}</cyan> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>\n"
            "{exception}"
        )
    else:
        # Standard format without request ID
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>\n"
            "{exception}"
        )


def setup_logging() -> None:
    """Configure Loguru logging."""
    # Remove default handler
    logger.remove()

    # Add custom handler with request ID support
    logger.add(
        sys.stderr,
        format=lambda record: format_log(record),
        level=config.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Bind request_id_var to logger context
    logger.configure(
        patcher=lambda record: record["extra"].update(request_id=request_id_var.get() or "N/A")
    )


# Initialize logging on module import
setup_logging()
