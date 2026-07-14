# AI Interview Prep Platform

A production-quality AI-powered platform for placement interview preparation. Two products, one shared knowledge layer:

- **🎙️ Voice Mock Interviewer (Maya)** — Unscripted, adaptive 30-minute spoken interviews with probing follow-ups and grounded feedback reports.
- **📚 RAG Doubt Sessions** — Ask questions answered from teacher-curated PDF corpora, with code-computed confidence scores and honest refusal on low confidence.

The platform's core loop: student confusion → red-flag → clustered teacher dashboard → PDF upload → knowledge gap closes → next student gets a real answer.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (Jinja2 + Vanilla JS)        │
│   MediaRecorder · Audio Playback · Push-to-Talk · Timer     │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP / WebSocket
┌────────────────────────────▼────────────────────────────────┐
│                     FastAPI + Uvicorn                        │
│                                                             │
│  ┌─────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ API     │  │ Interview    │  │ RAG Doubt Engine       │ │
│  │ Routes  │  │ Engine       │  │ (Retrieval + Grounding)│ │
│  └────┬────┘  └──────┬───────┘  └───────────┬────────────┘ │
│       │              │                      │              │
│  ┌────▼──────────────▼──────────────────────▼────────────┐ │
│  │          Unified LLM Client (Gemini → Groq)           │ │
│  │          Token Logging · Retry/Backoff · Fallback     │ │
│  └───────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    Supabase (Free Tier)                      │
│   Postgres · pgvector (768-dim) · Auth · Storage            │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer           | Technology                              |
|-----------------|------------------------------------------|
| Backend         | FastAPI + Uvicorn                        |
| Templates       | Jinja2                                   |
| DB / Auth       | Supabase (Postgres + pgvector)           |
| LLM (primary)   | Google Gemini Flash (free tier)          |
| LLM (fallback)  | Groq (Llama 3.3 70B)                    |
| Speech → Text   | Groq Whisper `whisper-large-v3-turbo`    |
| Text → Speech   | `edge-tts` (Microsoft neural voices)     |
| Embeddings      | Gemini `text-embedding-004` (768-dim)    |
| PDF Parsing     | `pymupdf`                                |
| Clustering      | `scikit-learn` (KMeans / HDBSCAN)        |
| Validation      | Pydantic v2                              |
| Frontend        | Jinja2 + Vanilla JS + Plain CSS          |
| Linting         | Ruff                                     |
| Logging         | structlog (JSON in prod, console in dev) |

---

## Folder Structure

```
ai-interview-prep-platform/
├── app/
│   ├── api/                 # FastAPI route handlers
│   │   └── __init__.py
│   ├── core/                # Configuration, logging, shared infra
│   │   ├── config.py        # Pydantic Settings (.env loader)
│   │   ├── logging_config.py# structlog setup
│   │   └── __init__.py
│   ├── services/            # Business logic & external integrations
│   │   ├── llm_client.py    # Unified Gemini → Groq LLM wrapper
│   │   └── __init__.py
│   ├── models/              # Pydantic schemas & data models
│   │   └── __init__.py
│   ├── utils/               # Shared helpers
│   │   └── __init__.py
│   ├── main.py              # FastAPI app entry point
│   └── __init__.py
├── scripts/
│   └── test_llm.py          # Standalone LLM client test
├── .env.example             # Environment variable template
├── .gitignore
├── pyproject.toml           # Ruff config + project metadata
├── requirements.txt         # Python dependencies
├── BUILD_PROMPT.md          # Full build specification
├── PROJECT_STATE.md         # Living architecture document
└── README.md                # This file
```

---

## Setup

### Prerequisites

