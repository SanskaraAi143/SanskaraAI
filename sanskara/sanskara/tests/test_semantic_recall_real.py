import os
import sys
import types
import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(os.getenv("RUN_SEMANTIC_RECALL_REAL", "0") not in ("1", "true", "True"), reason="Real Supabase test disabled. Set RUN_SEMANTIC_RECALL_REAL=1 to enable.")
async def test_semantic_recall_real_fallback_reads_inserted_memories(monkeypatch):
    # Require Supabase credentials; skip if missing
    if not os.getenv("SUPABASE_ACCESS_TOKEN") or not os.getenv("SUPABASE_PROJECT_ID"):
        pytest.skip("Supabase credentials not configured for real test")

    # Ensure recall enabled
    monkeypatch.setenv("DISABLE_SEMANTIC_RECALL", "0")

    # Insert memories via the real memory service (computes embeddings)
    try:
        try:
            from sanskara.memory.supabase_memory_service import SupabaseMemoryService
        except Exception:
            from sanskara.sanskara.memory.supabase_memory_service import SupabaseMemoryService  # type: ignore
    except Exception as e:
        pytest.skip(f"SupabaseMemoryService unavailable: {e}")

    svc = SupabaseMemoryService()
    app_name = os.getenv("SANSKARA_APP_NAME", "SanskaraAI")
    user_id = "w-real-semantic-test"

    await svc.add_text_to_memory(app_name=app_name, user_id=user_id, text="We discussed the budget for decor and catering.", metadata={"session_id": "s1", "message_id": "m1"})
    await svc.add_text_to_memory(app_name=app_name, user_id=user_id, text="Decided to shortlist venues near the lake.", metadata={"session_id": "s1", "message_id": "m2"})

    # Force semantic_recall to use fallback path by breaking the import of the memory service inside semantic_recall
    dummy = types.ModuleType("dummy")
    sys.modules['sanskara.memory.supabase_memory_service'] = dummy
    sys.modules['sanskara.sanskara.memory.supabase_memory_service'] = dummy

    from sanskara.semantic_recall import semantic_search_facts

    out = await semantic_search_facts(wedding_id=user_id, session_id=None, query="budget and venues", top_k=3)
    assert isinstance(out, dict)
    assert len(out.get("facts", [])) >= 1
    assert out["sources"][0].get("created_at") is not None
