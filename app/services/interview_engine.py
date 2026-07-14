import json
from datetime import datetime, timezone
from uuid import UUID
from typing import List, Dict, Any, Tuple
import structlog
from app.models.domain import Message, Session, ConversationSummary, Role
from app.services.llm_client import LLMClient
from supabase import Client

logger = structlog.get_logger(__name__)

class InterviewEngine:
    def __init__(self, db: Client, llm: LLMClient):
        self.db = db
        self.llm = llm

    def _get_elapsed_minutes(self, started_at: datetime) -> int:
        now = datetime.now(timezone.utc)
        diff = now - started_at
        return int(diff.total_seconds() / 60)

    def _determine_stage(self, elapsed_minutes: int) -> str:
        """
        Expanded Interview Stages:
        INTRO -> BACKGROUND -> TECHNICAL -> PROBING -> BEHAVIORAL -> WRAP_UP -> CLOSE
        We'll use a time-based heuristic for now.
        """
        if elapsed_minutes < 2:
            return "INTRO"
        elif elapsed_minutes < 5:
            return "BACKGROUND"
        elif elapsed_minutes < 15:
            return "TECHNICAL"
        elif elapsed_minutes < 22:
            return "PROBING"
        elif elapsed_minutes < 27:
            return "BEHAVIORAL"
        elif elapsed_minutes < 29:
            return "WRAP_UP"
        else:
            return "CLOSE"

    def _get_stage_directive(self, stage: str) -> str:
        directives = {
            "INTRO": "SYSTEM NOTE: We are in the INTRO stage. Keep it brief, warmly welcome the candidate, and ask how they are doing.",
            "BACKGROUND": "SYSTEM NOTE: We are in the BACKGROUND stage. Ask a question about their past experience or education.",
            "TECHNICAL": "SYSTEM NOTE: We are in the TECHNICAL stage. Start asking role-specific technical questions. Remember to probe vague answers.",
            "PROBING": "SYSTEM NOTE: We are in the PROBING stage. Deep dive into the technical details of their previous answers. Do not accept high-level buzzwords.",
            "BEHAVIORAL": "SYSTEM NOTE: We are in the BEHAVIORAL stage. Ask a scenario-based question (e.g., handling conflicts, overcoming failure, teamwork).",
            "WRAP_UP": "SYSTEM NOTE: We have about 2-3 minutes left (WRAP_UP stage). Ask the candidate if they have any questions for you.",
            "CLOSE": "SYSTEM NOTE: Time is up (CLOSE stage). Thank the candidate for their time and end the interview gracefully."
        }
        return directives.get(stage, "")

    def build_prompt(self, role: Role, summary: ConversationSummary, recent_messages: List[Message], session: Session) -> List[Dict[str, str]]:
        elapsed = self._get_elapsed_minutes(session.started_at)
        stage = self._determine_stage(elapsed)
        directive = self._get_stage_directive(stage)

        system_content = f"{role.system_prompt}\n\n{directive}"
        if summary.summary:
            system_content += f"\n\nCURRENT CONVERSATION SUMMARY (Older Context):\n{summary.summary}"

        messages_payload = [{"role": "system", "content": system_content}]

        for msg in recent_messages:
            # Map 'maya' to 'model', 'candidate' to 'user' for Gemini (llm_client expects role 'assistant'/'user')
            role_map = {"maya": "assistant", "candidate": "user", "system": "system"}
            llm_role = role_map.get(msg.speaker, "user")
            if llm_role == "system":
                # Inject system messages as user messages wrapped in brackets for visibility
                messages_payload.append({"role": "user", "content": f"[SYSTEM]: {msg.content}"})
            else:
                messages_payload.append({"role": llm_role, "content": msg.content})

        return messages_payload

    async def update_summary_async(self, session_id: UUID, current_summary: str, messages_to_summarize: List[Message]):
        """
        Call this in the background to summarize older messages and update the summary.
        """
        if not messages_to_summarize:
            return

        logger.info("Updating conversation summary", session_id=str(session_id), count=len(messages_to_summarize))
        
        # Build prompt for summarization
        prompt = "You are a helpful assistant maintaining a concise running summary of an interview.\n"
        if current_summary:
            prompt += f"CURRENT SUMMARY:\n{current_summary}\n\n"
        
        prompt += "NEW MESSAGES TO INCORPORATE:\n"
        for msg in messages_to_summarize:
            prompt += f"{msg.speaker.upper()}: {msg.content}\n"
            
        prompt += "\nPlease provide a new, highly concise running summary of the candidate's traits, strengths, weaknesses, and key points discussed. Replace the old summary. Do not output anything other than the summary text."

        payload = [{"role": "user", "content": prompt}]
        
        # We can use the main LLM for this
        try:
            response = await self.llm.generate(messages=payload)
            new_summary = response.text
            
            last_msg_id = messages_to_summarize[-1].id
            
            # Update DB
            self.db.table("conversation_summaries").update({
               "summary": new_summary,
               "last_summarized_message_id": str(last_msg_id),
               "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("session_id", str(session_id)).execute()
            
        except Exception as e:
            logger.error("Failed to update summary", session_id=str(session_id), error=str(e))

    async def process_turn(self, session_id: UUID, content: str) -> Tuple[str, Dict[str, Any]]:
        # 1. Fetch Session
        session_res = self.db.table("sessions").select("*").eq("id", str(session_id)).execute()
        if not session_res.data:
            raise ValueError(f"Session {session_id} not found")
        session = Session(**session_res.data[0])

        # 2. Fetch Role
        role_res = self.db.table("roles").select("*").eq("id", session.role_id).execute()
        role = Role(**role_res.data[0])

        # 3. Save Candidate Message
        cand_msg_res = self.db.table("messages").insert({
            "session_id": str(session_id),
            "speaker": "candidate",
            "content": content
        }).execute()

        # 4. Fetch Summary & Last 6 Turns (12 messages)
        # Assuming order by created_at desc, limit 12, then reverse for chronological order
        msgs_res = self.db.table("messages").select("*").eq("session_id", str(session_id)).order("created_at", desc=True).limit(12).execute()
        recent_messages = [Message(**m) for m in msgs_res.data[::-1]]

        summary_res = self.db.table("conversation_summaries").select("*").eq("session_id", str(session_id)).execute()
        if summary_res.data:
            summary = ConversationSummary(**summary_res.data[0])
        else:
            summary = ConversationSummary(session_id=session_id, summary="", updated_at=datetime.now(timezone.utc))

        # 5. Build Prompt
        prompt_payload = self.build_prompt(role, summary, recent_messages, session)

        # 6. Call LLM
        llm_response = await self.llm.generate(messages=prompt_payload)
        
        maya_content = llm_response.text
        metadata = {
            "model": llm_response.model,
            "provider": llm_response.provider,
            "tokens": {
                "prompt_tokens": llm_response.prompt_tokens,
                "completion_tokens": llm_response.completion_tokens,
                "total_tokens": llm_response.total_tokens,
            },
            "latency_ms": llm_response.latency_ms,
            "was_fallback": llm_response.was_fallback
        }

        # 7. Save Maya Message
        maya_msg_res = self.db.table("messages").insert({
            "session_id": str(session_id),
            "speaker": "maya",
            "content": maya_content,
            "metadata": metadata
        }).execute()

        return maya_content, metadata
