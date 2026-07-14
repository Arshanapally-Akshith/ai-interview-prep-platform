from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from uuid import UUID
import structlog

from app.models.schemas import SessionCreateRequest, SessionResponse, TurnRequest, TurnResponse, SessionHistoryResponse
from app.services.db import get_db
from supabase import Client
from app.services.interview_engine import InterviewEngine
from app.services.llm_client import LLMClient

logger = structlog.get_logger(__name__)
router = APIRouter()

from app.core.config import settings

def get_interview_engine(db: Client = Depends(get_db)) -> InterviewEngine:
    llm = LLMClient(settings)
    return InterviewEngine(db, llm)

@router.post("", response_model=SessionResponse)
async def create_session(req: SessionCreateRequest, db: Client = Depends(get_db)):
    # Validate role
    role_res = db.table("roles").select("id").eq("id", req.role_id).execute()
    if not role_res.data:
        raise HTTPException(status_code=400, detail="Invalid role_id")

    # Ensure user exists (for Phase 1, we might auto-create or assume seed user if none provided)
    # Since we need a user_id, let's just make sure it exists, or for testing we can insert a dummy user if we want
    # In a real app, user_id comes from auth token
    user_res = db.table("users").select("id").eq("id", str(req.user_id)).execute()
    if not user_res.data:
         # Auto-create user for testing purposes if they don't exist
         db.table("users").insert({"id": str(req.user_id), "email": f"test_{req.user_id}@example.com"}).execute()

    res = db.table("sessions").insert({
        "user_id": str(req.user_id),
        "role_id": req.role_id,
        "status": "active"
    }).execute()
    
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create session")
        
    return SessionResponse(**res.data[0])

@router.post("/{session_id}/turn", response_model=TurnResponse)
async def process_turn(
    session_id: UUID, 
    req: TurnRequest, 
    background_tasks: BackgroundTasks,
    engine: InterviewEngine = Depends(get_interview_engine),
    db: Client = Depends(get_db)
):
    try:
        maya_content, metadata = await engine.process_turn(session_id, req.content)
        
        # After processing, check if we need to summarize
        # We summarize every 4-5 turns (8-10 messages). Let's say if total messages > 12, we summarize older ones
        # For simplicity, let's count unsummarized messages
        summary_res = db.table("conversation_summaries").select("last_summarized_message_id, summary").eq("session_id", str(session_id)).execute()
        
        query = db.table("messages").select("*").eq("session_id", str(session_id)).order("created_at", desc=False)
        all_msgs = query.execute().data
        
        if len(all_msgs) > 12: # 6 turns
            # Get messages to summarize (older than the most recent 12)
            messages_to_summarize = all_msgs[:-12]
            
            # Find which ones aren't summarized yet
            last_sum_id = summary_res.data[0]["last_summarized_message_id"] if summary_res.data else None
            
            idx_start = 0
            if last_sum_id:
                for i, m in enumerate(messages_to_summarize):
                    if m["id"] == last_sum_id:
                        idx_start = i + 1
                        break
            
            unsummarized = messages_to_summarize[idx_start:]
            if len(unsummarized) >= 8: # roughly 4 turns
                current_summary = summary_res.data[0]["summary"] if summary_res.data else ""
                from app.models.domain import Message
                unsummarized_objs = [Message(**m) for m in unsummarized]
                background_tasks.add_task(engine.update_summary_async, session_id, current_summary, unsummarized_objs)

        return TurnResponse(content=maya_content, metadata=metadata)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error processing turn", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(session_id: UUID, db: Client = Depends(get_db)):
    msgs_res = db.table("messages").select("*").eq("session_id", str(session_id)).order("created_at", desc=False).execute()
    summary_res = db.table("conversation_summaries").select("summary").eq("session_id", str(session_id)).execute()
    
    summary = summary_res.data[0]["summary"] if summary_res.data else ""
    return SessionHistoryResponse(
        session_id=session_id,
        messages=msgs_res.data,
        summary=summary
    )
