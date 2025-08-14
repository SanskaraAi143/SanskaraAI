import json
from typing import Optional, Dict, Any, List
from google.adk.agents import LlmAgent
from google.adk.models import LlmResponse, LlmRequest
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import agent_tool
import os
from google.genai import types
import agentops

from sanskara.sub_agents.setup_agent.agent import setup_agent
from sanskara.sub_agents.vendor_management_agent.agent import vendor_management_agent
from sanskara.sub_agents.budget_and_expense_agent.agent import budget_and_expense_agent
from sanskara.sub_agents.ritual_and_cultural_agent.agent import ritual_and_cultural_agent
from sanskara.sub_agents.creative_agent.agent import creative_agent
#from sanskara.sub_agents.guest_and_communication_agent.agent import guest_and_communication_agent
from sanskara.sub_agents.task_and_timeline_agent.agent import task_and_timeline_agent

#from google.adk.plugins.logging_plugin import LoggingPlugin
from sanskara.prompt import ORCHESTRATOR_AGENT_PROMPT
from sanskara.tools import (
    update_workflow_status,
    update_task_details,
    upsert_workflow,
    upsert_task,
    load_artifact_content,
    list_user_artifacts,
    list_user_files_py,
    get_wedding_details,
    get_budget_summary,
    get_upcoming_deadlines,
    get_overdue_tasks,
    get_shortlisted_vendors,
    get_task_and_workflow_summary,
    get_active_wedding_for_user,
)
from sanskara.helpers import get_current_datetime # For fetching user and wedding info
from logger import json_logger as logger # Import the custom JSON logger

# New imports for structured context and semantic recall
from sanskara.context_models import SemanticMemory
from sanskara.semantic_recall import semantic_search_facts
from sanskara.db_queries import get_chat_sessions_by_wedding_id_query
from sanskara.db_queries import (
    get_recent_chat_messages_by_session_query,
    create_chat_message_query,
    create_chat_session_query,
    update_chat_session_last_updated_at_query,
    update_chat_session_summary_query,
)

# Agent Tools
# setup_agent_tool = agent_tool.AgentTool(agent=setup_agent)
vendor_management_agent_tool = agent_tool.AgentTool(agent=vendor_management_agent)
budget_and_expense_agent_tool = agent_tool.AgentTool(agent=budget_and_expense_agent)
ritual_and_cultural_agent_tool = agent_tool.AgentTool(agent=ritual_and_cultural_agent)
creative_agent_tool = agent_tool.AgentTool(agent=creative_agent)
#guest_and_communication_tool = agent_tool.AgentTool(agent=guest_and_communication_agent)
task_and_timeline_tool = agent_tool.AgentTool(agent=task_and_timeline_agent)



async def orchestrator_before_agent_callback(
    callback_context: CallbackContext
) -> Optional[LlmResponse]:
    """
    This function is called before the model is called.
    It performs essential setup and lightweight context priming.
    """
    wedding_id = callback_context.state.get("current_wedding_id")
    user_id = callback_context.state.get("current_user_id")

    with logger.contextualize(
        wedding_id=wedding_id,
        user_id=user_id,
        agent_name="OrchestratorAgent",
    ):
        logger.debug(
            "Entering orchestrator_before_agent_callback with user content: "
            f"{callback_context.user_content}"
        )

        if not wedding_id:
            logger.warning("No wedding_id in session state. Cannot prime context.")
            callback_context.state.update(
                {
                    "current_wedding_id": None,
                    "current_user_id": user_id,
                    "current_user_role": "guest",
                    "conversation_summary": "",
                    "recent_messages": [],
                    "semantic_memory": {},
                    "task_summary": {},
                    "budget_summary": {},
                }
            )
            return None

        try:
            # 1. Get User Role
            user_role = await _get_user_role(wedding_id, user_id)
            callback_context.state["current_user_role"] = user_role
            
            # 2. Lightweight Context Loading
            from sanskara.tools import get_task_and_workflow_summary, get_budget_summary

            task_summary = await get_task_and_workflow_summary(wedding_id)
            budget_summary = await get_budget_summary(wedding_id)

            callback_context.state["task_summary"] = task_summary
            callback_context.state["budget_summary"] = budget_summary

            logger.info(
                "Loaded lightweight context: "
                f"Tasks: {task_summary.get('total_tasks', 'N/A')}, "
                f"Budget: {budget_summary.get('total_budget', 'N/A')}"
            )

            # 3. Enrich with Conversation Memory
            conversation_summary, recent_messages = await _get_conversation_memory(
                wedding_id, callback_context
            )
            callback_context.state["conversation_summary"] = conversation_summary
            callback_context.state["recent_messages"] = recent_messages

            # 4. Enrich with Semantic Memory
            user_message = ""
            if (callback_context.user_content and
                hasattr(callback_context.user_content, 'parts') and
                callback_context.user_content.parts):
                user_message = callback_context.user_content.parts[0].text or ""

            semantic_memory = await semantic_search_facts(
                wedding_id=wedding_id,
                query=user_message,
                top_k=5,
            )
            callback_context.state["semantic_memory"] = {
                "facts": semantic_memory.get("facts", []),
                "sources": semantic_memory.get("sources", []),
            }
            
            logger.info(
                f"OrchestratorAgent context primed for wedding {wedding_id}. "
                f"User Role: {user_role}."
            )

        except Exception as e:
            logger.error(
                f"Error in orchestrator_before_agent_callback for wedding {wedding_id}: {e}",
                exc_info=True,
            )
    return None


