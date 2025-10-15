"""
Context Manager V2: deterministic, stateful context assembly for the Orchestrator.

Design goals (from docs):
- Database is the durable state. Agents are stateless between turns.
- Keep the context compact and predictable; avoid intent heuristics.
- Include workflow "save files" (status/current_step/context_summary/related_entity_ids).
- Provide collaboration signals (lead_party ownership, pending reviews/approvals).
- Compose with the baseline context service for core data.

Usage:
    ctx = await ContextManagerV2().build_context(wedding_id, user_id, user_role, user_message)

This returns a dict safe to place in callback_context.state and to feed into OrchestratorContext.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import json

from sanskara.helpers import execute_supabase_sql
from sanskara.context_service import assemble_baseline_context
from sanskara.context_models import WorkflowContextSummary # Import the new model


class ContextManagerV2:
    """Compose baseline context with durable workflow state and collaboration view."""

    async def build_context(
        self,
        wedding_id: str,
        user_id: str,
        user_role: Optional[str],
        user_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a compact orchestrator-ready context.

        - Starts with baseline context (core wedding/user, tasks, vendors, budget, timeline).
        - Adds workflow_saves (from workflows table) for active/paused items.
        - Adds collab_status (tasks by lead_party and statuses) for quick filtering.
        - Adds bookings (if table exists) to avoid redundant vendor searches.
        - Adds thread_hint derived from the latest user_message (lightweight routing aid).
        """
        # 1) Baseline, safe defaults
        ctx = await assemble_baseline_context(
            wedding_id=wedding_id,
            user_id=user_id,
            user_role=user_role,
        )

        # 2) Durable state from DB
        workflow_saves = await _get_workflow_saves(wedding_id)
        collab_status = await _get_collab_status(wedding_id)
        bookings = await _get_bookings(wedding_id)

        ctx["workflow_saves"] = workflow_saves
        ctx["collab_status"] = collab_status
        ctx["bookings"] = bookings

        # 2b) Provide a unified 'workflows' alias used by the prompt.
        # Prefer baseline active_workflows if present; otherwise synthesize from workflow_saves.
        try:
            active = ctx.get("active_workflows") or []
            if active:
                workflows = active
            else:
                # Map saves to a simplified workflow view
                workflows = [
                    {
                        "workflow_id": w.get("workflow_id"),
                        "name": w.get("workflow_name"),
                        "status": w.get("status"),
                        # Deserialize context_summary into WorkflowContextSummary model
                        "contextual_data": (WorkflowContextSummary(**w.get("context_summary")).contextual_data
                                            if isinstance(w.get("context_summary"), dict) else None),
                        "current_stage": (WorkflowContextSummary(**w.get("context_summary")).current_stage
                                          if isinstance(w.get("context_summary"), dict) else None),
                        "stage_goal": (WorkflowContextSummary(**w.get("context_summary")).stage_goal
                                       if isinstance(w.get("context_summary"), dict) else None),
                        "next_possible_actions": (WorkflowContextSummary(**w.get("context_summary")).next_possible_actions
                                                  if isinstance(w.get("context_summary"), dict) else None),
                        "summary_text": (WorkflowContextSummary(**w.get("context_summary")).summary_text
                                         if isinstance(w.get("context_summary"), dict) else None),
                        "updated_at": w.get("updated_at"),
                    }
                    for w in (workflow_saves or [])
                ]
        except Exception as e:
            logging.warning(f"Error processing workflow_saves in ContextManagerV2: {e}")
            workflows = ctx.get("active_workflows") or []

        ctx["workflows"] = workflows

        # 3) Lightweight thread hint (no intent tree; just simple keywords to help the LLM)
        hint = _derive_thread_hint(user_message or "")
        # Always include thread_hint key to satisfy prompt templating
        ctx["thread_hint"] = hint or {}
        # 4) Return
        return ctx


async def _get_workflow_saves(wedding_id: str) -> List[Dict[str, Any]]:
    """Return recent workflow rows acting as save files for long-running processes."""
    sql = """
    SELECT 
        workflow_id,
        workflow_name,
        status,
        context_summary,
        updated_at
    FROM workflows
    WHERE wedding_id = :wedding_id
      AND status IN ('in_progress','paused','awaiting_feedback')
    ORDER BY updated_at DESC
    LIMIT 10;
    """
    try:
        res = await execute_supabase_sql(sql, {"wedding_id": wedding_id})
        if res.get("status") == "success":
            return res.get("data", []) or []
    except Exception as e:
        logging.debug(f"_get_workflow_saves failed: {e}")
    return []


