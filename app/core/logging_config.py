"""
Structured logging configuration using structlog.

Why structlog?
- JSON output in production → machine-parseable, grep-friendly
- Pretty console output in development → human-readable
- Bound context → attach session_id, user_id, etc. to every log line
- stdlib integration → captures logs from uvicorn, httpx, SDKs

Usage:
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("something_happened", user_id="abc", tokens=150)
"""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(log_level: str = "INFO", is_production: bool = False) -> None:
    """Configure structured logging for the entire application.

    Args:
        log_level: Python log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        is_production: If True, output JSON. If False, output pretty console format.
    """
    log_level_int = getattr(logging, log_level.upper(), logging.INFO)

    # Shared processors applied to every log event
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,  # Merge context from contextvars
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_production:
        # Production: JSON lines, one event per line
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colorful, padded, human-readable
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            # Format exception info if present
            structlog.processors.format_exc_info,
            # Bridge to stdlib (so we can set level on the root logger)
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib root logger so all loggers (uvicorn, httpx, etc.) are captured
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level_int)

    # Quiet down noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
