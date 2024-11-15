"""Logging utils"""

import os
import sys
from datetime import datetime

from loguru import logger

from settings import DATA_DIR
from settings.manager import settings_manager

LOG_ENABLED: bool = settings_manager.settings.log


def setup_logger(level):
    """Setup the logger"""
    logs_dir_path = DATA_DIR / "logs"
    os.makedirs(logs_dir_path, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    log_filename = logs_dir_path / f"ragnar-{timestamp}.log"

    def get_log_settings(name, default_color, default_icon):
        color = os.getenv(f"RAGNAR_LOGGER_{name}_FG", default_color)
        icon = os.getenv(f"RAGNAR_LOGGER_{name}_ICON", default_icon)
        return f"<fg #{color}>", icon

    log_levels = {
        "PROGRAM": (35, "cc6600", "🤖"),
        "DISCORD": (36, "e56c49", "👽"),
        "DATABASE": (37, "d834eb", "🛢️"),
        "COMPLETED": (41, "FFFFFF", "🟢"),
        "CACHE": (42, "527826", "📜"),
        "NOT_FOUND": (43, "818589", "🤷‍"),
        "NEW": (44, "e63946", "✨"),
        "FILES": (45, "FFFFE0", "🗃️ "),
        "ITEM": (46, "92a1cf", "🗃️ "),
        "DISCOVERY": (47, "e56c49", "🔍"),
        "API": (48, "006989", "👾"),
        "OLLAMA": (49, "006989", "👾"),
    }

    for name, (no, default_color, default_icon) in log_levels.items():
        color, icon = get_log_settings(name, default_color, default_icon)
        logger.level(name, no=no, color=color, icon=icon)

    debug_color, debug_icon = get_log_settings("DEBUG", "98C1D9", "🐞")
    info_color, info_icon = get_log_settings("INFO", "818589", "📰")
    warning_color, warning_icon = get_log_settings("WARNING", "ffcc00", "⚠️ ")
    critical_color, critical_icon = get_log_settings("CRITICAL", "ff0000", "")
    success_color, success_icon = get_log_settings("SUCCESS", "00ff00", "✔️ ")

    logger.level("DEBUG", color=debug_color, icon=debug_icon)
    logger.level("INFO", color=info_color, icon=info_icon)
    logger.level("WARNING", color=warning_color, icon=warning_icon)
    logger.level("CRITICAL", color=critical_color, icon=critical_icon)
    logger.level("SUCCESS", color=success_color, icon=success_icon)

    log_format = (
        "<fg #818589>{time:YY-MM-DD} {time:HH:mm:ss}</fg #818589> | "
        "<level>{level.icon}</level> <level>{level: <9}</level> | "
        "<fg #990066>{module}</fg #990066>.<fg #990066>{function}</fg #990066> - <level>{message}</level>"
    )

    logger.configure(
        handlers=[
            {
                "sink": sys.stderr,
                "level": level.upper() or "INFO",
                "format": log_format,
                "backtrace": False,
                "diagnose": False,
                "enqueue": True,
            },
            {
                "sink": log_filename,
                "level": level.upper(),
                "format": log_format,
                "rotation": "25 MB",
                "retention": "24 hours",
                "compression": None,
                "backtrace": False,
                "diagnose": True,
                "enqueue": True,
            },
        ]
    )


def log_cleaner():
    """Remove old log files based on retention settings."""
    try:
        logs_dir_path = DATA_DIR / "logs"
        now = datetime.now()
        cleaned_files = [
            log_file
            for log_file in logs_dir_path.glob("ragnar-*.log")
            if (now - datetime.fromtimestamp(log_file.stat().st_mtime)).total_seconds()
            / 3600
            > 8
            or log_file.stat().st_size == 0
        ]

        for log_file in cleaned_files:
            log_file.unlink()

        if cleaned_files:
            logger.log(
                "COMPLETED",
                f"Cleaned up {len(cleaned_files)} old log(s) that were older than 8 hours, empty, or less than 1MB.",
            )
    except Exception as e:
        logger.exception(f"Failed to clean old logs: {e}")


log_level = "DEBUG" if settings_manager.settings.debug else "INFO"
setup_logger(log_level)
