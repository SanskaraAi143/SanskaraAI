from typing import List, Dict, Any, Optional
import os
from logger import json_logger as logger

DEFAULT_TOP_K = 5

# New: restrict to session_final_summary entries when present
SESSION_SUMMARY_ONLY = True  # could be toggled via env later


def _compact(text: str, max_len: int = 220) -> str:
    try:
        t = (text or "").strip().replace("\n", " ")
        return (t[: max_len - 1] + "…") if len(t) > max_len else t
    except Exception:
        return text or ""


async def _fallback_fetch_latest_memories(*, wedding_id: str, top_k: int) -> List[Dict[str, Any]]:
    """Fallback: pull latest memories for this wedding without vector search (summary entries first)."""
    try:
        from sanskara.helpers import execute_supabase_sql, sql_quote_value
        app_name = os.getenv("SANSKARA_APP_NAME", "SanskaraAI")
        # Prefer rows whose content.metadata.type == 'session_final_summary'
        sql = (
            "SELECT content, created_at "
            "FROM memories "
            f"WHERE app_name = {sql_quote_value(app_name)} "
            f"  AND user_id = {sql_quote_value(wedding_id)} "
            "ORDER BY (content->'metadata'->>'type' = 'session_final_summary') DESC, created_at DESC "
            f"LIMIT {int(top_k)};"
        )
        res = await execute_supabase_sql(sql)
        if res.get("status") == "success":
            return res.get("data", [])
    except Exception as e:
        logger.debug(f"_fallback_fetch_latest_memories error: {e}")
    return []


async def semantic_search_facts(
    *,
    wedding_id: str,
    session_id: Optional[str],
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, Any]:
    """
    Return compressed semantic facts only from session_final_summary memories (summary-only mode).
    If summaries not yet stored or vector search fails, falls back to latest summary rows.
    """
    try:
        if not query or len(query.strip()) == 0:
            return {"facts": [], "sources": []}

        if os.getenv("DISABLE_SEMANTIC_RECALL", "0") in ("1", "true", "True"):
            return {"facts": [], "sources": []}

        # Attempt vector search but filter to session_final_summary entries client-side
        try:
            from sanskara.sanskara.memory.supabase_memory_service import SupabaseMemoryService  # type: ignore
        except Exception:
            try:
                from sanskara.memory.supabase_memory_service import SupabaseMemoryService  # type: ignore
            except Exception as imp_err:
                logger.debug(f"semantic_recall: memory service import failed, using fallback. Error: {imp_err}")
                SupabaseMemoryService = None  # type: ignore

        facts: List[str] = []
        sources: List[Dict[str, Any]] = []

        if 'SupabaseMemoryService' in locals() and SupabaseMemoryService is not None:
            try:
                svc = SupabaseMemoryService()
                app_name = os.getenv("SANSKARA_APP_NAME", "SanskaraAI")
                resp = await svc.search_memory(app_name=app_name, user_id=wedding_id, query=query)
                # Filter to summaries only
                filtered = []
                for m in (resp.memories or []):
                    text = ""
                    if getattr(m, "content", None) and getattr(m.content, "parts", None):
                        part0 = m.content.parts[0]
                        text = getattr(part0, "text", "") or str(part0)
                    # Heuristic: summary entries tagged inside text or stored with metadata (not exposed by MemoryEntry now)
                    # Because MemoryEntry currently doesn't surface metadata, rely on prefix pattern
                    if "session_final_summary" in text or len(text.split()) <= 120:  # lightweight heuristic
                        filtered.append(m)
                for m in filtered[: int(top_k)]:
                    try:
                        part0 = m.content.parts[0] if (m.content and m.content.parts) else None
                        text = getattr(part0, "text", "") if part0 else ""
                        comp = _compact(text)
                        if comp:
                            facts.append(comp)
                            sources.append({
                                "created_at": getattr(m, "timestamp", None),
                                "author": getattr(m, "author", None),
                            })
                    except Exception:
                        continue
                if facts:
                    return {"facts": facts[: int(top_k)], "sources": sources[: int(top_k)]}
            except Exception as e:
                logger.debug(f"semantic_recall: embedding search failed, falling back. Error: {e}")

        # Fallback: fetch latest memories prioritizing summaries
        rows = await _fallback_fetch_latest_memories(wedding_id=wedding_id, top_k=top_k)
        for r in rows:
            try:
                content = r.get("content") or {}
                if isinstance(content, dict):
                    text = content.get("text", "")
                    meta = content.get("metadata") if isinstance(content, dict) else None
                else:
                    text = str(content)
                    meta = None
                if meta and meta.get("type") != "session_final_summary":
                    continue  # only summaries
                comp = _compact(text)
                if comp:
                    source = {"created_at": r.get("created_at")}
                    if isinstance(meta, dict):
                        if meta.get("session_id"):
                            source["session_id"] = meta.get("session_id")
                        if meta.get("adk_session_id"):
                            source["adk_session_id"] = meta.get("adk_session_id")
                    facts.append(comp)
                    sources.append(source)
            except Exception:
                continue
        return {"facts": facts[: int(top_k)], "sources": sources[: int(top_k)]}

    except Exception as e:
        logger.error(f"semantic_search_facts error: {e}", exc_info=True)
        return {"facts": [], "sources": []}
