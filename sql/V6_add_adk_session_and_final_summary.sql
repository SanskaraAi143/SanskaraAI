-- Migration: Add adk_session_id and final_summary columns to chat_sessions
-- Safe to run multiple times (IF NOT EXISTS guards)
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS adk_session_id text;
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS final_summary text;
-- Optional embedding column if later you want to store summary embedding directly (commented out)
-- ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS final_summary_embedding vector(1024);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_adk_session_id ON chat_sessions(adk_session_id);