async def _get_collab_status(wedding_id: str) -> Dict[str, Any]:
    """Return small aggregates to show per-side responsibilities and pending items."""
    sql = """
    WITH base AS (
        SELECT 
            LOWER(COALESCE(lead_party, 'member')) AS lead_party,
            status
        FROM tasks
        WHERE wedding_id = :wedding_id
    )
    SELECT 
        json_build_object(
            'bride_side', json_build_object(
                'open', COUNT(*) FILTER (WHERE lead_party IN ('bride','bride_side') AND status <> 'completed'),
                'pending_review', COUNT(*) FILTER (WHERE lead_party IN ('bride','bride_side') AND status = 'pending_review'),
                'pending_final_approval', COUNT(*) FILTER (WHERE lead_party IN ('bride','bride_side') AND status = 'pending_final_approval')
            ),
            'groom_side', json_build_object(
                'open', COUNT(*) FILTER (WHERE lead_party IN ('groom','groom_side') AND status <> 'completed'),
                'pending_review', COUNT(*) FILTER (WHERE lead_party IN ('groom','groom_side') AND status = 'pending_review'),
                'pending_final_approval', COUNT(*) FILTER (WHERE lead_party IN ('groom','groom_side') AND status = 'pending_final_approval')
            ),
            'couple', json_build_object(
                'open', COUNT(*) FILTER (WHERE lead_party = 'couple' AND status <> 'completed'),
                'pending_review', COUNT(*) FILTER (WHERE lead_party = 'couple' AND status = 'pending_review'),
                'pending_final_approval', COUNT(*) FILTER (WHERE lead_party = 'couple' AND status = 'pending_final_approval')
            )
        ) AS collab
    FROM base;
    """
    try:
        res = await execute_supabase_sql(sql, {"wedding_id": wedding_id})
        if res.get("status") == "success" and res.get("data"):
            row = res["data"][0]
            return row.get("collab", {}) or {}
    except Exception as e:
        logging.debug(f"_get_collab_status failed: {e}")
    return {"bride_side": {}, "groom_side": {}, "couple": {}}


async def _get_bookings(wedding_id: str) -> List[Dict[str, Any]]:
    """Return simple bookings list if the table exists; otherwise empty.

    This helps the orchestrator avoid suggesting searches for already-booked vendors.
    """
    sql = """
    SELECT 
        b.booking_id,
        b.vendor_id,
        COALESCE(v.vendor_name, NULL) AS vendor_name,
        b.booking_status AS status,
        b.event_date,
        b.total_amount,
        b.paid_amount,
        b.created_at
    FROM bookings b
    LEFT JOIN vendors v ON v.vendor_id = b.vendor_id
    WHERE b.wedding_id = :wedding_id
    ORDER BY b.created_at DESC
    LIMIT 20;
    """
    try:
        res = await execute_supabase_sql(sql, {"wedding_id": wedding_id})
        if res.get("status") == "success":
            return res.get("data", []) or []
    except Exception as e:
        # Table may not exist in some environments; fail open
        logging.debug(f"_get_bookings failed (non-fatal): {e}")
    return []


def _derive_thread_hint(user_message: str) -> Optional[Dict[str, Any]]:
    """A tiny, safe hint to guide the LLM without intent classification complexity."""
    try:
        text = (user_message or "").lower()
        if not text:
            return None
        if any(k in text for k in ("venue", "hall", "banquet", "resort")):
            return {"topic": "vendors", "category": "venue"}
        if any(k in text for k in ("dj", "band", "music", "sangeet")):
            return {"topic": "vendors", "category": "entertainment"}
        if any(k in text for k in ("budget", "cost", "expense", "money")):
            return {"topic": "budget"}
        if any(k in text for k in ("timeline", "deadline", "due", "schedule")):
            return {"topic": "timeline"}
        if any(k in text for k in ("guest", "rsvp", "invite", "whatsapp")):
            return {"topic": "guests"}
    except Exception:
        return None
    return None
