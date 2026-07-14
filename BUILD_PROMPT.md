# BUILD PROMPT — AI Interview Prep Platform

> **How to use this file.** Paste the whole thing as your first message to Claude Code / Antigravity. Then, for each phase, say: **"Begin Phase 1."** Do not say "build the whole project" — you will get slop. Work phase by phase, verify the gate, then move on.

---

## ROLE

You are the lead engineer building a production-quality AI interview preparation platform. I am the product owner. We build in strict phases. **You do not start a phase until I say "Begin Phase N."** You do not skip ahead, and you do not build Phase 3 while I asked for Phase 2.

---

## MY ENVIRONMENT — READ CAREFULLY

- **OS: Windows 11, Intel i7, no GPU.**
- All commands you give me must be **Windows PowerShell**, not bash. No `export`, no `source venv/bin/activate`, no `rm -rf`, no `&&` chaining assumptions.
  - venv activate: `.\venv\Scripts\Activate.ps1`
  - env vars: `.env` file + `python-dotenv`, never shell exports
- Python 3.11+.
- **No local ML models that need >1GB RAM.** No GPU inference. If a step wants a heavy local model, use a free API instead.
- I am a competent developer but new to RAG and voice pipelines. Explain *why*, not just *what*, when you make a non-obvious call.

---

## ABSOLUTE CONSTRAINTS

1. **Python for everything.** FastAPI backend. The ONLY JavaScript permitted is browser-forced: microphone capture (`MediaRecorder`), audio playback, the push-to-talk button, and the countdown timer. If you find yourself writing a JS framework, a JS state store, or JS business logic — **stop, you have made a mistake.**
2. **Free tiers only.** No paid API, no paid DB, no paid hosting. If a design needs paid infrastructure, redesign it.
3. **No hardcoded question banks.** Every interviewer turn is generated live from the conversation. If you write a list of interview questions in a Python file, you have failed the core requirement.
4. **The LLM never scores its own confidence.** Confidence is computed in code, from embeddings. Any `"confidence": 0.9` coming out of an LLM response is a bug.
5. **Secrets in `.env`.** Never in code, never in git. Ship `.env.example`.

---

## TECH STACK — USE EXACTLY THIS

| Layer | Tech |
|---|---|
| Backend | FastAPI + Uvicorn |
| Templates | Jinja2 |
| DB / Auth / Vectors | Supabase (Postgres + pgvector) |
| LLM | Google Gemini Flash (free tier) |
| LLM fallback | Groq (Llama) |
| Speech→Text | Groq Whisper `whisper-large-v3-turbo` |
| Text→Speech | `edge-tts` |
| Embeddings | Gemini `text-embedding-004` (768-dim) |
| PDF parsing | `pymupdf` |
| Clustering | `scikit-learn` |
| Validation | Pydantic v2 |
| Frontend | Jinja + vanilla JS + plain CSS |

Do not substitute. If something genuinely doesn't work on Windows free-tier, **tell me before switching.**

---

## THE PRODUCT

Two products, one user base, one knowledge layer.

**A — Voice Mock Interviewer.** Student picks a role, has a real 30-minute *spoken* conversation with an AI interviewer named **Maya**. Maya listens, follows up, probes shallow answers, and closes naturally. Nothing scripted. Then a written feedback report, grounded in what the candidate actually said.

**B — Doubt Session (RAG).** Student picks a role, asks questions. Answers come from a teacher-curated PDF corpus via retrieval. Every answer gets a **code-computed** confidence score. Low confidence → honest refusal + a **red flag** to the teacher.

**The loop (this is the heart of the project):**
Student confusion → red flag → clustered on the teacher dashboard → teacher uploads a PDF → gap closes → next student gets a real answer.

### Roles

`hr` (mandatory for all), then Phase-1 technical roles: `backend`, `frontend`, `aiml`.
Later (config only, no code change): `fullstack`, `data_engineer`, `devops`, `qa_sdet`, `mobile`, `data_scientist`, `security`, `embedded`.

A role = **a system prompt + a PDF corpus.** Adding role #12 must be a database row, not a code change. If adding a role requires touching Python, your architecture is wrong.

---

## PHASE PROTOCOL — MANDATORY

