import sys
import types
import importlib
import os
import pytest

pytestmark = pytest.mark.asyncio


async def test_semantic_recall_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("DISABLE_SEMANTIC_RECALL", "1")
    from sanskara.semantic_recall import semantic_search_facts

    out = await semantic_search_facts(wedding_id="w1", session_id=None, query="any", top_k=3)
    assert out == {"facts": [], "sources": []}


async def test_semantic_recall_fallback_aggregates_latest(monkeypatch):
    # Ensure recall is enabled
    monkeypatch.setenv("DISABLE_SEMANTIC_RECALL", "0")

    # Inject a lightweight dummy memory service module to avoid heavy model imports
    dummy_mod = types.ModuleType("sanskara.memory.supabase_memory_service")

    class DummySupabaseMemoryService:
        async def search_memory(self, *args, **kwargs):
            # Force the code to hit the fallback path
            raise RuntimeError("force fallback")

    dummy_mod.SupabaseMemoryService = DummySupabaseMemoryService
    sys.modules['sanskara.memory.supabase_memory_service'] = dummy_mod

    # Patch fallback fetcher to simulate DB rows
    import sanskara.semantic_recall as sem

    async def fake_fallback_fetch_latest_memories(*, wedding_id: str, top_k: int):
        return [
            {"content": {"text": "Discussed budget breakdown for decor and catering."}, "created_at": "2025-08-08T10:00:00Z"},
            {"content": {"text": "Confirmed photographer shortlist and next steps."}, "created_at": "2025-08-08T10:05:00Z"},
        ]

    monkeypatch.setattr(sem, "_fallback_fetch_latest_memories", fake_fallback_fetch_latest_memories)

    out = await sem.semantic_search_facts(wedding_id="w123", session_id=None, query="budget and vendors", top_k=2)
    assert isinstance(out, dict)
    assert len(out.get("facts", [])) == 2
    assert len(out.get("sources", [])) == 2
    assert out["sources"][0].get("created_at")
