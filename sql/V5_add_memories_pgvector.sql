-- Supabase Memory Service schema (pgvector)
-- Enables long‑term semantic memory used by SupabaseMemoryService

-- 1) Required extensions
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector for embedding similarity search
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- for gen_random_uuid()

-- 2) Memories table (1536 dims match the SentenceTransformer model in code)
CREATE TABLE IF NOT EXISTS memories (
  memory_id   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  app_name    text        NOT NULL,            -- e.g., 'SanskaraAI'
  user_id     text        NOT NULL,            -- we use wedding_id here as the grouping key
  content     jsonb       NOT NULL,            -- {"text": "...", "metadata": {"session_id": "...", "message_id": "..."}}
  embedding   vector(1536) NOT NULL,           -- embedding dimension must match the model
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- 3) Helpful indexes
CREATE INDEX IF NOT EXISTS idx_memories_app_user
  ON memories(app_name, user_id);

-- Approximate nearest neighbor index for vector searches (L2 distance)
-- Note: Tune lists based on data size; analyze table after large ingests.
CREATE INDEX IF NOT EXISTS idx_memories_embedding_ivfflat
  ON memories USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Optional: time-ordered scans
CREATE INDEX IF NOT EXISTS idx_memories_created_at
  ON memories (created_at DESC);
