import sys
import types
import pytest

pytestmark = pytest.mark.asyncio


async def test_vector_path_uses_supabase_memory_service(monkeypatch):
    # Enable semantic recall
    monkeypatch.setenv("DISABLE_SEMANTIC_RECALL", "0")

    # Build a dummy SupabaseMemoryService returning deterministic entries
    dummy_mod = types.ModuleType("sanskara.memory.supabase_memory_service")

    class DummyMemoryEntry:
        def __init__(self, text, ts="2025-08-08T12:00:00Z"):
            class Part:
                def __init__(self, t):
                    self.text = t
            class Content:
                def __init__(self, t):
                    self.parts = [Part(t)]
            self.author = "user"
            self.content = Content(text)
            self.timestamp = ts

    class DummyResponse:
        def __init__(self, texts):
            self.memories = [DummyMemoryEntry(t) for t in texts]

    class DummySupabaseMemoryService:
        async def search_memory(self, *args, **kwargs):
            return DummyResponse(["A prior note about budget.", "A decision to book a venue near lake."])

    dummy_mod.SupabaseMemoryService = DummySupabaseMemoryService
    sys.modules['sanskara.memory.supabase_memory_service'] = dummy_mod

    from sanskara.semantic_recall import semantic_search_facts

    out = await semantic_search_facts(wedding_id="w1", session_id=None, query="budget venue", top_k=2)
    assert len(out.get("facts", [])) == 2
    assert any("budget" in f.lower() for f in out["facts"])
