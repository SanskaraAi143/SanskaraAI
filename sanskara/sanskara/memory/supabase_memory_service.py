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


# Load a CPU‐optimized static embedding model once
EMBED_MODEL_NAME = "sentence-transformers/static-retrieval-mrl-en-v1"
_EMBED_MODEL = SentenceTransformer(EMBED_MODEL_NAME, device="cpu")  # CPU only
_EMBED_DIM = _EMBED_MODEL.get_sentence_embedding_dimension()
logging.info(
    f"SupabaseMemoryService: Loaded embedding model '{EMBED_MODEL_NAME}' with dim={_EMBED_DIM}"
)

def preload_embeddings(warmup_texts: Optional[List[str]] = None) -> int:
    """Warm up the sentence transformer at process start to avoid first‑user latency.

    Returns the embedding dimension. Any errors are logged and swallowed.
    """
    try:
        texts = warmup_texts or [
            "warmup",
            "Sanskara AI startup warmup",
        ]
        # A tiny encode triggers any lazy initializations and BLAS kernels
        _ = _EMBED_MODEL.encode(texts, show_progress_bar=False)
        logging.info("Embedding model warmup completed (%d texts).", len(texts))
    except Exception as e:
        logging.debug("Embedding model warmup skipped/failed: %s", e)
    return _EMBED_DIM

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
            logging.info("No events to add to memory.")
            return

        sql = (
            "INSERT INTO memories (app_name, user_id, content, embedding) VALUES\n"
            + ",\n".join(rows)
            + ";"
        )
        res = await execute_supabase_sql(sql)
        if res.get("status") != "success":
            logging.error("Insert failed: %s", res.get("error"))
        else:
            logging.info("Inserted %d memory rows.", len(rows))

    async def add_text_to_memory(self, *, app_name: str, user_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a single text memory with embedding. Stores metadata inside content JSON for traceability."""
        try:
            if not text or not text.strip():
                return
            embedding: List[float] = _EMBED_MODEL.encode([text], show_progress_bar=False)[0]
            vec_literal = f"ARRAY[{','.join(str(x) for x in embedding)}]::vector"
            content_payload = {"text": text}
            if metadata:
                content_payload["metadata"] = metadata
            content_json = json.dumps(content_payload).replace("'", "''")
            sql = (
                "INSERT INTO memories (app_name, user_id, content, embedding) VALUES ("
                f"{sql_quote_value(app_name)}, {sql_quote_value(user_id)}, '{content_json}', {vec_literal}) RETURNING 1;"
            )
            await execute_supabase_sql(sql)
        except Exception as e:
            logging.warning(f"add_text_to_memory failed: {e}")

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
            logging.error("Search failed: %s", res.get("error"))
            return SearchMemoryResponse()

        memories: List[MemoryEntry] = []
        for row in res["data"]:
            content = row.get("content", {})
            if isinstance(content, dict):
                text = content.get("text", "")
                meta = content.get("metadata", {}) if isinstance(content.get("metadata", {}), dict) else {}
            else:
                text = str(content)
                meta = {}
            author = meta.get("role") or "user"
            memories.append(
                MemoryEntry(
                    author=author,
                    content=types.Content(parts=[types.Part(text=text)], role=author if author in ("user", "assistant") else "user"),
                    timestamp=row.get("created_at"),
                )
            )
        return SearchMemoryResponse(memories=memories)
