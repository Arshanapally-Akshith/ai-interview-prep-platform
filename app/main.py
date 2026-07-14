"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload

This module:
  - Initializes structured logging on startup
  - Creates the LLM client singleton (available app-wide via app.state)
  - Exposes /health for liveness checks
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.services.llm_client import LLMClient

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown logic.

    Why lifespan instead of @app.on_event?
    FastAPI deprecated on_event in favor of lifespan context managers.
    This is the modern pattern.
    """
    # --- Startup ---
    setup_logging(log_level=settings.log_level, is_production=settings.is_production)

    logger.info(
        "app_starting",
        env=settings.app_env,
        gemini_configured=settings.has_gemini,
        groq_configured=settings.has_groq,
    )

    # Initialize LLM client singleton — every service that needs LLM access
    # gets it from app.state.llm_client (injected via FastAPI dependency)
    app.state.llm_client = LLMClient(settings)

    logger.info("app_started", host=settings.app_host, port=settings.app_port)

    yield  # --- App runs here ---

    # --- Shutdown ---
    logger.info("app_shutting_down")


app = FastAPI(
    title="AI Interview Prep Platform",
    description="Voice mock interviews and RAG-based doubt resolution for placement preparation",
    version="0.1.0",
    lifespan=lifespan,
)


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Liveness probe. Returns 200 if the app is running.

    Phase 0 gate: this must return {"status": "ok"}.
    """
    return {
        "status": "ok",
        "env": settings.app_env,
        "llm_providers": {
            "gemini": settings.has_gemini,
            "groq": settings.has_groq,
        },
    }
