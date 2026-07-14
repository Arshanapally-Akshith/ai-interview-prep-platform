import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from app.services.interview_engine import InterviewEngine
from app.models.domain import Role, Session, ConversationSummary, Message

class DummyLLM:
    pass

class DummyDB:
    pass

def test_determine_stage():
    engine = InterviewEngine(DummyDB(), DummyLLM())
    assert engine._determine_stage(1) == "INTRO"
    assert engine._determine_stage(4) == "BACKGROUND"
    assert engine._determine_stage(10) == "TECHNICAL"
    assert engine._determine_stage(20) == "PROBING"
    assert engine._determine_stage(26) == "BEHAVIORAL"
    assert engine._determine_stage(28) == "WRAP_UP"
    assert engine._determine_stage(30) == "CLOSE"

def test_build_prompt():
    engine = InterviewEngine(DummyDB(), DummyLLM())
    
    role = Role(id="backend", name="Backend", system_prompt="Test Prompt", created_at=datetime.now())
    session = Session(id=uuid4(), user_id=uuid4(), role_id="backend", started_at=datetime.now(timezone.utc) - timedelta(minutes=10), updated_at=datetime.now())
    summary = ConversationSummary(session_id=session.id, summary="The candidate knows Python.", updated_at=datetime.now())
    
    messages = [
        Message(id=uuid4(), session_id=session.id, speaker="candidate", content="Hello", created_at=datetime.now()),
        Message(id=uuid4(), session_id=session.id, speaker="maya", content="Hi", created_at=datetime.now())
    ]
    
    prompt = engine.build_prompt(role, summary, messages, session)
    
    # Check system prompt
    assert prompt[0]["role"] == "system"
    assert "Test Prompt" in prompt[0]["content"]
    assert "TECHNICAL stage" in prompt[0]["content"]
    assert "The candidate knows Python." in prompt[0]["content"]
    
    # Check messages
    assert prompt[1]["role"] == "user"
    assert prompt[1]["content"] == "Hello"
    assert prompt[2]["role"] == "assistant"
    assert prompt[2]["content"] == "Hi"
