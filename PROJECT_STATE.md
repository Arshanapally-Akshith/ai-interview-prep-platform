# PROJECT STATE — AI Interview Prep Platform

> **Living document.** Updated every phase. This is your map when you come back after a week.
>
> Last updated: **Phase 0**

---

## Current Architecture

```
Browser ──HTTP──▶ FastAPI (Uvicorn)
                    ├── /health
                    └── LLMClient (Gemini → Groq fallback)
```

No database, no auth, no templates yet. Phase 0 is skeleton + LLM plumbing.

---

## Environment Variables

| Variable                  | Added In | Used By          |
|---------------------------|----------|------------------|
| `GEMINI_API_KEY`          | Phase 0  | LLM Client       |
| `GEMINI_MODEL`            | Phase 0  | LLM Client       |
| `GROQ_API_KEY`            | Phase 0  | LLM Client       |
| `GROQ_MODEL`              | Phase 0  | LLM Client       |
| `LLM_MAX_RETRIES`         | Phase 0  | LLM Client       |
| `LLM_RETRY_BASE_WAIT`     | Phase 0  | LLM Client       |
| `LLM_RETRY_MAX_WAIT`      | Phase 0  | LLM Client       |
| `LLM_DEFAULT_TEMPERATURE` | Phase 0  | LLM Client       |
| `LLM_DEFAULT_MAX_TOKENS`  | Phase 0  | LLM Client       |
| `APP_ENV`                 | Phase 0  | Config / Logging  |
| `APP_HOST`                | Phase 0  | Config            |
| `APP_PORT`                | Phase 0  | Config            |
| `LOG_LEVEL`               | Phase 0  | Logging           |

---

## Database Tables

*None yet. Supabase tables arrive in Phase 1.*

---

## API Endpoints

| Method | Path      | Auth | Description              | Added In |
|--------|-----------|------|--------------------------|----------|
| GET    | `/health` | No   | Liveness check, 200 = ok | Phase 0  |

---

## Key Files

| File                          | Purpose                                   | Phase |
|-------------------------------|-------------------------------------------|-------|
| `app/main.py`                 | FastAPI app, lifespan, /health             | 0     |
| `app/core/config.py`          | Pydantic Settings, .env loader             | 0     |
| `app/core/logging_config.py`  | structlog setup (JSON prod / console dev)  | 0     |
| `app/services/llm_client.py`  | Unified Gemini→Groq LLM wrapper            | 0     |
| `scripts/test_llm.py`         | Standalone LLM client test                 | 0     |

---

## Roles

| Role ID  | Name       | Status   | System Prompt | PDF Corpus |
|----------|------------|----------|---------------|------------|
| `hr`     | HR         | Phase 1  | —             | —          |
| `backend`| Backend    | Phase 1  | —             | —          |
| `frontend`| Frontend  | Phase 1  | —             | —          |
| `aiml`   | AI/ML      | Phase 1  | —             | —          |

*Roles are stored in the database, not in code. Added in Phase 1.*

---

## Known Limitations (Current Phase)

1. No database — all state is in-memory / stateless
2. No auth — endpoints are public
3. No frontend — API only
4. LLM client does not yet support streaming (needed for voice in Phase 2)
5. No embeddings client yet (needed for RAG in Phase 4)

---

## Phase History

### Phase 0 — Skeleton & Config ✅
- Repo structure, venv, dependencies
- FastAPI app with /health
- Pydantic-settings config loader
- Unified LLM client with Gemini→Groq fallback + token logging
- Structured logging (structlog)
- Ruff linting configured
