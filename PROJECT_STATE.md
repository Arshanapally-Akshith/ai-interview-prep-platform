# PROJECT STATE — AI Interview Prep Platform

> **Living document.** Updated every phase. This is your map when you come back after a week.
>
> Last updated: **Phase 1**

---

## Current Architecture

```
Browser (Vanilla JS) ──HTTP──▶ FastAPI (Uvicorn)
                     ├── /health
                     ├── /api/sessions (Turn processing + LLM orchestration)
                     ├── /api/roles
                     └── LLMClient (Gemini → Groq fallback)
                                │
                                ▼
                           Supabase (PostgreSQL)
                           (users, roles, sessions, conversation_summaries, messages)
```

Phase 1 brings Supabase integration, rolling context summary via background tasks, and a basic HTML/JS text chat UI to interact with the LLM Interview Engine.

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
| `SUPABASE_URL`            | Phase 1  | DB Service        |
| `SUPABASE_KEY`            | Phase 1  | DB Service        |

---

## Database Tables (Supabase)

| Table | Purpose |
|---|---|
| `users` | Stores candidate identities. |
| `roles` | Pre-defined interview roles containing system prompts (`hr`, `backend`, etc). |
| `sessions` | Tracks active interviews, associated with a user and a role. |
| `conversation_summaries` | Stores rolling summary of older messages to keep LLM context size bounded. |
| `messages` | Verbatim chat history. Metadata column for tokens/latency tracking. |

---

## API Endpoints

| Method | Path | Auth | Description | Added In |
|---|---|---|---|---|
| GET | `/health` | No | Liveness check, 200 = ok | Phase 0 |
| POST | `/api/sessions` | No | Create new interview session | Phase 1 |
| POST | `/api/sessions/{id}/turn` | No | Process candidate message, get Maya response | Phase 1 |
| GET | `/api/sessions/{id}/history` | No | Get full history and summary | Phase 1 |
| GET | `/api/roles` | No | List available roles | Phase 1 |

---

## Key Files

| File | Purpose | Phase |
|---|---|---|
| `app/main.py` | FastAPI app, /health, static mounts, lifespan | 0, 1 |
| `app/core/config.py` | Pydantic Settings, .env loader (includes Supabase) | 0, 1 |
| `app/core/logging_config.py` | structlog setup | 0 |
| `app/services/llm_client.py` | Unified Gemini→Groq LLM wrapper | 0 |
| `app/services/db.py` | Supabase client setup | 1 |
| `app/services/interview_engine.py`| Core logic (rolling summary, stage determination, prompting) | 1 |
| `app/api/endpoints/sessions.py` | Session and turn API routes | 1 |
| `app/api/endpoints/roles.py` | Roles API routes | 1 |
| `app/models/domain.py` | Pydantic models for DB entities | 1 |
| `app/models/schemas.py` | Pydantic schemas for API requests/responses | 1 |
| `templates/index.html` | Text chat UI layout | 1 |
| `static/js/app.js` | Text chat frontend logic | 1 |
| `static/css/style.css` | Text chat styles | 1 |
| `supabase/schema.sql` | DB schema and seed data | 1 |
| `docs/prompts.md` | Interview role system prompts documentation | 1 |

---

## Roles

| Role ID | Name | Status | System Prompt | PDF Corpus |
|---|---|---|---|---|
| `hr` | HR | Phase 1 | See `docs/prompts.md` | — |
| `backend`| Backend | Phase 1 | See `docs/prompts.md` | — |
| `frontend`| Frontend | Phase 1 | See `docs/prompts.md` | — |
| `aiml` | AI/ML | Phase 1 | See `docs/prompts.md` | — |

*Roles are stored in the database, not in code.*

---

## Known Limitations (Current Phase)

1. No auth — endpoints are public (dummy user_id is injected in `sessions.py`).
2. Voice is missing (Text-only for now).
3. LLM client does not yet support streaming (needed for voice in Phase 2).
4. No embeddings client yet (needed for RAG in Phase 4).

---

## Phase History

### Phase 0 — Skeleton & Config ✅
- Repo structure, venv, dependencies
- FastAPI app with /health
- Pydantic-settings config loader
- Unified LLM client with Gemini→Groq fallback + token logging
- Structured logging (structlog)

### Phase 1 — Interview Engine (Text Mode) ✅
- Supabase schema (`users`, `roles`, `sessions`, `conversation_summaries`, `messages`)
- API endpoints for session management and chat turns
- `InterviewEngine` to manage interview stages via elapsed time and rolling context summary
- Vanilla JS text chat UI
- Centralized role prompts (`docs/prompts.md`)
