"""
Unified LLM client with Gemini → Groq fallback, retry/backoff, and token logging.

This is the SINGLE gateway for every LLM call in the project. No other module
should import google.genai or groq directly. This ensures:
  1. Consistent fallback behavior
  2. Centralized token usage logging (the free tier is our tightest constraint)
  3. Uniform response format regardless of provider

Design:
  - Try Gemini first (higher quality, generous daily quota, tight RPM).
  - On rate-limit or error → retry with exponential backoff (up to max_retries).
  - If Gemini exhausted → fall back to Groq (fast, decent quality, separate quota).
  - Every call is logged: provider, model, tokens, latency, fallback status.
  - If both providers fail, raise LLMError so the caller can handle gracefully.

Usage:
    from app.services.llm_client import LLMClient
    from app.core.config import settings

    client = LLMClient(settings)
    response = await client.generate(
        messages=[{"role": "user", "content": "Hello!"}],
        system_prompt="You are a helpful assistant.",
    )
    print(response.text, response.total_tokens)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

if TYPE_CHECKING:
    from app.core.config import Settings

logger = structlog.get_logger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class LLMError(Exception):
    """Base exception for LLM client errors."""


class LLMProviderError(LLMError):
    """A single provider failed (may still fall back to another)."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class LLMAllProvidersExhaustedError(LLMError):
    """All providers failed after retries. The caller must handle this."""

    def __init__(self, errors: list[LLMProviderError]) -> None:
        self.errors = errors
        providers = ", ".join(e.provider for e in errors)
        super().__init__(f"All LLM providers failed: {providers}")


# =============================================================================
# Response Model
# =============================================================================


@dataclass(frozen=True)
class LLMResponse:
    """Uniform response from any LLM provider.

    Frozen dataclass — once created, it's immutable. This is intentional:
    responses are facts, not mutable state.
    """

    text: str
    provider: str  # "gemini" or "groq"
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    was_fallback: bool = False


# =============================================================================
# LLM Client
# =============================================================================


