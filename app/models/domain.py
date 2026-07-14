from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class User(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime

class Role(BaseModel):
    id: str
    name: str
    system_prompt: str
    created_at: datetime

class Session(BaseModel):
    id: UUID
    user_id: UUID
    role_id: str
    status: str = "active"
    started_at: datetime
    updated_at: datetime

class ConversationSummary(BaseModel):
    session_id: UUID
    summary: str
    last_summarized_message_id: Optional[UUID] = None
    updated_at: datetime

class Message(BaseModel):
    id: UUID
    session_id: UUID
    speaker: str  # 'candidate', 'maya', 'system'
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
