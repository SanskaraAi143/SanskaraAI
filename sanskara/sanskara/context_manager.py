"""
Smart Context Manager for Orchestrator Agent
Provides intent-driven, optimized context loading
"""

import json
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from sanskara.helpers import execute_supabase_sql
from logger import json_logger as logger


class ContextScope(Enum):
    """Defines different context scopes based on user intent"""
    MINIMAL = "minimal"           # Just wedding basics + user info
    WORKFLOW_FOCUSED = "workflow" # Specific workflow + related tasks
    BUDGET_FOCUSED = "budget"     # Budget + payment + vendor costs
    VENDOR_FOCUSED = "vendor"     # Vendor workflows + shortlisted vendors
    TIMELINE_FOCUSED = "timeline" # Timeline + deadlines + urgent tasks
    PROACTIVE = "proactive"       # Smart full context for proactive suggestions
    FULL = "full"                # Everything (fallback)


class UserIntent(Enum):
    """User intent categories for context optimization"""
    VENDOR_SEARCH = "vendor_search"
    BUDGET_MANAGEMENT = "budget_management"
    TIMELINE_PLANNING = "timeline_planning"
    TASK_MANAGEMENT = "task_management"
    RITUAL_INQUIRY = "ritual_inquiry"
    GENERAL_PLANNING = "general_planning"
    STATUS_CHECK = "status_check"
    PROACTIVE_GREETING = "proactive_greeting"  # When user just says hi/hello
    OPEN_ENDED = "open_ended"                  # Vague questions needing proactive response


@dataclass
class ContextRequest:
    """Represents a context loading request"""
    wedding_id: str
    user_id: str
    user_role: str
    intent: UserIntent
    scope: ContextScope
    specific_ids: Optional[List[str]] = None  # Specific workflow/task IDs
    include_budget: bool = False
    include_timeline: bool = False
    include_pending_actions: bool = True


