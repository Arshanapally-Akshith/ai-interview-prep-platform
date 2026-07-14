from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.models.domain import Message

class SessionCreateRequest(BaseModel):
    user_id: UUID
    role_id: str

class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    role_id: str
    status: str
    started_at: datetime

class TurnRequest(BaseModel):
    content: str

class TurnResponse(BaseModel):
    content: str
    speaker: str = "maya"
    metadata: dict = Field(default_factory=dict)

class SessionHistoryResponse(BaseModel):
    session_id: UUID
    messages: List[Message]
    summary: str
