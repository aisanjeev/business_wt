"""Logging configuration and utilities."""

import logging
import sys
from typing import Optional

from app.config import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """Setup application logging.
    
    Args:
        log_level: Log level string (debug, info, warning, error, critical).
        log_format: Custom log format string.
    
    Returns:
        Configured logger instance.
    """
    level = log_level or settings.log_level.upper()
    
    # Default format with timestamp, level, module, and message
    default_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "[%(filename)s:%(lineno)d] - %(message)s"
    )
    format_str = log_format or default_format
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level),
        format=format_str,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    # Get application logger
    logger = logging.getLogger("whatsapp_chat")
    logger.setLevel(getattr(logging, level))
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.db_echo else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.
    
    Args:
        name: Logger name, typically __name__ of the module.
    
    Returns:
        Logger instance.
    """
    return logging.getLogger(f"whatsapp_chat.{name}")


# Create default logger
logger = setup_logging()