- **Python 3.11+** installed and on PATH
- **Windows 11** (all commands are PowerShell)
- API keys (both free):
  - [Google Gemini](https://aistudio.google.com/apikey)
  - [Groq](https://console.groq.com/keys)

### Installation

```powershell
# 1. Clone the repository
git clone <repo-url>
cd ai-interview-prep-platform

# 2. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
Copy-Item .env.example .env
# Open .env and add your API keys
```

### Running the Server

```powershell
# Start the development server
uvicorn app.main:app --reload

# Verify it's running
# Visit http://localhost:8000/health in your browser
# Expected: {"status": "ok", "env": "development", "llm_providers": {"gemini": true, "groq": true}}
```

### Testing the LLM Client

```powershell
# Run the standalone LLM test (no server needed)
python scripts/test_llm.py

# This tests:
#   1. Basic generation via Gemini
#   2. Automatic fallback to Groq
#   3. Multi-turn conversation
# Check console output for token usage logs
```

### Linting

```powershell
# Check for lint errors
ruff check .

# Auto-fix what can be fixed
ruff check . --fix

# Format code
ruff format .
```

---

## Environment Variables

| Variable                 | Required | Default                    | Description                          |
|--------------------------|----------|----------------------------|--------------------------------------|
| `GEMINI_API_KEY`         | Yes*     | —                          | Google Gemini API key                |
| `GEMINI_MODEL`           | No       | `gemini-2.0-flash`         | Gemini model name                    |
| `GROQ_API_KEY`           | Yes*     | —                          | Groq API key (fallback LLM + STT)   |
| `GROQ_MODEL`             | No       | `llama-3.3-70b-versatile`  | Groq model name                     |
| `LLM_MAX_RETRIES`        | No       | `2`                        | Retries per provider before fallback |
| `LLM_RETRY_BASE_WAIT`    | No       | `1.0`                      | Base wait (seconds) for backoff      |
| `LLM_RETRY_MAX_WAIT`     | No       | `8.0`                      | Max wait (seconds) for backoff       |
| `LLM_DEFAULT_TEMPERATURE`| No       | `0.7`                      | Default sampling temperature         |
| `LLM_DEFAULT_MAX_TOKENS` | No       | `1024`                     | Default max output tokens            |
| `APP_ENV`                | No       | `development`              | `development` or `production`        |
| `APP_HOST`               | No       | `0.0.0.0`                  | Server bind host                     |
| `APP_PORT`               | No       | `8000`                     | Server bind port                     |
| `LOG_LEVEL`              | No       | `INFO`                     | Logging level                        |

*At least one of `GEMINI_API_KEY` or `GROQ_API_KEY` must be set.

---

## Development Roadmap

| Phase | Focus                        | Status      |
|-------|------------------------------|-------------|
| 0     | Skeleton & Config            | ✅ Complete |
| 1     | Interview Engine (text mode) | ⬜ Pending  |
| 2     | Voice (STT + TTS)            | ⬜ Pending  |
| 3     | Grounded Report              | ⬜ Pending  |
| 4     | RAG Doubt System             | ⬜ Pending  |
| 5     | Teacher Loop & Dashboard     | ⬜ Pending  |
| 6     | Auth, Polish, Deploy         | ⬜ Pending  |
| 7     | Remaining Roles (config-only)| ⬜ Pending  |

---

## Key Design Decisions

- **Single LLM Client** — Every LLM call goes through `app/services/llm_client.py`. Centralized retry, fallback, and token logging. The free tier is the tightest constraint.
- **Rolling Context** — Interviews use a summary + last ~6 turns instead of full history replay. Prevents quadratic token growth that would exhaust Gemini's free tier by minute 10.
- **Code-Computed Confidence** — The LLM never scores its own confidence. Retrieval similarity and groundedness are computed in Python from embeddings.
- **Roles as Data** — A role = a database row (system prompt + PDF corpus). Adding role #12 is an INSERT, not a code change.
- **Grounding Enforced in Code** — Report evidence quotes are string-matched against the transcript. If a quote doesn't exist in the transcript, the score is dropped. Grounding is a guarantee, not a hope.

---

## License

Private — not for redistribution.