async def orchestrator_after_agent_callback(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """Persist the user turn into chat_messages and touch chat_sessions."""
    wedding_id = callback_context.state.get("current_wedding_id")
    user_id = callback_context.state.get("current_user_id")
    if not wedding_id:
        return None

    # Extract user message text (if any)
    user_text = ""
    try:
        if (
            callback_context.user_content
            and hasattr(callback_context.user_content, "parts")
            and callback_context.user_content.parts
        ):
            first_part = callback_context.user_content.parts[0]
            user_text = getattr(first_part, "text", "") or ""
    except Exception as e:
        logger.warning(f"after_callback: failed to extract user text: {e}")
        user_text = ""

    # Skip if there's nothing to persist
    if not user_text:
        return None

    from sanskara.helpers import execute_supabase_sql

    # Ensure a chat session exists (use most recent or create one)
    session_id: Optional[str] = None
    try:
        sessions_sql = get_chat_sessions_by_wedding_id_query(wedding_id)
        sessions_resp = await execute_supabase_sql(sessions_sql)
        if sessions_resp.get("status") == "success" and sessions_resp.get("data"):
            session_id = sessions_resp["data"][0].get("session_id")
        if not session_id:
            # create new session
            create_sql = create_chat_session_query(wedding_id=wedding_id, summary=None)
            create_resp = await execute_supabase_sql(create_sql)
            if create_resp.get("status") == "success" and create_resp.get("data"):
                session_id = create_resp["data"][0].get("session_id")
    except Exception as e:
        logger.error(f"after_callback: failed to ensure chat session: {e}", exc_info=True)
        return None

    if not session_id:
        return None

    # Expose DB chat session id in session state for downstream consumers (e.g., websocket service)
    try:
        callback_context.state["db_chat_session_id"] = session_id
    except Exception:
        pass

    # Build metadata for the message (intent/scope if available)
    metadata: Dict[str, Any] = {}
    try:
        orch_ctx = callback_context.state.get("orchestrator_context") or {}
        meta = orch_ctx.get("meta") or {}
        if meta:
            metadata["intent"] = meta.get("intent")
            metadata["scope"] = meta.get("scope")
            metadata["k_turns"] = meta.get("k_turns")
            metadata["top_k"] = meta.get("top_k")
    except Exception:
        pass

    # Insert the user message
    try:
        insert_sql = create_chat_message_query(
            session_id=session_id,
            sender_type="user",
            text=user_text,
            sender_name="user",
            metadata=metadata or None,
        )
        insert_resp = await execute_supabase_sql(insert_sql)
        await execute_supabase_sql(update_chat_session_last_updated_at_query(session_id))

        # (Removed) Per-turn semantic memory embedding per new strategy: only store end-of-session summary embedding
        # Leaving the old code commented for reference. If needed, re-enable behind a feature flag.
        # try:
        #     if os.getenv("DISABLE_SEMANTIC_RECALL", "0") not in ("1", "true", "True"):
        #         from sanskara.sanskara.memory.supabase_memory_service import SupabaseMemoryService  # type: ignore
        #     else:
        #         SupabaseMemoryService = None  # type: ignore
        # except Exception:
        #     try:
        #         from sanskara.memory.supabase_memory_service import SupabaseMemoryService  # type: ignore
        #     except Exception:
        #         SupabaseMemoryService = None  # type: ignore
        # if SupabaseMemoryService is not None:
        #     try:
        #         svc = SupabaseMemoryService()
        #         db_msg_id = None
        #         if insert_resp.get("status") == "success" and insert_resp.get("data"):
        #             db_msg_id = insert_resp["data"][0].get("message_id")
        #         await svc.add_text_to_memory(
        #             app_name=os.getenv("SANSKARA_APP_NAME", "sanskara"),
        #             user_id=wedding_id,
        #             text=user_text,
        #             metadata={"session_id": session_id, "message_id": db_msg_id, **(metadata or {})},
        #         )
        #     except Exception as e:
        #         logger.debug(f"after_callback: add_text_to_memory failed: {e}")

    except Exception as e:
        logger.error(f"after_callback: failed to insert chat message: {e}", exc_info=True)
        return None

    # Rolling summary every N turns (user messages only for now)
    try:
        turn_count = int(callback_context.state.get("turn_count") or 0) + 1
        callback_context.state["turn_count"] = turn_count
        SUMMARY_EVERY = 6
        if turn_count % SUMMARY_EVERY == 0:
            # Pull last 12 messages for compression
            msgs_sql = get_recent_chat_messages_by_session_query(session_id, limit=12)
            msgs_resp = await execute_supabase_sql(msgs_sql)
            messages = msgs_resp.get("data") if msgs_resp.get("status") == "success" else []
            # Simple compact summary: collapse user/assistant lines into bullets and trim length
            def _compact(text: str, max_len: int = 180) -> str:
                if not text:
                    return ""
                t = text.strip().replace("\n", " ")
                return (t[: max_len - 1] + "…") if len(t) > max_len else t
            bullets = []
            for r in reversed(messages or []):  # chronological
                role = r.get("role", "user")
                content = r.get("content", "")
                if not content:
                    continue
                prefix = "U:" if role == "user" else "A:"
                bullets.append(f"{prefix} {_compact(content)}")
            summary_text = " | ".join(bullets[-8:])  # keep last 8 lines compact
            summary_payload = {"rolling_summary": summary_text}
            await execute_supabase_sql(update_chat_session_summary_query(session_id, summary_payload))
    except Exception as e:
        logger.warning(f"after_callback: rolling summary failed: {e}")

    return None


async def _get_user_role(wedding_id: str, user_id: str) -> str:
    """Get the actual user role from database instead of hardcoding"""
    sql = """
    SELECT 
        CASE 
            WHEN wm.role IS NOT NULL THEN wm.role
            WHEN u.email = (w.details->>'bride_email') THEN 'bride'
            WHEN u.email = (w.details->>'groom_email') THEN 'groom'
            ELSE 'member'
        END as user_role
    FROM weddings w
    LEFT JOIN users u ON u.user_id = :user_id
    LEFT JOIN wedding_members wm ON wm.wedding_id = w.wedding_id AND wm.user_id = :user_id
    WHERE w.wedding_id = :wedding_id;
    """
    
    from sanskara.helpers import execute_supabase_sql
    result = await execute_supabase_sql(sql, {"wedding_id": wedding_id, "user_id": user_id})
    
    if result.get("status") == "success" and result.get("data"):
        return result["data"][0].get("user_role", "member")
    
    return "member"  # Default fallback

orchestrator_agent = LlmAgent(
    name="OrchestratorAgent",
    #model="gemini-2.5-flash",
    model="gemini-2.0-flash-live-001",
    description="Orchestrates the entire user workflow for Sanskara AI, including onboarding, ritual search, budget management, and vendor search. The user only interacts with this agent.",
    instruction=ORCHESTRATOR_AGENT_PROMPT,
    sub_agents=[
        # setup_agent,
        # vendor_management_agent,
        # budget_and_expense_agent,
        # ritual_and_cultural_agent,
        # creative_agent,
        # guest_and_communication_agent,
        # task_and_timeline_agent,
    ],
    tools=[
        # Core Tools
        update_workflow_status,
        update_task_details,
        upsert_workflow,
        upsert_task,
        get_current_datetime,
        # New Granular Info Tools
        get_wedding_details,
        get_budget_summary,
        get_upcoming_deadlines,
        get_overdue_tasks,
        get_shortlisted_vendors,
        get_task_and_workflow_summary,
        get_active_wedding_for_user,
        # Sub-Agent Tools
        vendor_management_agent_tool,
        budget_and_expense_agent_tool,
        ritual_and_cultural_agent_tool,
        creative_agent_tool,
        task_and_timeline_tool,
        # Artifact Tools
        load_artifact_content,
        list_user_artifacts,
        list_user_files_py,
    ],
    before_agent_callback= orchestrator_before_agent_callback,
    after_agent_callback= orchestrator_after_agent_callback,
)
root_agent = orchestrator_agent