For **every** phase, in this order:

1. **Plan first.** Before writing code, state: files you'll create, key decisions, anything you're unsure about. **Wait for my "go."**
2. **Then build.**
3. **Then give me the exact PowerShell commands** to install, run, and verify.
4. **Then stop** and write a `PHASE_N_SUMMARY.md` in the repo root containing:
   - What was built (files + purpose, one line each)
   - Key design decisions **and why**
   - What I must do manually (keys, SQL to paste into Supabase, etc.)
   - **How to verify it works** — concrete steps, expected output
   - Known limitations / what's deliberately deferred
   - What Phase N+1 will do
5. **Do not begin Phase N+1** until I say so.

Also maintain a running `PROJECT_STATE.md` — current architecture, all env vars, all DB tables, all endpoints. Update it every phase. This is my map when I come back after a week.

---

# THE PHASES

## PHASE 0 — Skeleton & Config

- Repo structure, `venv`, `requirements.txt`, `.env.example`, `.gitignore`
- FastAPI app that boots, `/health` endpoint
- Config loader (pydantic-settings) reading `.env`
- **LLM client wrapper** with a Gemini→Groq fallback and retry/backoff. Every LLM call in the project goes through this one module. Log token usage — the free tier is our tightest constraint and I want to see it burn.
- Structured logging

**Gate:** `uvicorn app.main:app --reload` runs, `/health` returns 200.

---

## PHASE 1 — Interview Engine (TEXT MODE ONLY — NO VOICE)

**Do not add voice in this phase.** Voice latency hides a boring interviewer. If Maya is dull, I need to know now, not in week four.

- Supabase tables: `users`, `roles`, `sessions`, `messages`. Give me the SQL to paste.
- Role system prompts for `hr`, `backend`, `frontend`, `aiml`, stored **in the DB**, not in Python.
- Turn endpoint: `POST /session/{id}/turn` — save candidate text → build context → Gemini → save reply → return.
- **Interview arc**, driven by elapsed time injected into the prompt: warm-up (intro, college, tech stack) → core technical → **probe** → wrap-up → close. Backend nudges Maya to wrap up as time runs long; a heuristic detects the closing line.
- **CONTEXT STRATEGY — CRITICAL.** Do **not** resend full history every turn. That is quadratic and will exhaust the Gemini free tier by minute ten. Instead: **rolling summary + last ~6 verbatim turns.** Keep recent turns verbatim (Maya needs exact wording to follow up), summarize everything older into a running state ("4th-year CS, claims strong PyTorch, vague on backprop, confident on transformers"). That summary doubles as the report skeleton later. **Implement this now, not as an optimization later.**
- A dead-simple text chat page to test Maya.

**Gate:** I hold a 10-turn text interview. Maya asks about my background, then role-specific questions, and — this is the real test — **when I give a deliberately vague answer, she probes it.** If she accepts vagueness, the product is worthless. Fix the prompt until she doesn't.

---

## PHASE 2 — Voice

- `MediaRecorder` push-to-talk → POST audio blob to FastAPI. **~40 lines of JS, no more.**
- STT: Groq Whisper. **Store the audio file** — we'll mine it for speaking pace and filler words in the report.
- TTS: `edge-tts`, one consistent female neural voice for Maya.
- Endpoint returns `{transcript, reply_text, reply_audio_url}`.
- Latency: stream the LLM, fire TTS on the **first complete sentence** so Maya starts talking before she's finished thinking. Target under 3s to first audio.
- 30-minute countdown; expiry ends the session via the same close flow.
- Graceful degradation: if Groq STT throttles, fall back to browser Web Speech.

**Gate:** I hold a real spoken interview end to end.

---

## PHASE 3 — Grounded Report

- End-of-session: transcript → Gemini → JSON report → Pydantic validation → retry once on failure.
- **ENFORCE GROUNDING IN CODE. Do not trust the prompt.** Schema requires, per score, a `evidence_quote` that must appear **verbatim in the transcript**. In Python, string-match every quote against the transcript and **drop any score whose evidence doesn't exist.** Grounding must be a guarantee, not a hope.
- `topics_not_covered` field — explicitly listed, explicitly **not scored**. Never penalize the candidate for what was never asked.
- **Free bonus from stored audio:** words-per-minute, filler-word count, average pause length. No prompt can fake these.
- If report generation is rate-limited: **still complete the session**, allow regeneration from the report screen.
- Post-report survey, stored per session, visible only to admin.

