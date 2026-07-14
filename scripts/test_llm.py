"""
Standalone LLM client test script.

Tests the Gemini → Groq fallback wrapper without running the full FastAPI app.
Run from the project root with the venv active:

    python scripts/test_llm.py

What this tests:
  1. Basic generation via primary provider (Gemini)
  2. Automatic fallback to Groq (by simulating a Gemini failure)
  3. Token usage logging output

Check the console output for structured log lines showing provider, tokens, and latency.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure the project root is on the path so `app` is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.services.llm_client import LLMClient, LLMAllProvidersExhaustedError, LLMProviderError

# Initialize logging so we can see structured output
setup_logging(log_level="DEBUG", is_production=False)

import structlog

logger = structlog.get_logger("test_llm")

DIVIDER = "=" * 70


async def test_basic_generation(client: LLMClient) -> None:
    """Test 1: Basic generation through the primary provider."""
    print(f"\n{DIVIDER}")
    print("TEST 1: Basic Generation (primary provider)")
    print(DIVIDER)

    try:
        response = await client.generate(
            messages=[{"role": "user", "content": "Say 'Hello from Maya!' in exactly 5 words."}],
            system_prompt="You are a helpful assistant. Be concise.",
            temperature=0.3,
            max_tokens=50,
        )
        print(f"\n  Provider:    {response.provider}")
        print(f"  Model:       {response.model}")
        print(f"  Response:    {response.text}")
        print(f"  Tokens:      {response.prompt_tokens} in / {response.completion_tokens} out / {response.total_tokens} total")
        print(f"  Latency:     {response.latency_ms:.0f}ms")
        print(f"  Fallback:    {response.was_fallback}")
        print(f"\n  ✅ PASSED")
    except LLMAllProvidersExhaustedError as e:
        print(f"\n  ❌ FAILED — {e}")
        print("  Check your API keys in .env")


async def test_fallback(client: LLMClient) -> None:
    """Test 2: Force Gemini to fail, verify Groq fallback activates."""
    print(f"\n{DIVIDER}")
    print("TEST 2: Fallback Behavior")
    print(DIVIDER)

    if not settings.has_groq:
        print("\n  ⏭️  SKIPPED — No Groq API key configured, can't test fallback")
        return

    if not settings.has_gemini:
        print("\n  ⏭️  SKIPPED — No Gemini key configured, primary is already Groq")
        return

    # Create a client with a broken Gemini key to force fallback
    from app.core.config import Settings

    broken_settings = Settings(
        gemini_api_key="invalid-key-to-force-failure",
        groq_api_key=settings.groq_api_key,
        llm_max_retries=1,  # Fail fast for testing
        llm_retry_base_wait=0.1,
        llm_retry_max_wait=0.5,
    )
    broken_client = LLMClient(broken_settings)

    try:
        response = await broken_client.generate(
            messages=[{"role": "user", "content": "Say 'Fallback works!' in exactly 2 words."}],
            system_prompt="You are a helpful assistant. Be concise.",
            temperature=0.3,
            max_tokens=50,
        )
        if response.provider == "groq" and response.was_fallback:
            print(f"\n  Provider:    {response.provider} (fallback)")
            print(f"  Response:    {response.text}")
            print(f"  Latency:     {response.latency_ms:.0f}ms")
            print(f"\n  ✅ PASSED — Fallback activated correctly")
        else:
            print(f"\n  ⚠️  Unexpected: responded via {response.provider}, fallback={response.was_fallback}")
    except LLMAllProvidersExhaustedError as e:
        print(f"\n  ❌ FAILED — Both providers down: {e}")


async def test_multi_turn(client: LLMClient) -> None:
    """Test 3: Multi-turn conversation (used in interview mode)."""
    print(f"\n{DIVIDER}")
    print("TEST 3: Multi-turn Conversation")
    print(DIVIDER)

    try:
        response = await client.generate(
            messages=[
                {"role": "user", "content": "My name is Alex and I study Computer Science."},
                {"role": "assistant", "content": "Nice to meet you, Alex! What year are you in?"},
                {"role": "user", "content": "I'm in my final year."},
            ],
            system_prompt="You are Maya, a friendly technical interviewer. Ask a follow-up about their final year project.",
            temperature=0.7,
            max_tokens=150,
        )
        print(f"\n  Provider:    {response.provider}")
        print(f"  Response:    {response.text[:200]}{'...' if len(response.text) > 200 else ''}")
        print(f"  Tokens:      {response.total_tokens} total")
        print(f"\n  ✅ PASSED")
    except LLMAllProvidersExhaustedError as e:
        print(f"\n  ❌ FAILED — {e}")


async def main() -> None:
    """Run all tests."""
    print("\n🧪 AI Interview Prep Platform — LLM Client Test Suite")
    print(f"   Gemini configured: {settings.has_gemini}")
    print(f"   Groq configured:   {settings.has_groq}")

    if not settings.has_gemini and not settings.has_groq:
        print("\n❌ No API keys found. Copy .env.example to .env and add your keys.")
        print("   Get Gemini key: https://aistudio.google.com/apikey")
        print("   Get Groq key:   https://console.groq.com/keys")
        sys.exit(1)

    client = LLMClient(settings)

    await test_basic_generation(client)
    await test_fallback(client)
    await test_multi_turn(client)

    print(f"\n{DIVIDER}")
    print("All tests complete. Check the structured log output above for token usage details.")
    print(DIVIDER)


if __name__ == "__main__":
    asyncio.run(main())