class LLMClient:
    """Unified LLM client with Gemini → Groq automatic fallback.

    Instantiate once (typically in FastAPI lifespan), use throughout the app.
    Thread-safe for concurrent async calls.
    """

    def __init__(self, config: Settings) -> None:
        self._config = config
        self._gemini_client = None
        self._groq_client = None

        # Lazily initialize only the providers we have keys for
        if config.has_gemini:
            from google import genai

            self._gemini_client = genai.Client(api_key=config.gemini_api_key)
            logger.info("llm_provider_initialized", provider="gemini", model=config.gemini_model)

        if config.has_groq:
            from groq import AsyncGroq

            self._groq_client = AsyncGroq(api_key=config.groq_api_key)
            logger.info("llm_provider_initialized", provider="groq", model=config.groq_model)

        if not config.has_gemini and not config.has_groq:
            logger.warning("no_llm_providers_configured")

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            messages: Conversation turns as [{"role": "user"|"assistant", "content": "..."}].
            system_prompt: Optional system instruction (prepended, not part of messages).
            temperature: Sampling temperature. Defaults to config value.
            max_tokens: Max output tokens. Defaults to config value.

        Returns:
            LLMResponse with text, token counts, and provider metadata.

        Raises:
            LLMAllProvidersExhaustedError: If all providers fail after retries.
        """
        temperature = temperature if temperature is not None else self._config.llm_default_temperature
        max_tokens = max_tokens if max_tokens is not None else self._config.llm_default_max_tokens

        errors: list[LLMProviderError] = []

        # --- Try Gemini first ---
        if self._gemini_client is not None:
            try:
                return await self._call_gemini(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    was_fallback=False,
                )
            except LLMProviderError as e:
                errors.append(e)
                logger.warning(
                    "gemini_failed_falling_back",
                    error=str(e),
                    fallback_provider="groq",
                )

        # --- Fallback to Groq ---
        if self._groq_client is not None:
            try:
                return await self._call_groq(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    was_fallback=len(errors) > 0,
                )
            except LLMProviderError as e:
                errors.append(e)
                logger.error("groq_fallback_also_failed", error=str(e))

        # --- Both exhausted ---
        if not errors:
            errors.append(LLMProviderError("none", "No LLM providers configured"))

        raise LLMAllProvidersExhaustedError(errors)

    # -------------------------------------------------------------------------
    # Gemini
    # -------------------------------------------------------------------------

    async def _call_gemini(
        self,
        *,
        messages: list[dict[str, str]],
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        was_fallback: bool,
    ) -> LLMResponse:
        """Call Gemini with retry. Raises LLMProviderError on exhaustion."""
        from google.genai import types as genai_types

        @retry(
            stop=stop_after_attempt(self._config.llm_max_retries),
            wait=wait_exponential(
                multiplier=self._config.llm_retry_base_wait,
                max=self._config.llm_retry_max_wait,
            ),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        async def _attempt() -> LLMResponse:
            start = time.perf_counter()

            # Build the contents list for Gemini
            contents = self._messages_to_gemini_contents(messages)

            config = genai_types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            if system_prompt:
                config.system_instruction = system_prompt

            response = await self._gemini_client.aio.models.generate_content(
                model=self._config.gemini_model,
                contents=contents,
                config=config,
            )

            latency_ms = (time.perf_counter() - start) * 1000

            # Extract token counts
            usage = response.usage_metadata
            prompt_tokens = usage.prompt_token_count if usage else 0
            completion_tokens = usage.candidates_token_count if usage else 0
            total_tokens = usage.total_token_count if usage else 0

            result = LLMResponse(
                text=response.text or "",
                provider="gemini",
                model=self._config.gemini_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=round(latency_ms, 1),
                was_fallback=was_fallback,
            )

            self._log_usage(result)
            return result

        try:
            return await _attempt()
        except Exception as e:
            raise LLMProviderError("gemini", str(e)) from e

    # -------------------------------------------------------------------------
    # Groq
    # -------------------------------------------------------------------------

    async def _call_groq(
        self,
        *,
        messages: list[dict[str, str]],
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        was_fallback: bool,
    ) -> LLMResponse:
        """Call Groq with retry. Raises LLMProviderError on exhaustion."""

        @retry(
            stop=stop_after_attempt(self._config.llm_max_retries),
            wait=wait_exponential(
                multiplier=self._config.llm_retry_base_wait,
                max=self._config.llm_retry_max_wait,
            ),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        async def _attempt() -> LLMResponse:
            start = time.perf_counter()

            # Build OpenAI-compatible messages for Groq
            groq_messages = self._build_groq_messages(messages, system_prompt)

            response = await self._groq_client.chat.completions.create(
                model=self._config.groq_model,
                messages=groq_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            latency_ms = (time.perf_counter() - start) * 1000

            usage = response.usage
            result = LLMResponse(
                text=response.choices[0].message.content or "",
                provider="groq",
                model=self._config.groq_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                latency_ms=round(latency_ms, 1),
                was_fallback=was_fallback,
            )

            self._log_usage(result)
            return result

        try:
            return await _attempt()
        except Exception as e:
            raise LLMProviderError("groq", str(e)) from e

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _messages_to_gemini_contents(
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Convert our generic message format to Gemini's content format.

        Gemini uses "user" and "model" roles (not "assistant").
        """
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        return contents

    @staticmethod
    def _build_groq_messages(
        messages: list[dict[str, str]],
        system_prompt: str | None,
    ) -> list[dict[str, str]]:
        """Build OpenAI-compatible message list for Groq."""
        groq_messages: list[dict[str, str]] = []
        if system_prompt:
            groq_messages.append({"role": "system", "content": system_prompt})
        groq_messages.extend(messages)
        return groq_messages

    @staticmethod
    def _log_usage(response: LLMResponse) -> None:
        """Log token usage and latency for every LLM call.

        This is how we 'see the free tier burn' — every call is tracked.
        """
        logger.info(
            "llm_call_complete",
            provider=response.provider,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            latency_ms=response.latency_ms,
            was_fallback=response.was_fallback,
        )