**Gate:** Report scores trace to real quotes. I try to break it by never mentioning Docker — the report must not score me on Docker.

---

## PHASE 4 — RAG Doubt System

- `documents`, `chunks` (pgvector 768), `doubts` tables.
- Ingestion: PDF → pymupdf → chunk (~500 tok, 50 overlap, respect section boundaries) → embed → store with `role_id`.
- **TWO CONFIDENCE GATES. Both computed in code.**
  - **Gate 1 — Retrieval gate (before generating).** Embed question, retrieve top-k, examine top-1 similarity *and* the top-1-to-top-k gap. If retrieval is weak → **do not call the LLM at all.** It cannot hallucinate if it never runs. Refuse immediately.
  - **Gate 2 — Groundedness gate (after generating).** Split the answer into claims. For each, check support against the retrieved chunks. Start with max-cosine per claim. Score = weighted fn of retrieval strength × claim coverage.
- Three outcomes: **high** → answer + cite chunks. **medium** → answer with caveat. **low** → refuse:
  > *"That's a great question — we don't have material covering it yet. Your teacher has been notified and we'll get back to you."*
- **Wrong-role detection — no classifier, no extra model.** Run retrieval across **all** role corpora, not just the selected one. If another role scores far higher: *"This looks like a Data Engineering question — switch roles for a proper answer."*
- **Critical distinction:** low-in-selected + high-elsewhere = wrong role → redirect, **NOT a red flag.** Low-in-selected + low-everywhere = genuine content gap → **red flag.** Getting this wrong floods the teacher dashboard with noise.

**Gate:** Ask an in-corpus question → good cited answer. Ask an out-of-corpus question → honest refusal, not a hallucination. Ask a backend question while in the AI/ML role → correct redirect.

---

## PHASE 5 — Teacher Loop (THE CENTERPIECE)

- `red_flags` table storing the question **embedding**.
- **Cluster red flags** (KMeans/HDBSCAN on embeddings). The teacher must **never** see a raw list of 200 questions. They see:
  > **"14 students asked about Kafka consumer groups — no content."** [Upload PDF]
  This turns a log into a work queue. It is the single change that makes the project land.
- Teacher dashboard: clusters ranked by student count, PDF upload per role, gaps auto-resolve on ingest.
- Admin views: student performance, survey results.

**Gate:** I ask an unanswerable question 3× from 3 accounts → one clustered flag appears → I upload a PDF → the same question now answers correctly. **Demo the full loop closing.**

---

## PHASE 6 — Auth, Polish, Deploy

- Supabase auth, student/teacher split, role selection at signup (multi-select).
- Session history, past reports.
- Deploy free (Render/Fly/HF Spaces).
- Document the cold-start problem and the Supabase 7-day idle pause **in the README** — I will be demoing this and I refuse to be ambushed by it.

---

## PHASE 7 — Remaining Roles

Config only. Adding roles 5–12 must require **zero Python changes**. If it doesn't, the architecture failed and we fix the architecture, not the roles.

---

## THINGS THAT WILL GO WRONG — DESIGN FOR THEM NOW

- **Gemini free tier is the real bottleneck.** One 30-min interview = 25–40 LLM calls. Four concurrent students can brown out the app. This is why the rolling-summary context strategy is non-negotiable, why Groq fallback exists, and why I want token logging from Phase 0.
- **Free hosting cold-starts.** First turn will be slow.
- **Supabase free pauses after ~7 days idle.**
- **Thin corpus = constant refusals.** Seed each Phase-1 role with real PDFs before students touch it, or the red-flag dashboard just proves we have no content.

---

## START HERE

Do **not** write code yet.

First, respond with:
1. Your understanding of the project in your own words — I want to know if this landed.
2. Anything in this spec you think is **wrong or risky**. Push back. I would rather argue now than rewrite in week three.
3. Your Phase 0 plan.

Then wait for me to say **"Begin Phase 0."**
