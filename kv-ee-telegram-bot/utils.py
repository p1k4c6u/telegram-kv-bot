import os
import sys


def setup_logging():
    """Setup logging configuration"""
    import logging
    from logging.handlers import RotatingFileHandler

    # Get log level from environment
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                "bot.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
            ),
        ],
    )

    # Set logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at level: {log_level_str}")
    return logger


logger = setup_logging()


# Global flag for notifications
def set_notifications_enabled(enabled: bool):
    """Enable or disable notifications"""
    global _notifications_enabled
    _notifications_enabled = enabled
    logger.info(f"Notifications {'enabled' if enabled else 'disabled'}")


def get_notifications_enabled() -> bool:
    """Get current notification status"""
    return _notifications_enabled


# Initialize notification flag
_notifications_enabled = True
