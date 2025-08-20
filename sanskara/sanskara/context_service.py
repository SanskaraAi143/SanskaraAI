"""
Simple, deterministic context assembly for the Orchestrator.

Goals:
- Minimal, reliable baseline context with safe defaults.
- Fast queries with small caps to avoid prompt bloat.
- No intent magic; the agent asks tools for more when needed.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import asyncio
from typing import Any, Dict, List, Optional

from logger import json_logger as logger
from sanskara.helpers import execute_supabase_sql


def _safe_defaults() -> Dict[str, Any]:
    """Return a dict with all prompt-referenced keys set to safe defaults."""
    return {
        # Core identifiers
        "wedding_data": {},
        "current_wedding_id": None,
        "current_user_id": None,
        "current_user_role": None,
        "user_display_name": None,
        "user_email": None,

        # Vendor-related
        "shortlisted_vendors": [],

        # Budget-related
        "budget_by_category": [],
        "budget_totals": {"total_budget": 0, "total_spent": 0, "remaining_budget": 0},
        "recent_expenses": [],
        "budget_summary": {"total_budget": 0, "total_spent": 0, "pending_amount": 0, "total_items": 0},

        # Timeline-related
        "upcoming_events": [],
        "overdue_tasks": [],
        "urgent_tasks": [],
        "timeline_summary": {"upcoming_count": 0, "overdue_count": 0, "urgent_count": 0},
        "upcoming_deadlines": [],

        # Workflow/tasks
        "active_workflows": [],
        "relevant_tasks": [],
        "all_tasks": [],

        # Proactive/insights placeholders (not computed here)
        "priority_items": [],
        "recent_activity": [],
        "progress_by_category": [],
        "budget_insights": [],
        "timeline_context": {},
        "suggested_next_actions": [],
        "top_3_next_actions": [],
        "proactive_insights": {},

        # Collab/guest placeholders
        "pending_actions": {"pending_reviews": [], "awaiting_workflows": []},
        "calendar_events": [],
        "cultural_context": {},
        "guest_context": {},
        "collaboration_context": {},

        # Artifacts intentionally not pre-populated
        "recent_artifacts": [],
    }


async def _get_core_context(wedding_id: str, user_id: str) -> Dict[str, Any]:
    sql = """
    SELECT 
        w.*,
        u.display_name as user_display_name,
        u.email as user_email
    FROM weddings w
    LEFT JOIN users u ON u.user_id = :user_id
    WHERE w.wedding_id = :wedding_id;
    """
    try:
        res = await execute_supabase_sql(sql, {"wedding_id": wedding_id, "user_id": user_id})
        if res.get("status") == "success" and res.get("data"):
            row = res["data"][0]
            return {
                "wedding_data": row,
                "current_wedding_id": wedding_id,
                "current_user_id": user_id,
                "user_display_name": row.get("user_display_name"),
                "user_email": row.get("user_email"),
            }
    except Exception as e:
        logger.warning(f"_get_core_context failed: {e}")
    return {
        "wedding_data": {},
        "current_wedding_id": wedding_id,
        "current_user_id": user_id,
    }


async def _get_tasks_and_workflows(wedding_id: str) -> Dict[str, Any]:
    sql = """
    WITH active_workflows AS (
        SELECT * FROM workflows 
        WHERE wedding_id = :wedding_id 
          AND status IN ('in_progress','paused','awaiting_feedback')
        ORDER BY updated_at DESC
        LIMIT 10
    ),
    open_tasks AS (
        SELECT * FROM tasks
        WHERE wedding_id = :wedding_id AND is_complete = false
        ORDER BY due_date ASC NULLS LAST, priority DESC
        LIMIT 25
    )
    SELECT 
      (SELECT COALESCE(json_agg(active_workflows), '[]'::json) FROM active_workflows) AS active_workflows,
      (SELECT COALESCE(json_agg(open_tasks), '[]'::json) FROM open_tasks) AS relevant_tasks;
    """
    try:
        res = await execute_supabase_sql(sql, {"wedding_id": wedding_id})
        if res.get("status") == "success" and res.get("data"):
            row = res["data"][0]
            return {
                "active_workflows": row.get("active_workflows", []),
                "relevant_tasks": row.get("relevant_tasks", []),
            }
    except Exception as e:
        logger.debug(f"_get_tasks_and_workflows failed: {e}")
    return {"active_workflows": [], "relevant_tasks": []}


async def _get_budget_summaries(wedding_id: str) -> Dict[str, Any]:
    # Favor simpler columns (amount + status Paid/Pending) if available
    sql = """
    SELECT 
        COALESCE(SUM(amount)::numeric, 0) as total_budget,
        COUNT(*) as total_items,
        SUM(CASE WHEN status = 'Paid' THEN amount ELSE 0 END)::numeric as total_spent,
        SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END)::numeric as pending_amount
    FROM budget_items 
    WHERE wedding_id = :wedding_id;
    """
    try:
        res = await execute_supabase_sql(sql, {"wedding_id": wedding_id})
        if res.get("status") == "success" and res.get("data"):
            data = res["data"][0]
            # Ensure numeric types for arithmetic
            try:
                total_budget = float(data.get("total_budget", 0) or 0)
            except (TypeError, ValueError):
                total_budget = 0.0
            try:
                total_spent = float(data.get("total_spent", 0) or 0)
            except (TypeError, ValueError):
                total_spent = 0.0
            try:
                pending_amount = float(data.get("pending_amount", 0) or 0)
            except (TypeError, ValueError):
                pending_amount = 0.0
            return {
                "budget_summary": {
                    "total_budget": total_budget,
                    "total_spent": total_spent,
                    "pending_amount": pending_amount,
                    "total_items": data.get("total_items", 0) or 0,
                },
                "budget_totals": {
                    "total_budget": total_budget,
                    "total_spent": total_spent,
                    "remaining_budget": (total_budget - total_spent) if total_budget is not None and total_spent is not None else 0,
                },
            }
    except Exception as e:
        logger.debug(f"_get_budget_summaries failed: {e}")
    return {
        "budget_summary": {"total_budget": 0, "total_spent": 0, "pending_amount": 0, "total_items": 0},
        "budget_totals": {"total_budget": 0, "total_spent": 0, "remaining_budget": 0},
    }


async def _get_timeline_and_deadlines(wedding_id: str) -> Dict[str, Any]:
    today = datetime.utcnow().date()
    next_30 = today + timedelta(days=30)
    next_14 = today + timedelta(days=14)
    sql = """
    WITH upcoming_events AS (
        SELECT * FROM timeline_events 
        WHERE wedding_id = :wedding_id 
          AND event_date_time::date BETWEEN :today AND :next_30
        ORDER BY event_date_time ASC
        LIMIT 10
    ),
    overdue_tasks AS (
        SELECT * FROM tasks 
        WHERE wedding_id = :wedding_id 
          AND is_complete = false
          AND due_date < :today
        ORDER BY due_date ASC
        LIMIT 10
    ),
    urgent_tasks AS (
        SELECT * FROM tasks 
        WHERE wedding_id = :wedding_id 
          AND is_complete = false
          AND due_date BETWEEN :today AND :next_30
        ORDER BY due_date ASC
        LIMIT 10
    ),
    upcoming_deadlines AS (
        SELECT task_id, title, due_date, priority, category 
        FROM tasks 
        WHERE wedding_id = :wedding_id 
          AND is_complete = false
          AND due_date <= :next_14
        ORDER BY due_date ASC
        LIMIT 5
    )
    SELECT 
      (SELECT COALESCE(json_agg(upcoming_events), '[]'::json) FROM upcoming_events) AS upcoming_events,
      (SELECT COALESCE(json_agg(overdue_tasks), '[]'::json) FROM overdue_tasks) AS overdue_tasks,
      (SELECT COALESCE(json_agg(urgent_tasks), '[]'::json) FROM urgent_tasks) AS urgent_tasks,
      (SELECT COALESCE(json_agg(upcoming_deadlines), '[]'::json) FROM upcoming_deadlines) AS upcoming_deadlines;
    """
    try:
        res = await execute_supabase_sql(
            sql,
            {"wedding_id": wedding_id, "today": today.isoformat(), "next_30": next_30.isoformat(), "next_14": next_14.isoformat()},
        )
        if res.get("status") == "success" and res.get("data"):
            row = res["data"][0]
            return {
                "upcoming_events": row.get("upcoming_events", []),
                "overdue_tasks": row.get("overdue_tasks", []),
                "urgent_tasks": row.get("urgent_tasks", []),
                "upcoming_deadlines": row.get("upcoming_deadlines", []),
                "timeline_summary": {
                    "upcoming_count": len(row.get("upcoming_events", []) or []),
                    "overdue_count": len(row.get("overdue_tasks", []) or []),
                    "urgent_count": len(row.get("urgent_tasks", []) or []),
                },
            }
    except Exception as e:
        logger.debug(f"_get_timeline_and_deadlines failed: {e}")
    return {
        "upcoming_events": [],
        "overdue_tasks": [],
        "urgent_tasks": [],
        "upcoming_deadlines": [],
        "timeline_summary": {"upcoming_count": 0, "overdue_count": 0, "urgent_count": 0},
    }


async def _get_shortlisted_vendors(wedding_id: str) -> Dict[str, Any]:
    sql = """
    SELECT * FROM user_shortlisted_vendors 
    WHERE wedding_id = :wedding_id
    ORDER BY created_at DESC
    LIMIT 10;
    """
    try:
        res = await execute_supabase_sql(sql, {"wedding_id": wedding_id})
        if res.get("status") == "success" and res.get("data") is not None:
            return {"shortlisted_vendors": res.get("data", [])}
    except Exception as e:
        logger.debug(f"_get_shortlisted_vendors failed: {e}")
    return {"shortlisted_vendors": []}


async def _get_pending_actions(wedding_id: str, user_role: Optional[str]) -> Dict[str, Any]:
    sql = """
    WITH pending_reviews AS (
        SELECT * FROM tasks 
        WHERE wedding_id = :wedding_id 
          AND status IN ('pending_review', 'pending_final_approval')
          AND (lead_party = :user_party OR lead_party = 'couple')
        LIMIT 10
    ),
    awaiting_workflows AS (
        SELECT * FROM workflows 
        WHERE wedding_id = :wedding_id 
          AND status = 'awaiting_feedback'
        LIMIT 10
    )
    SELECT 
      (SELECT COALESCE(json_agg(pending_reviews), '[]'::json) FROM pending_reviews) AS pending_reviews,
      (SELECT COALESCE(json_agg(awaiting_workflows), '[]'::json) FROM awaiting_workflows) AS awaiting_workflows;
    """
    user_party = f"{user_role}_side" if user_role in ("bride", "groom") else (user_role or "member")
    try:
        res = await execute_supabase_sql(sql, {"wedding_id": wedding_id, "user_party": user_party})
        if res.get("status") == "success" and res.get("data"):
            row = res["data"][0]
            return {
                "pending_actions": {
                    "pending_reviews": row.get("pending_reviews", []),
                    "awaiting_workflows": row.get("awaiting_workflows", []),
                }
            }
    except Exception as e:
        logger.debug(f"_get_pending_actions failed: {e}")
    return {"pending_actions": {"pending_reviews": [], "awaiting_workflows": []}}


async def assemble_baseline_context(
    wedding_id: str,
    user_id: str,
    user_role: Optional[str],
    cap: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Build a compact, stable context dict with safe defaults and capped lists.
    """
    defaults = _safe_defaults()
    defaults.update({
        "current_wedding_id": wedding_id,
        "current_user_id": user_id,
        "current_user_role": user_role,
    })

    try:
        core, tw, budget, timebox, vendors, pending = await _gather_parallel(
            wedding_id, user_id, user_role
        )
        ctx: Dict[str, Any] = {**defaults, **core, **tw, **budget, **timebox, **vendors, **pending}
    except Exception as e:
        logger.error(f"assemble_baseline_context failed (falling back to defaults): {e}")
        ctx = defaults

    # Cap lists to avoid prompt bloat
    caps = cap or {
        "active_workflows": 10,
        "relevant_tasks": 25,
        "shortlisted_vendors": 10,
        "recent_expenses": 10,
        "upcoming_events": 10,
        "overdue_tasks": 10,
        "urgent_tasks": 10,
        "upcoming_deadlines": 5,
        "calendar_events": 20,
    }
    try:
        for k, limit in caps.items():
            if isinstance(ctx.get(k), list) and len(ctx[k]) > limit:
                ctx[k] = ctx[k][:limit]
    except Exception as e:
        logger.debug(f"assemble_baseline_context capping failed: {e}")
    return ctx


async def _gather_parallel(wedding_id: str, user_id: str, user_role: Optional[str]):
    """Gather slices concurrently using asyncio.gather to reduce latency."""
    core_coro = _get_core_context(wedding_id, user_id)
    tw_coro = _get_tasks_and_workflows(wedding_id)
    budget_coro = _get_budget_summaries(wedding_id)
    timebox_coro = _get_timeline_and_deadlines(wedding_id)
    vendors_coro = _get_shortlisted_vendors(wedding_id)
    pending_coro = _get_pending_actions(wedding_id, user_role)

    core, tw, budget, timebox, vendors, pending = await asyncio.gather(
        core_coro, tw_coro, budget_coro, timebox_coro, vendors_coro, pending_coro,
        return_exceptions=False,
    )
    return core, tw, budget, timebox, vendors, pending
