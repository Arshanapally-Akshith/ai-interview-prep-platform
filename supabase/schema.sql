-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Roles Table
CREATE TABLE roles (
    id VARCHAR(50) PRIMARY KEY, -- 'hr', 'backend', 'frontend', 'aiml'
    name VARCHAR(100) NOT NULL,
    system_prompt TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sessions Table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id VARCHAR(50) REFERENCES roles(id),
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'completed'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversation Summaries Table
CREATE TABLE conversation_summaries (
    session_id UUID PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    summary TEXT DEFAULT '',
    last_summarized_message_id UUID,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages Table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    speaker VARCHAR(20) NOT NULL, -- 'candidate', 'maya', 'system'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb, -- token usage, latency, model info
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_role_id ON sessions(role_id);
CREATE INDEX idx_messages_session_id ON messages(session_id);

-- Initial Roles (Phase 1 seed data)
-- Note: See docs/prompts.md for the full prompt text, which should be updated here.
INSERT INTO roles (id, name, system_prompt) VALUES
('hr', 'HR', 'You are Maya, an HR interviewer...'),
('backend', 'Backend', 'You are Maya, a senior backend engineer conducting a technical interview...'),
('frontend', 'Frontend', 'You are Maya, a senior frontend engineer conducting a technical interview...'),
('aiml', 'AI/ML', 'You are Maya, an AI/ML engineering lead conducting a technical interview...');
