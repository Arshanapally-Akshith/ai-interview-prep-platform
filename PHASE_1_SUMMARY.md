# Phase 1 Summary: Interview Engine (Text Mode)

## What Was Built
- **Supabase Schema**: Created `supabase/schema.sql` containing tables for `users`, `roles`, `sessions`, `conversation_summaries`, and `messages`. Includes seed data for the 4 initial roles.
- **System Prompts Documentation**: Added `docs/prompts.md` documenting the exact prompts to be seeded into the Supabase database.
- **Pydantic Models**: Added `app/models/domain.py` and `app/models/schemas.py` to strongly type the DB entities and API requests/responses.
- **Supabase Service**: Added `app/services/db.py` to initialize and inject the Supabase client.
- **Interview Engine**: Added `app/services/interview_engine.py` to handle prompt assembly, elapsed-time stage determination (INTRO → BACKGROUND → TECHNICAL → PROBING → BEHAVIORAL → WRAP_UP → CLOSE), and background context summarization.
- **API Endpoints**: Added `app/api/endpoints/sessions.py` and `app/api/endpoints/roles.py` to expose the interview capabilities.
- **Text Chat UI**: Added `templates/index.html`, `static/js/app.js`, and `static/css/style.css` to allow manual testing of the Maya interviewer.
- **Unit Tests**: Added `tests/test_interview_engine.py` to verify stage determination and prompt assembly logic.

## Key Design Decisions
- **Rolling Context with `conversation_summaries` Table**: Instead of storing the summary in the `sessions` table, we moved it to a dedicated table to handle tracking of the `last_summarized_message_id`. A background task handles summarization to avoid blocking the user's turn response.
- **Metadata Column in Messages**: We added a `metadata` JSONB column to the `messages` table to log token usage and LLM latency on a per-turn basis.
- **Speaker Column**: The `role` column in the messages table was renamed to `speaker` (candidate, maya, system) to disambiguate from the "interview roles" (hr, backend, etc.).
- **Stage Progression via Elapsed Time**: To ensure the interview moves forward naturally without explicit hardcoded questions, the system injects a hidden directive into the system prompt based on how much time has passed since the session started.

## What You Must Do Manually
1. Set up a Supabase project and get your URL and Keys.
2. Update the `.env` file with `SUPABASE_URL` and `SUPABASE_KEY`.
3. Open the Supabase SQL editor and execute the contents of `supabase/schema.sql` to create the tables and seed the initial roles.

## How to Verify It Works
1. Ensure your `.env` is configured with Supabase and LLM API keys.
2. Run `uvicorn app.main:app --reload`.
3. Open `http://localhost:8000/` in your browser.
4. Select a role and start a test interview.
5. Provide deliberately vague answers to test Maya's probing capability (e.g., saying "I built microservices" without explaining how). Maya should interrupt and probe for details.
6. Verify token usage in the backend logs; it should plateau after ~6 turns as older messages are summarized.

## Known Limitations
- The application currently auto-creates a dummy user (or skips auth) because authentication is slated for Phase 6.
- The UI is extremely minimal as its sole purpose is to test the conversational model.
- We haven't implemented Voice latency tracking since voice is Phase 2.

## What Phase 2 Will Do
Phase 2 will introduce Voice (STT + TTS) integration via Groq Whisper and `edge-tts`. We'll build a ~40-line `MediaRecorder` client to push audio blobs to the FastAPI backend and return spoken responses, streaming the LLM output for minimal latency.
