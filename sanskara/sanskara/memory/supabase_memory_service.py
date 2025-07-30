from __future__ import annotations
import json
import logging
from typing import Any, Dict, Optional, List

from typing_extensions import override
from sentence_transformers import SentenceTransformer

from google.adk.memory.base_memory_service import BaseMemoryService, SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.sessions import Session
from sanskara.helpers import execute_supabase_sql,sql_quote_value
from google.genai import types  # for Content/Part classes

logger = logging.getLogger(__name__)

# Load a CPU‐optimized static embedding model once
EMBED_MODEL_NAME = "sentence-transformers/static-retrieval-mrl-en-v1"
_EMBED_MODEL = SentenceTransformer(EMBED_MODEL_NAME, device="cpu")  # CPU only[1]
_EMBED_DIM = _EMBED_MODEL.get_sentence_embedding_dimension()  # 1536

class SupabaseMemoryService(BaseMemoryService):
    """Memory service using Supabase + pgvector + local CPU embeddings."""

    @override
    async def add_session_to_memory(self, session: Session):
        # Collect rows for bulk insert
        rows: List[str] = []
        for event in session.events:
            if not event.content or not event.content.parts:
                continue
            text = " ".join(event.content.parts)
            # Compute embedding on CPU
            embedding: List[float] = _EMBED_MODEL.encode([text], show_progress_bar=False)[0]
            # Build PostgreSQL vector literal
            vec_literal = f"ARRAY[{','.join(str(x) for x in embedding)}]::vector"
            content_json = json.dumps({"text": text}).replace("'", "''")
            rows.append(
                f"({sql_quote_value(session.app_name)},"
                f"{sql_quote_value(session.user_id)},"
                f"'{content_json}',"
                f"{vec_literal})"
            )

        if not rows:
            logger.info("No events to add to memory.")
            return

        sql = (
            "INSERT INTO memories (app_name, user_id, content, embedding) VALUES\n"
            + ",\n".join(rows)
            + ";"
        )
        res = await execute_supabase_sql(sql)
        if res.get("status") != "success":
            logger.error("Insert failed: %s", res.get("error"))
        else:
            logger.info("Inserted %d memory rows.", len(rows))

    @override
    async def search_memory(
        self, *, app_name: str, user_id: str, query: str
    ) -> SearchMemoryResponse:
        # Encode the query to the same embedding space
        q_emb: List[float] = _EMBED_MODEL.encode([query], show_progress_bar=False)[0]
        vec_literal = f"ARRAY[{','.join(str(x) for x in q_emb)}]::vector"
        k = 5  # number of neighbors

        sql = (
            "SELECT content, created_at "
            "FROM memories "
            f"WHERE app_name = {sql_quote_value(app_name)} "
            f"  AND user_id = {sql_quote_value(user_id)} "
            f"ORDER BY embedding <-> {vec_literal} "
            f"LIMIT {k};"
        )
        res = await execute_supabase_sql(sql)
        if res.get("status") != "success":
            logger.error("Search failed: %s", res.get("error"))
            return SearchMemoryResponse()

        memories: List[MemoryEntry] = []
        for row in res["data"]:
            content = row.get("content", {})
            text = content.get("text", "")
            memories.append(
                MemoryEntry(
                    author="user",
                    content=types.Content(parts=[types.Part(text=text)], role="user"),
                    timestamp=row.get("created_at"),
                )
            )
        return SearchMemoryResponse(memories=memories)
