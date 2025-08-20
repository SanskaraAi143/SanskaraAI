from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class OrchestratorMeta(BaseModel):
    intent: Optional[str] = None
    scope: Optional[str] = None
    k_turns: int = 6
    top_k: int = 5
    context_version: str = "v1"
    assembled_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    token_estimate: Optional[int] = None


class SemanticMemory(BaseModel):
    facts: List[str] = []
    sources: List[Dict[str, Any]] = []


class OrchestratorContext(BaseModel):
    # Core DB slices (existing keys from context_manager)
    wedding_data: Dict[str, Any] = {}
    current_wedding_id: Optional[str] = None
    current_user_id: Optional[str] = None
    current_user_role: Optional[str] = None
    user_display_name: Optional[str] = None
    user_email: Optional[str] = None

    # Optional slices used by prompts
    shortlisted_vendors: List[Dict[str, Any]] = []
    budget_by_category: List[Dict[str, Any]] = []
    budget_totals: Dict[str, Any] = {"total_budget": 0, "total_spent": 0, "remaining_budget": 0}
    recent_expenses: List[Dict[str, Any]] = []

    upcoming_events: List[Dict[str, Any]] = []
    overdue_tasks: List[Dict[str, Any]] = []
    urgent_tasks: List[Dict[str, Any]] = []
    timeline_summary: Dict[str, Any] = {"upcoming_count": 0, "overdue_count": 0, "urgent_count": 0}

    active_workflows: List[Dict[str, Any]] = []
    relevant_tasks: List[Dict[str, Any]] = []
    all_tasks: List[Dict[str, Any]] = []

    priority_items: List[Dict[str, Any]] = []
    recent_activity: List[Dict[str, Any]] = []
    progress_by_category: List[Dict[str, Any]] = []
    budget_insights: List[Dict[str, Any]] = []
    timeline_context: Dict[str, Any] = {}
    suggested_next_actions: List[Dict[str, Any]] = []
    top_3_next_actions: List[Dict[str, Any]] = []
    proactive_insights: Dict[str, Any] = {}

    pending_actions: Dict[str, Any] = {"pending_reviews": [], "awaiting_workflows": []}

    budget_summary: Dict[str, Any] = {"total_budget": 0, "total_spent": 0, "pending_amount": 0, "total_items": 0}
    upcoming_deadlines: List[Dict[str, Any]] = []
    calendar_events: List[Dict[str, Any]] = []
    cultural_context: Dict[str, Any] = {}
    guest_context: Dict[str, Any] = {}
    collaboration_context: Dict[str, Any] = {}

    # V2 additions: durable state and collaboration aggregates
    workflow_saves: List[Dict[str, Any]] = []  # rows from workflows table (active/paused/awaiting_feedback)
    collab_status: Dict[str, Any] = {}         # small aggregates per lead_party
    bookings: List[Dict[str, Any]] = []        # already-booked vendors
    thread_hint: Optional[Dict[str, Any]] = None  # lightweight hint from latest user message

    # Conversation memory additions
    conversation_summary: Optional[str] = None
    recent_messages: List[Dict[str, Any]] = []  # [{role, content, created_at}]
    semantic_memory: SemanticMemory = Field(default_factory=SemanticMemory)

    # Meta
    meta: OrchestratorMeta = Field(default_factory=OrchestratorMeta)

    def to_state(self) -> Dict[str, Any]:
        # Dump to plain dict for ADK state
        return self.model_dump()