class SmartContextManager:
    """Intelligent context manager that provides targeted context based on user intent"""
    
    def __init__(self):
        self.intent_to_scope_mapping = {
            UserIntent.VENDOR_SEARCH: ContextScope.VENDOR_FOCUSED,
            UserIntent.BUDGET_MANAGEMENT: ContextScope.BUDGET_FOCUSED,
            UserIntent.TIMELINE_PLANNING: ContextScope.TIMELINE_FOCUSED,
            UserIntent.TASK_MANAGEMENT: ContextScope.WORKFLOW_FOCUSED,
            UserIntent.RITUAL_INQUIRY: ContextScope.MINIMAL,
            UserIntent.STATUS_CHECK: ContextScope.PROACTIVE,     # Need full view for status
            UserIntent.PROACTIVE_GREETING: ContextScope.PROACTIVE,  # Need full view for suggestions
            UserIntent.OPEN_ENDED: ContextScope.PROACTIVE,      # Need full view for proactive response
            UserIntent.GENERAL_PLANNING: ContextScope.PROACTIVE, # Changed from FULL to PROACTIVE
        }
    
    async def get_smart_context(self, request: ContextRequest) -> Dict[str, Any]:
        """
        Main method to get optimized context based on user intent
        """
        logger.info(f"Getting smart context for intent: {request.intent}, scope: {request.scope}")
        
        # Always get core context
        context = await self._get_core_context(request.wedding_id, request.user_id, request.user_role)
        
        # Add scope-specific context
        if request.scope == ContextScope.MINIMAL:
            # Already have core context
            pass
        elif request.scope == ContextScope.VENDOR_FOCUSED:
            vendor_context = await self._get_vendor_context(request.wedding_id)
            context.update(vendor_context)
        elif request.scope == ContextScope.BUDGET_FOCUSED:
            budget_context = await self._get_budget_context(request.wedding_id)
            context.update(budget_context)
        elif request.scope == ContextScope.TIMELINE_FOCUSED:
            timeline_context = await self._get_timeline_context(request.wedding_id)
            context.update(timeline_context)
        elif request.scope == ContextScope.WORKFLOW_FOCUSED:
            workflow_context = await self._get_workflow_context(request.wedding_id, request.specific_ids)
            context.update(workflow_context)
        elif request.scope == ContextScope.PROACTIVE:
            proactive_context = await self._get_proactive_context(request.wedding_id, request.user_role)
            context.update(proactive_context)
        else:  # FULL
            full_context = await self._get_full_context(request.wedding_id)
            context.update(full_context)
        
        # Always include pending actions if requested
        if request.include_pending_actions:
            pending_context = await self._get_pending_actions_context(request.wedding_id, request.user_role)
            context.update(pending_context)
        
        # Add dynamic inclusions
        if request.include_budget and request.scope != ContextScope.BUDGET_FOCUSED:
            budget_summary = await self._get_budget_summary(request.wedding_id)
            context["budget_summary"] = budget_summary
        
        if request.include_timeline and request.scope != ContextScope.TIMELINE_FOCUSED:
            upcoming_deadlines = await self._get_upcoming_deadlines(request.wedding_id)
            context["upcoming_deadlines"] = upcoming_deadlines
        
        # Ensure essential fields are always present with defaults (for prompt template compatibility)
        try:
            self._ensure_default_fields(context, request.scope)
        except Exception as e:
            logger.error(f"Error in _ensure_default_fields: {e}", exc_info=True)
            # Add shortlisted_vendors manually if there was an error
            if "shortlisted_vendors" not in context:
                context["shortlisted_vendors"] = []
                logger.info("Manually added shortlisted_vendors = [] due to error")
        
        logger.info(f"Context loaded with keys: {list(context.keys())}")
        return context
    
    async def _get_core_context(self, wedding_id: str, user_id: str, user_role: str) -> Dict[str, Any]:
        """Get essential wedding and user information"""
        sql = """
        SELECT 
            w.*,
            u.display_name as user_display_name,
            u.email as user_email
        FROM weddings w
        LEFT JOIN users u ON u.user_id = :user_id
        WHERE w.wedding_id = :wedding_id;
        """
        
        result = await execute_supabase_sql(sql, {
            "wedding_id": wedding_id, 
            "user_id": user_id
        })
        
        if result.get("status") == "success" and result.get("data"):
            wedding_data = result["data"][0]
            return {
                "wedding_data": wedding_data,
                "current_wedding_id": wedding_id,
                "current_user_id": user_id,
                "current_user_role": user_role,
                "user_display_name": wedding_data.get("user_display_name"),
                "user_email": wedding_data.get("user_email")
            }
        
        return {
            "wedding_data": {},
            "current_wedding_id": wedding_id,
            "current_user_id": user_id,
            "current_user_role": user_role
        }
    
    async def _get_vendor_context(self, wedding_id: str) -> Dict[str, Any]:
        """Get vendor-related context"""
        sql = """
        WITH vendor_workflows AS (
            SELECT * FROM workflows 
            WHERE wedding_id = :wedding_id 
            AND workflow_name ILIKE '%vendor%'
            AND status IN ('in_progress', 'paused', 'awaiting_feedback')
        ),
        vendor_tasks AS (
            SELECT * FROM tasks 
            WHERE wedding_id = :wedding_id 
            AND category ILIKE '%vendor%'
            AND is_complete = false
        ),
        shortlisted_vendors AS (
            SELECT * FROM user_shortlisted_vendors 
            WHERE wedding_id = :wedding_id
            ORDER BY created_at DESC
            LIMIT 10
        )
        SELECT 
            (SELECT COALESCE(json_agg(vendor_workflows), '[]'::json) FROM vendor_workflows) as vendor_workflows,
            (SELECT COALESCE(json_agg(vendor_tasks), '[]'::json) FROM vendor_tasks) as vendor_tasks,
            (SELECT COALESCE(json_agg(shortlisted_vendors), '[]'::json) FROM shortlisted_vendors) as shortlisted_vendors;
        """
        
        result = await execute_supabase_sql(sql, {"wedding_id": wedding_id})
        
        if result.get("status") == "success" and result.get("data"):
            data = result["data"][0]
            return {
                "active_workflows": data.get("vendor_workflows", []),
                "relevant_tasks": data.get("vendor_tasks", []),
                "shortlisted_vendors": data.get("shortlisted_vendors", [])
            }
        
        return {"active_workflows": [], "relevant_tasks": [], "shortlisted_vendors": []}
    
    async def _get_budget_context(self, wedding_id: str) -> Dict[str, Any]:
        """Get comprehensive budget context"""
        sql = """
        WITH budget_summary AS (
            SELECT 
                category,
                SUM(estimated_cost) as total_estimated,
                SUM(actual_cost) as total_actual,
                COUNT(*) as item_count
            FROM budget_items 
            WHERE wedding_id = :wedding_id
            GROUP BY category
        ),
        recent_expenses AS (
            SELECT * FROM budget_items 
            WHERE wedding_id = :wedding_id 
            AND actual_cost > 0
            ORDER BY updated_at DESC
            LIMIT 5
        ),
        budget_workflows AS (
            SELECT * FROM workflows 
            WHERE wedding_id = :wedding_id 
            AND workflow_name ILIKE '%budget%'
            AND status IN ('in_progress', 'paused', 'awaiting_feedback')
        )
        SELECT 
            (SELECT COALESCE(json_agg(budget_summary), '[]'::json) FROM budget_summary) as budget_by_category,
            (SELECT COALESCE(json_agg(recent_expenses), '[]'::json) FROM recent_expenses) as recent_expenses,
            (SELECT COALESCE(json_agg(budget_workflows), '[]'::json) FROM budget_workflows) as budget_workflows,
            (SELECT 
                COALESCE(SUM(estimated_cost), 0) as total_budget,
                COALESCE(SUM(actual_cost), 0) as total_spent,
                COALESCE(SUM(estimated_cost) - SUM(actual_cost), 0) as remaining_budget
             FROM budget_items WHERE wedding_id = :wedding_id
            ) as budget_totals;
        """
        
        result = await execute_supabase_sql(sql, {"wedding_id": wedding_id})
        
        if result.get("status") == "success" and result.get("data"):
            data = result["data"][0]
            return {
                "budget_by_category": data.get("budget_by_category", []),
                "recent_expenses": data.get("recent_expenses", []),
                "active_workflows": data.get("budget_workflows", []),
                "budget_totals": data.get("budget_totals", {}),
                "budget_summary": data.get("budget_totals", {})
            }
        
        return {"budget_by_category": [], "recent_expenses": [], "budget_totals": {}}
    
    async def _get_timeline_context(self, wedding_id: str) -> Dict[str, Any]:
        """Get timeline and deadline context"""
        today = datetime.now().date()
        next_30_days = today + timedelta(days=30)
        
        sql = """
        WITH upcoming_events AS (
            SELECT * FROM timeline_events 
            WHERE wedding_id = :wedding_id 
            AND event_date_time::date BETWEEN :today AND :next_30_days
            ORDER BY event_date_time ASC
        ),
        overdue_tasks AS (
            SELECT * FROM tasks 
            WHERE wedding_id = :wedding_id 
            AND due_date < :today
            AND is_complete = false
        ),
        urgent_tasks AS (
            SELECT * FROM tasks 
            WHERE wedding_id = :wedding_id 
            AND due_date BETWEEN :today AND :next_30_days
            AND is_complete = false
            ORDER BY due_date ASC
        )
        SELECT 
            (SELECT COALESCE(json_agg(upcoming_events), '[]'::json) FROM upcoming_events) as upcoming_events,
            (SELECT COALESCE(json_agg(overdue_tasks), '[]'::json) FROM overdue_tasks) as overdue_tasks,
            (SELECT COALESCE(json_agg(urgent_tasks), '[]'::json) FROM urgent_tasks) as urgent_tasks;
        """
        
        result = await execute_supabase_sql(sql, {
            "wedding_id": wedding_id,
            "today": today.isoformat(),
            "next_30_days": next_30_days.isoformat()
        })
        
        if result.get("status") == "success" and result.get("data"):
            data = result["data"][0]
            return {
                "upcoming_events": data.get("upcoming_events", []),
                "overdue_tasks": data.get("overdue_tasks", []),
                "urgent_tasks": data.get("urgent_tasks", []),
                "timeline_summary": {
                    "upcoming_count": len(data.get("upcoming_events", [])),
                    "overdue_count": len(data.get("overdue_tasks", [])),
                    "urgent_count": len(data.get("urgent_tasks", []))
                }
            }
        
        return {"upcoming_events": [], "overdue_tasks": [], "urgent_tasks": []}
    
    async def _get_workflow_context(self, wedding_id: str, specific_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get workflow-specific context"""
        where_clause = "wedding_id = :wedding_id AND status IN ('in_progress', 'paused', 'awaiting_feedback')"
        params = {"wedding_id": wedding_id}
        
        if specific_ids:
            placeholders = ",".join([f":id_{i}" for i in range(len(specific_ids))])
            where_clause += f" AND workflow_id IN ({placeholders})"
            for i, workflow_id in enumerate(specific_ids):
                params[f"id_{i}"] = workflow_id
        
        sql = f"""
        WITH relevant_workflows AS (
            SELECT * FROM workflows WHERE {where_clause}
        ),
        workflow_tasks AS (
            SELECT t.* FROM tasks t
            INNER JOIN relevant_workflows w ON t.workflow_id = w.workflow_id
            WHERE t.is_complete = false
        )
        SELECT 
            (SELECT COALESCE(json_agg(relevant_workflows), '[]'::json) FROM relevant_workflows) as active_workflows,
            (SELECT COALESCE(json_agg(workflow_tasks), '[]'::json) FROM workflow_tasks) as relevant_tasks;
        """
        
        result = await execute_supabase_sql(sql, params)
        
        if result.get("status") == "success" and result.get("data"):
            data = result["data"][0]
            return {
                "active_workflows": data.get("active_workflows", []),
                "relevant_tasks": data.get("relevant_tasks", [])
            }
        
        return {"active_workflows": [], "relevant_tasks": []}
    
    async def _get_proactive_context(self, wedding_id: str, user_role: str) -> Dict[str, Any]:
        """
        Get SMART FULL context optimized for proactive suggestions.
        This provides comprehensive but intelligently filtered information for the AI 
        to identify patterns, spot issues, and suggest next best actions.
        """
        sql = """
        WITH 
        -- Priority items requiring attention
        high_priority_items AS (
            SELECT 
                'task' as item_type,
                task_id as item_id,
                title as item_name,
                status,
                priority,
                due_date,
                lead_party,
                category,
                'overdue' as urgency_level
            FROM tasks 
            WHERE wedding_id = :wedding_id 
            AND is_complete = false 
            AND due_date < CURRENT_DATE
            
            UNION ALL
            
            SELECT 
                'task' as item_type,
                task_id as item_id,
                title as item_name,
                status,
                priority,
                due_date,
                lead_party,
                category,
                'urgent' as urgency_level
            FROM tasks 
            WHERE wedding_id = :wedding_id 
            AND is_complete = false 
            AND due_date BETWEEN CURRENT_DATE AND (CURRENT_DATE + INTERVAL '14 days')
            AND priority = 'high'
            
            UNION ALL
            
            SELECT 
                'workflow' as item_type,
                workflow_id as item_id,
                workflow_name as item_name,
                status,
                'medium' as priority,
                NULL as due_date,
                NULL as lead_party,
                'workflow' as category,
                'blocked' as urgency_level
            FROM workflows 
            WHERE wedding_id = :wedding_id 
            AND status = 'awaiting_feedback'
            AND updated_at < (CURRENT_TIMESTAMP - INTERVAL '7 days')
        ),
        
        -- Recent activity for momentum tracking
        recent_activity AS (
            SELECT 
                'task_completed' as activity_type,
                title as activity_description,
                updated_at as activity_time,
                category
            FROM tasks 
            WHERE wedding_id = :wedding_id 
            AND is_complete = true 
            AND updated_at > (CURRENT_TIMESTAMP - INTERVAL '7 days')
            
            UNION ALL
            
            SELECT 
                'vendor_shortlisted' as activity_type,
                vendor_name as activity_description,
                created_at as activity_time,
                vendor_category as category
            FROM user_shortlisted_vendors 
            WHERE wedding_id = :wedding_id 
            AND created_at > (CURRENT_TIMESTAMP - INTERVAL '7 days')
            
            ORDER BY activity_time DESC
            LIMIT 10
        ),
        
        -- Progress by category for pattern recognition
        category_progress AS (
            SELECT 
                category,
                COUNT(*) as total_tasks,
                COUNT(*) FILTER (WHERE is_complete = true) as completed_tasks,
                COUNT(*) FILTER (WHERE is_complete = false AND due_date < CURRENT_DATE) as overdue_tasks,
                ROUND(
                    (COUNT(*) FILTER (WHERE is_complete = true)::float / COUNT(*)) * 100.0
                )::integer as completion_percentage
            FROM tasks 
            WHERE wedding_id = :wedding_id 
            AND category IS NOT NULL
            GROUP BY category
        ),
        
        -- Budget insights for recommendations
        budget_insights AS (
            SELECT 
                category,
                SUM(estimated_cost) as budgeted_amount,
                SUM(actual_cost) as spent_amount,
                SUM(estimated_cost) - SUM(actual_cost) as remaining_amount,
                CASE 
                    WHEN SUM(estimated_cost) > 0 THEN
                        ROUND((SUM(actual_cost) / SUM(estimated_cost)) * 100.0)::integer
                    ELSE 0 
                END as spend_percentage,
                COUNT(*) as item_count
            FROM budget_items 
            WHERE wedding_id = :wedding_id 
            GROUP BY category
            HAVING SUM(estimated_cost) > 0
        ),
        
        -- Key workflows and their status for orchestration
        key_workflows AS (
            SELECT 
                w.*,
                COUNT(t.task_id) as total_tasks,
                COUNT(t.task_id) FILTER (WHERE t.is_complete = true) as completed_tasks,
                COUNT(t.task_id) FILTER (WHERE t.is_complete = false AND t.due_date < CURRENT_DATE) as overdue_tasks
            FROM workflows w
            LEFT JOIN tasks t ON w.workflow_id = t.workflow_id
            WHERE w.wedding_id = :wedding_id 
            AND w.status IN ('in_progress', 'paused', 'awaiting_feedback', 'not_started')
            GROUP BY w.workflow_id
        ),
        
        -- Next suggested actions based on wedding timeline
        wedding_timeline_context AS (
            SELECT 
                wedding_date,
                wedding_date - CURRENT_DATE as days_until_wedding,
                CASE 
                    WHEN wedding_date - CURRENT_DATE > 365 THEN 'planning_phase'
                    WHEN wedding_date - CURRENT_DATE > 180 THEN 'major_vendors_phase'
                    WHEN wedding_date - CURRENT_DATE > 90 THEN 'details_phase'
                    WHEN wedding_date - CURRENT_DATE > 30 THEN 'final_preparations_phase'
                    ELSE 'crunch_time_phase'
                END as planning_phase
            FROM weddings 
            WHERE wedding_id = :wedding_id
        )
        
        SELECT 
            (SELECT COALESCE(json_agg(high_priority_items ORDER BY 
                CASE urgency_level 
                    WHEN 'overdue' THEN 1 
                    WHEN 'blocked' THEN 2 
                    WHEN 'urgent' THEN 3 
                    ELSE 4 
                END
            ), '[]'::json) FROM high_priority_items) as priority_items,
            
            (SELECT COALESCE(json_agg(recent_activity), '[]'::json) FROM recent_activity) as recent_activity,
            
            (SELECT COALESCE(json_agg(category_progress ORDER BY completion_percentage DESC), '[]'::json) FROM category_progress) as progress_by_category,
            
            (SELECT COALESCE(json_agg(budget_insights ORDER BY spend_percentage DESC), '[]'::json) FROM budget_insights) as budget_insights,
            
            (SELECT COALESCE(json_agg(key_workflows ORDER BY 
                CASE status 
                    WHEN 'awaiting_feedback' THEN 1 
                    WHEN 'in_progress' THEN 2 
                    WHEN 'paused' THEN 3 
                    ELSE 4 
                END
            ), '[]'::json) FROM key_workflows) as active_workflows,
            
            (SELECT row_to_json(wedding_timeline_context) FROM wedding_timeline_context) as timeline_context;
        """
        
        result = await execute_supabase_sql(sql, {"wedding_id": wedding_id})
        
        if result.get("status") == "success" and result.get("data"):
            data = result["data"][0]
            
            # Add intelligent next actions based on the data
            next_actions = self._generate_smart_next_actions(data, user_role)
            
            return {
                "priority_items": data.get("priority_items", []),
                "recent_activity": data.get("recent_activity", []),
                "progress_by_category": data.get("progress_by_category", []),
                "budget_insights": data.get("budget_insights", []),
                "active_workflows": data.get("key_workflows", data.get("active_workflows", [])),
                "timeline_context": data.get("timeline_context", {}),
                "suggested_next_actions": next_actions,
                "top_3_next_actions": next_actions[:3],
                "proactive_insights": self._generate_proactive_insights(data, user_role)
            }
        
        return {
            "priority_items": [],
            "recent_activity": [],
            "progress_by_category": [],
            "budget_insights": [],
            "active_workflows": [],
            "timeline_context": {},
            "suggested_next_actions": [],
            "top_3_next_actions": [],
            "proactive_insights": {}
        }
    
    def _generate_smart_next_actions(self, context_data: Dict[str, Any], user_role: str) -> List[Dict[str, Any]]:
        """Generate intelligent next action suggestions based on context analysis"""
        actions = []
        
        # Check for overdue items
        priority_items = context_data.get("priority_items", [])
        overdue_items = [item for item in priority_items if item.get("urgency_level") == "overdue"]
        
        if overdue_items:
            for item in overdue_items[:3]:  # Top 3 overdue
                if item.get("lead_party") == f"{user_role}_side" or item.get("lead_party") == "couple":
                    actions.append({
                        "action_type": "urgent_task",
                        "priority": "high",
                        "description": f"Complete overdue task: {item.get('item_name')}",
                        "reasoning": f"This task was due {item.get('due_date')} and is blocking progress",
                        "category": item.get("category")
                    })
        
        # Check for stalled workflows
        blocked_workflows = [item for item in priority_items if item.get("urgency_level") == "blocked"]
        for workflow in blocked_workflows:
            actions.append({
                "action_type": "unblock_workflow",
                "priority": "high", 
                "description": f"Provide feedback for {workflow.get('item_name')}",
                "reasoning": "This workflow has been waiting for feedback for over a week",
                "category": "workflow_management"
            })
        
        # Check for categories with low progress
        progress_data = context_data.get("progress_by_category", [])
        low_progress_categories = [cat for cat in progress_data if cat.get("completion_percentage", 0) < 20]
        
        for category in low_progress_categories[:2]:  # Top 2 categories needing attention
            actions.append({
                "action_type": "focus_category",
                "priority": "medium",
                "description": f"Focus on {category.get('category')} planning",
                "reasoning": f"Only {category.get('completion_percentage')}% complete with {category.get('total_tasks')} tasks",
                "category": category.get("category")
            })
        
        # Timeline-based suggestions
        timeline = context_data.get("timeline_context", {})
        planning_phase = timeline.get("planning_phase")
        days_until = timeline.get("days_until_wedding", 365)
        
        if planning_phase == "major_vendors_phase" and days_until < 200:
            actions.append({
                "action_type": "vendor_focus",
                "priority": "high",
                "description": "Prioritize booking major vendors (venue, catering, photography)",
                "reasoning": f"With {days_until} days until wedding, major vendors should be secured",
                "category": "vendor_management"
            })
        
        return actions[:5]  # Return top 5 actions
    
    def _generate_proactive_insights(self, context_data: Dict[str, Any], user_role: str) -> Dict[str, Any]:
        """Generate proactive insights for the orchestrator to use"""
        insights = {}
        
        # Budget insights
        budget_data = context_data.get("budget_insights", [])
        if budget_data:
            over_budget_categories = [cat for cat in budget_data if cat.get("spend_percentage", 0) > 90]
            under_budget_categories = [cat for cat in budget_data if cat.get("spend_percentage", 0) < 50]
            
            insights["budget_status"] = {
                "over_budget_categories": over_budget_categories,
                "under_budget_categories": under_budget_categories,
                "total_categories": len(budget_data)
            }
        
        # Progress insights
        progress_data = context_data.get("progress_by_category", [])
        if progress_data:
            completed_categories = [cat for cat in progress_data if cat.get("completion_percentage", 0) == 100]
            lagging_categories = [cat for cat in progress_data if cat.get("completion_percentage", 0) < 30]
            
            insights["progress_status"] = {
                "completed_categories": len(completed_categories),
                "lagging_categories": lagging_categories,
                "total_categories": len(progress_data)
            }
        
        # Timeline insights
        timeline = context_data.get("timeline_context", {})
        insights["timeline_pressure"] = {
            "days_remaining": timeline.get("days_until_wedding", 365),
            "planning_phase": timeline.get("planning_phase", "planning_phase"),
            "urgency_level": self._calculate_urgency_level(timeline.get("days_until_wedding", 365))
        }
        
        # Recent momentum
        recent_activity = context_data.get("recent_activity", [])
        insights["momentum"] = {
            "recent_completions": len([act for act in recent_activity if act.get("activity_type") == "task_completed"]),
            "recent_vendor_activity": len([act for act in recent_activity if act.get("activity_type") == "vendor_shortlisted"]),
            "activity_level": "high" if len(recent_activity) > 5 else "medium" if len(recent_activity) > 2 else "low"
        }
        
        return insights
    
    def _calculate_urgency_level(self, days_until_wedding: int) -> str:
        """Calculate urgency level based on days until wedding"""
        if days_until_wedding < 30:
            return "critical"
        elif days_until_wedding < 90:
            return "high"
        elif days_until_wedding < 180:
            return "medium"
        else:
            return "low"
    
    async def _get_pending_actions_context(self, wedding_id: str, user_role: str) -> Dict[str, Any]:
        """Get tasks/workflows requiring user attention"""
        sql = """
        WITH pending_reviews AS (
            SELECT * FROM tasks 
            WHERE wedding_id = :wedding_id 
            AND status IN ('pending_review', 'pending_final_approval')
            AND (lead_party = :user_party OR lead_party = 'couple')
        ),
        awaiting_workflows AS (
            SELECT * FROM workflows 
            WHERE wedding_id = :wedding_id 
            AND status = 'awaiting_feedback'
        )
        SELECT 
            (SELECT COALESCE(json_agg(pending_reviews), '[]'::json) FROM pending_reviews) as pending_reviews,
            (SELECT COALESCE(json_agg(awaiting_workflows), '[]'::json) FROM awaiting_workflows) as awaiting_workflows;
        """
        
        user_party = f"{user_role}_side" if user_role in ['bride', 'groom'] else user_role
        
        result = await execute_supabase_sql(sql, {
            "wedding_id": wedding_id,
            "user_party": user_party
        })
        
        if result.get("status") == "success" and result.get("data"):
            data = result["data"][0]
            return {
                "pending_actions": {
                    "pending_reviews": data.get("pending_reviews", []),
                    "awaiting_workflows": data.get("awaiting_workflows", [])
                }
            }
        
        return {"pending_actions": {"pending_reviews": [], "awaiting_workflows": []}}
    
    async def _get_budget_summary(self, wedding_id: str) -> Dict[str, Any]:
        """Get quick budget summary (corrected column names)"""
        sql = """
        SELECT 
            COALESCE(SUM(amount), 0) as total_budget,
            COUNT(*) as total_items,
            SUM(CASE WHEN status = 'Paid' THEN amount ELSE 0 END) as total_spent,
            SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END) as pending_amount
        FROM budget_items 
        WHERE wedding_id = :wedding_id;
        """
        
        result = await execute_supabase_sql(sql, {"wedding_id": wedding_id})
        
        if result.get("status") == "success" and result.get("data"):
            data = result["data"][0]
            return {
                "total_budget": data.get("total_budget", 0),
                "total_spent": data.get("total_spent", 0), 
                "pending_amount": data.get("pending_amount", 0),
                "total_items": data.get("total_items", 0)
            }
        
        return {"total_budget": 0, "total_spent": 0, "pending_amount": 0, "total_items": 0}
    
    async def _get_upcoming_deadlines(self, wedding_id: str) -> List[Dict[str, Any]]:
        """Get upcoming deadlines"""
        next_14_days = (datetime.now().date() + timedelta(days=14)).isoformat()
        
        sql = """
        SELECT task_id, title, due_date, priority, category 
        FROM tasks 
        WHERE wedding_id = :wedding_id 
        AND due_date <= :next_14_days
        AND is_complete = false
        ORDER BY due_date ASC
        LIMIT 5;
        """
        
        result = await execute_supabase_sql(sql, {
            "wedding_id": wedding_id,
            "next_14_days": next_14_days
        })
        
        if result.get("status") == "success" and result.get("data"):
            return result["data"]
        
        return []
    
    def _ensure_default_fields(self, context: Dict[str, Any], scope: ContextScope):
        """
        Ensure essential fields are always present for prompt template compatibility.
        This prevents KeyError exceptions when the prompt template references fields
        that aren't included in certain context scopes.
        """
        logger.info(f"_ensure_default_fields called for scope: {scope}, current keys: {list(context.keys())}")
        
        # Vendor-related fields (used in prompt template)
        if "shortlisted_vendors" not in context:
            context["shortlisted_vendors"] = []
            logger.info("Added default shortlisted_vendors = []")
        
        # Budget-related fields
        if "budget_by_category" not in context:
            context["budget_by_category"] = []
        if "budget_totals" not in context:
            context["budget_totals"] = {"total_budget": 0, "total_spent": 0, "remaining_budget": 0}
        if "recent_expenses" not in context:
            context["recent_expenses"] = []
        
        # Timeline-related fields
        if "upcoming_events" not in context:
            context["upcoming_events"] = []
        if "overdue_tasks" not in context:
            context["overdue_tasks"] = []
        if "urgent_tasks" not in context:
            context["urgent_tasks"] = []
        if "timeline_summary" not in context:
            context["timeline_summary"] = {"upcoming_count": 0, "overdue_count": 0, "urgent_count": 0}
        
        # Workflow-related fields  
        if "active_workflows" not in context:
            context["active_workflows"] = []
        if "relevant_tasks" not in context:
            context["relevant_tasks"] = []
        
        # Proactive fields (only add empty defaults if not already present)
        if "priority_items" not in context:
            context["priority_items"] = []
        if "recent_activity" not in context:
            context["recent_activity"] = []
        if "progress_by_category" not in context:
            context["progress_by_category"] = []
        if "budget_insights" not in context:
            context["budget_insights"] = []
        if "timeline_context" not in context:
            context["timeline_context"] = {}
        if "suggested_next_actions" not in context:
            context["suggested_next_actions"] = []
        if "top_3_next_actions" not in context:
            context["top_3_next_actions"] = {}
        if "proactive_insights" not in context:
            context["proactive_insights"] = {}
        
        # Pending actions
        if "pending_actions" not in context:
            context["pending_actions"] = {"pending_reviews": [], "awaiting_workflows": []}
        
        # Budget summary (for cross-scope inclusion)
        if "budget_summary" not in context:
            context["budget_summary"] = {"total_budget": 0, "total_spent": 0, "pending_amount": 0, "total_items": 0}
        
        # Upcoming deadlines (for cross-scope inclusion)
        if "upcoming_deadlines" not in context:
            context["upcoming_deadlines"] = []
    
    async def _get_full_context(self, wedding_id: str) -> Dict[str, Any]:
        """Get complete context (fallback)"""
        # This is similar to the original get_complete_wedding_context but more organized
        sql = """
        WITH all_workflows AS (
            SELECT * FROM workflows 
            WHERE wedding_id = :wedding_id 
            AND status IN ('in_progress', 'paused', 'awaiting_feedback')
        ),
        all_tasks AS (
            SELECT * FROM tasks 
            WHERE wedding_id = :wedding_id 
            AND is_complete = false
        )
        SELECT 
            (SELECT COALESCE(json_agg(all_workflows), '[]'::json) FROM all_workflows) as active_workflows,
            (SELECT COALESCE(json_agg(all_tasks), '[]'::json) FROM all_tasks) as all_tasks;
        """
        
        result = await execute_supabase_sql(sql, {"wedding_id": wedding_id})
        
        if result.get("status") == "success" and result.get("data"):
            data = result["data"][0]
            return {
                "active_workflows": data.get("active_workflows", []),
                "all_tasks": data.get("all_tasks", [])
            }
        
        return {"active_workflows": [], "all_tasks": []}
    
    def infer_user_intent(self, user_message: str) -> UserIntent:
        """
        Infer user intent from their message
        Enhanced to detect proactive scenarios
        """
        message_lower = user_message.lower().strip()
        
        # Handle empty or very short messages (proactive scenarios)
        if len(message_lower) < 5:
            return UserIntent.PROACTIVE_GREETING
        
        # Greeting patterns (need proactive response)
        greeting_patterns = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']
        if any(greeting in message_lower for greeting in greeting_patterns):
            return UserIntent.PROACTIVE_GREETING
        
        # Open-ended questions requiring proactive suggestions
        open_ended_patterns = [
            'what should i do',
            'what next',
            'help me',
            'what do you recommend',
            'where do i start',
            'what\'s the plan',
            'how are things going',
            'what\'s my progress',
            'what am i missing',
            'anything urgent',
            'what needs attention'
        ]
        if any(pattern in message_lower for pattern in open_ended_patterns):
            return UserIntent.OPEN_ENDED

        # Status check patterns (need comprehensive view) - moved before vendor search
        status_patterns = [
            'how is', 'how am i doing', 'where do i stand', 'what\'s left',
            'progress', 'planning going', 'status', 'overview', 'summary'
        ]
        if any(pattern in message_lower for pattern in status_patterns):
            return UserIntent.STATUS_CHECK

        # Task-related keywords (more specific for actions) - moved before vendor search
        task_phrases = ['mark as complete', 'mark the', 'update task', 'complete the', 'finish task']
        task_keywords = [
            'mark', 'complete', 'done', 'finish', 'check off', 'update status'
        ]
        if any(phrase in message_lower for phrase in task_phrases) or any(word in message_lower for word in task_keywords):
            return UserIntent.TASK_MANAGEMENT

        # Ritual-related keywords - moved before vendor search
        ritual_keywords = [
            'ritual', 'tradition', 'ceremony', 'custom', 'culture',
            'religious', 'hindu', 'sanskrit', 'puja'
        ]
        if any(word in message_lower for word in ritual_keywords):
            return UserIntent.RITUAL_INQUIRY        # Vendor-related keywords
        vendor_keywords = [
            'vendor', 'photographer', 'caterer', 'venue', 'book', 'shortlist',
            'decorator', 'florist', 'dj', 'band', 'makeup', 'mehendi'
        ]
        if any(word in message_lower for word in vendor_keywords):
            return UserIntent.VENDOR_SEARCH
        
        # Budget-related keywords (more specific)
        budget_phrases = ['budget for', 'how much', 'spent so far', 'cost of', 'money for', 'expense tracking']
        budget_keywords = [
            'budget', 'cost', 'expense', 'payment', 'money', 'price',
            'spend', 'afford', 'expensive', 'cheap', 'financial'
        ]
        if any(phrase in message_lower for phrase in budget_phrases) or any(word in message_lower for word in budget_keywords):
            return UserIntent.BUDGET_MANAGEMENT
        
        # Timeline-related keywords (more specific)
        timeline_phrases = ['next deadline', 'this week', 'what should i do this week', 'upcoming tasks', 'due date']
        timeline_keywords = [
            'deadline', 'timeline', 'schedule', 'when', 'date',
            'time', 'due', 'urgent', 'overdue'
        ]
        if any(phrase in message_lower for phrase in timeline_phrases) or any(word in message_lower for word in timeline_keywords):
            return UserIntent.TIMELINE_PLANNING
        
        # Task-related keywords (more specific for actions)
        task_phrases = ['mark as complete', 'mark the', 'update task', 'complete the', 'finish task']
        task_keywords = [
            'mark', 'complete', 'done', 'finish', 'check off', 'update status'
        ]
        if any(phrase in message_lower for phrase in task_phrases) or any(word in message_lower for word in task_keywords):
            return UserIntent.TASK_MANAGEMENT
        
        # Ritual-related keywords (more specific)
        ritual_phrases = ['what hindu rituals', 'wedding customs', 'traditional ceremony', 'pooja items']
        ritual_keywords = [
            'ritual', 'tradition', 'ceremony', 'custom', 'culture',
            'religious', 'hindu', 'sanskrit', 'puja', 'mehendi'
        ]
        if any(phrase in message_lower for phrase in ritual_phrases) or any(word in message_lower for word in ritual_keywords):
            return UserIntent.RITUAL_INQUIRY
        
        # Default to general planning (which uses proactive context)
        return UserIntent.GENERAL_PLANNING
    
    def create_context_request(self, wedding_id: str, user_id: str, user_role: str, 
                             user_message: str = "") -> ContextRequest:
        """
        Create a context request based on user message and requirements
        Enhanced for proactive behavior
        """
        intent = self.infer_user_intent(user_message) if user_message else UserIntent.PROACTIVE_GREETING
        scope = self.intent_to_scope_mapping.get(intent, ContextScope.PROACTIVE)
        
        # For proactive scenarios, we need comprehensive context
        proactive_intents = [
            UserIntent.PROACTIVE_GREETING,
            UserIntent.OPEN_ENDED, 
            UserIntent.STATUS_CHECK,
            UserIntent.GENERAL_PLANNING
        ]
        
        if intent in proactive_intents:
            # Proactive scenarios need full context for intelligent suggestions
            include_budget = True
            include_timeline = True
            scope = ContextScope.PROACTIVE
        else:
            # Specific requests can use focused context
            include_budget = intent in [UserIntent.VENDOR_SEARCH, UserIntent.BUDGET_MANAGEMENT]
            include_timeline = intent in [UserIntent.TIMELINE_PLANNING, UserIntent.TASK_MANAGEMENT]
        
        return ContextRequest(
            wedding_id=wedding_id,
            user_id=user_id,
            user_role=user_role,
            intent=intent,
            scope=scope,
            include_budget=include_budget,
            include_timeline=include_timeline,
            include_pending_actions=True
        )


# Global instance
context_manager = SmartContextManager()
