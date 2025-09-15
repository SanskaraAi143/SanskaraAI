import json
import re
from typing import Optional, Dict, Any, List
from google.adk.agents import LlmAgent
from google.adk.models import LlmResponse, LlmRequest
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import agent_tool
import os
from google.genai import types
from google.adk.planners.plan_re_act_planner import PlanReActPlanner
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
    get_active_workflows,
    get_tasks_for_wedding,
    update_workflow_status,
    update_task_details,
    # Removed legacy context readers: get_wedding_context, get_tasks_for_wedding,
    # get_task_feedback, get_task_approvals, get_complete_wedding_context
    upsert_workflow,
    upsert_task,
    add_task_feedback,
    get_complete_wedding_context,
    set_task_approval,
    load_artifact_content,
    # resolve_artifacts,  # deprecated
    list_user_artifacts,
    list_user_files_py,
)
# Use the new stateful Context Manager V2 (composes baseline context + workflows)
from sanskara.context_manager_v2 import ContextManagerV2
# Removed context_debugger import (legacy)
from sanskara.helpers import get_current_datetime, execute_supabase_sql # For fetching user and wedding info and executing sql
import logging # Import the custom JSON logger
from sanskara.exceptions import WeddingNotActiveError

# New imports for structured context and semantic recall
from sanskara.context_models import OrchestratorContext, OrchestratorMeta, SemanticMemory
from sanskara.semantic_recall import semantic_search_facts
from sanskara.db_queries import get_chat_sessions_by_wedding_id_query
from sanskara.db_queries import (
    get_latest_chat_session_id_by_wedding_id_query,
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


async def parse_and_load_images_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """Parse [FILES: ...] references in the latest user message and inline matching image artifacts.

    - Looks for patterns like [FILES: file1.png, file2.jpg] or [FILE: name.jpeg].
    - Loads artifacts via callback_context.load_artifact and injects them as parts before model call.
    - Cleans the user text by removing the [FILES: ...] markers to avoid confusing the model.
    - Returns None to proceed with modified request; or a short LlmResponse on hard error.
    """
    logging.info("Parsing and loading images from user message")
    try:
        if not llm_request or not getattr(llm_request, "contents", None):
            return None

        # Find the last user content
        user_content = None
        user_index = None
        for i, content in enumerate(reversed(llm_request.contents)):
            if getattr(content, "role", None) == "user":
                user_content = content
                user_index = len(llm_request.contents) - 1 - i
                break

        if user_content is None or not getattr(user_content, "parts", None):
            return None

        first_part = user_content.parts[0] if user_content.parts else None
        user_text = getattr(first_part, "text", "") or ""
        if not user_text:
            return None

        # Match [FILES: ...] or [FILE: ...]
        matches = re.findall(r"\\\[(FILES?|files?):\s*([^\\]+)\\]", user_text)
        if not matches:
            return None

        # Collect filenames across all matches; split on comma or semicolon
        filenames: List[str] = []
        for _label, inner in matches:
            parts = re.split(r"[,;]", inner)
            filenames.extend([p.strip() for p in parts if p and p.strip()])

        if not filenames:
            return None

        # Load artifacts and keep image-like ones
        image_parts: List[Any] = []
        for fname in filenames:
            try:
                art = await callback_context.load_artifact(filename=fname)
            except Exception as e:
                logging.debug(f"before_model: load_artifact failed for {fname}: {e}")
                continue
            # Expecting an object with inline_data {mime_type, data}
            inline = getattr(art, "inline_data", None)
            mime = getattr(inline, "mime_type", None) if inline else None
            if mime and isinstance(mime, str) and mime.lower().startswith("image/"):
                image_parts.append(art)
                logging.info({
                    "event": "before_model:add_image_part",
                    "filename": fname,
                    "mime_type": mime,
                })

        if not image_parts:
            return None

        # Clean the text by removing all [FILES: ...] segments
        cleaned_text = re.sub(r"\\\[(FILES?|files?):\s*[^\\]+\\]", "", user_text).strip()

        # Rebuild user parts: cleaned text (if any) + images
        new_parts: List[types.Part] = []
        if cleaned_text:
            new_parts.append(types.Part(text=cleaned_text))
        new_parts.extend(image_parts)  # artifacts are already types.Part-compatible

        updated_user = types.Content(role="user", parts=new_parts)
        contents_copy = list(llm_request.contents)
        contents_copy[user_index] = updated_user
        llm_request.contents = contents_copy

        logging.info({
            "event": "before_model:enhanced_with_images",
            "count": len(image_parts),
            "filenames": filenames,
        })
        return None
    except Exception as e:
        logging.error(f"before_model: parse_and_load_images_callback error: {e}", exc_info=True)
        # Fail open: proceed with normal request
        return None


async def orchestrator_before_agent_callback(
    callback_context: CallbackContext
) -> Optional[LlmResponse]:
    """This function is called before the model is called.
    Artifact listing removed per request; artifacts will be accessed on-demand via tools only.
    """
    wedding_id = callback_context.state.get("current_wedding_id")
    user_id = callback_context.state.get("current_user_id")
    
    logging.info({
        "event": "orchestrator_before_agent_callback:start",
        "wedding_id": wedding_id,
        "user_id": user_id,
        "agent_name": "OrchestratorAgent",
    })
    logging.debug(
        "Entering orchestrator_before_agent_callback with state:"\
        f"user content {callback_context.user_content}"
    )

    if not wedding_id:
        logging.warning(
            "No wedding_id found in session state. Cannot prime"\
            " OrchestratorAgent context."
        )
        callback_context.state.update(
            {
                "wedding_data": None,
                "active_workflows": None,
                "all_tasks": None,
                "current_wedding_id": None,
                "current_user_id": user_id,
                "current_user_role": "bride",
                # Keep placeholder so prompt variable exists but do NOT pre-populate
                "recent_artifacts": [],
            }
        )
        return None

    try:
            # Get user role (fix the hardcoded issue)
            user_role = await _get_user_role(wedding_id, user_id)
            
            # Extract user message (for memory/semantic recall; no intent routing)
            user_message = ""
            if (
                callback_context.user_content
                and hasattr(callback_context.user_content, 'parts')
                and callback_context.user_content.parts
            ):
                user_message = callback_context.user_content.parts[0].text or ""

            # Build Context V2: baseline + durable workflow state + collaboration view
            ctx_manager = ContextManagerV2()
            context_data = await ctx_manager.build_context(
                wedding_id=wedding_id,
                user_id=user_id,
                user_role=user_role,
                user_message=user_message,
            )

            # Token guard: cap list sizes to keep prompt compact
            try:
                caps = {
                    "active_workflows": 10,
                    "relevant_tasks": 25,
                    "all_tasks": 50,
                    "shortlisted_vendors": 10,
                    "recent_expenses": 10,
                    "upcoming_events": 10,
                    "overdue_tasks": 10,
                    "urgent_tasks": 10,
                    "priority_items": 10,
                    "recent_activity": 10,
                    "progress_by_category": 10,
                    "budget_insights": 10,
                    "suggested_next_actions": 5,
                    "upcoming_deadlines": 5,
                    "calendar_events": 20,
                }
                for k, max_len in caps.items():
                    if isinstance(context_data.get(k), list) and len(context_data[k]) > max_len:
                        context_data[k] = context_data[k][:max_len]
            except Exception as e:
                logging.warning(f"Token guard capping failed: {e}")
            
            # Ensure prompt-referenced keys exist with safe defaults (artifact list intentionally empty)
            # Baseline context already includes safe defaults
            
            # Enrich with lightweight conversation memory
            conversation_summary: Optional[str] = None
            recent_messages: List[Dict[str, Any]] = []
            try:
                # Load the latest session summary for this wedding (most recent first)
                sql = get_chat_sessions_by_wedding_id_query(wedding_id)
                from sanskara.helpers import execute_supabase_sql  # local import to avoid circulars
                sessions_resp = await execute_supabase_sql(sql)
                if sessions_resp.get("status") == "success" and sessions_resp.get("data"):
                    latest = sessions_resp["data"][0]
                    raw_summary = latest.get("summary")
                    if isinstance(raw_summary, dict):
                        import json as _json
                        conversation_summary = _json.dumps(raw_summary)
                    elif isinstance(raw_summary, str):
                        conversation_summary = raw_summary
                    else:
                        conversation_summary = None

                    # Load last K recent messages for this session
                    latest_session_id = latest.get("session_id")
                    if latest_session_id:
                        try:
                            callback_context.state["db_chat_session_id"] = latest_session_id
                        except Exception:
                            pass
                        k_turns = 6
                        msgs_sql = get_recent_chat_messages_by_session_query(latest_session_id, limit=k_turns * 2)
                        msgs_resp = await execute_supabase_sql(msgs_sql)
                        if msgs_resp.get("status") == "success" and msgs_resp.get("data"):
                            rows = list(reversed(msgs_resp["data"]))
                            recent_messages = [
                                {
                                    "role": r.get("role"),
                                    "content": r.get("content"),
                                    "created_at": r.get("created_at"),
                                }
                                for r in rows
                            ]
                else:
                    # No prior sessions; create one now for continuity across the turn
                    try:
                        create_sql = create_chat_session_query(wedding_id=wedding_id, summary=None)
                        create_resp = await execute_supabase_sql(create_sql)
                        if create_resp.get("status") == "success" and create_resp.get("data"):
                            new_session_id = create_resp["data"][0].get("session_id")
                            if new_session_id:
                                try:
                                    callback_context.state["db_chat_session_id"] = new_session_id
                                except Exception:
                                    pass
                    except Exception as _e:
                        logging.debug(f"Failed to create initial chat session: {_e}")
            except Exception as mem_err:
                logging.warning(f"Conversation summary load failed: {mem_err}")
                conversation_summary = None
            
            context_data["conversation_summary"] = conversation_summary or ""
            context_data["recent_messages"] = recent_messages or []

            # Semantic recall using Supabase memory
            semantic = await semantic_search_facts(
                wedding_id=wedding_id,
                session_id=None,
                query=user_message or "",
                top_k=5,
            )
            
            # Build structured orchestrator context
            try:
                meta = OrchestratorMeta(
                    intent=None,
                    scope="context_v2",
                    k_turns=6,
                    top_k=5,
                    context_version="v2",
                )
                structured_ctx = OrchestratorContext(
                    **context_data,
                    semantic_memory=SemanticMemory(
                        facts=semantic.get("facts", []),
                        sources=semantic.get("sources", []),
                    ),
                    meta=meta,
                )
                callback_context.state["orchestrator_context"] = structured_ctx.to_state()
            except Exception as build_err:
                logging.warning(f"Failed to build OrchestratorContext: {build_err}")
            
            try:
                callback_context.state["semantic_memory"] = {
                    "facts": semantic.get("facts", []),
                    "sources": semantic.get("sources", []),
                }
            except Exception:
                pass
            
            wedding_status = await _get_wedding_status(wedding_id)
            if wedding_status != "active":
                logging.warning(f"Wedding {wedding_id} is not active (status: {wedding_status}). Raising WeddingNotActiveError.")
                raise WeddingNotActiveError(
                    f"Your wedding planning setup is currently in '{wedding_status}' status. "
                    "Please complete the onboarding process before I can fully assist you. "
                    "I'll be ready to help once your wedding status is 'active'!"
                )

            logging.info(
                f"Successfully assembled baseline context for wedding {wedding_id}. "
                f"Context keys: {list(context_data.keys())}"
            )

            callback_context.state.update(context_data)

            logging.info(
                f"OrchestratorAgent baseline context primed for wedding {wedding_id}. "
                f"Final context keys: {list(context_data.keys())}"
            )

    except Exception as e:
        logging.error(
            "Error in orchestrator_before_agent_callback for wedding"\
            f" {wedding_id}: {e}",
            exc_info=True,
        )
        raise
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
        logging.warning(f"after_callback: failed to extract user text: {e}")
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
        logging.error(f"after_callback: failed to ensure chat session: {e}", exc_info=True)
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
        #         logging.debug(f"after_callback: add_text_to_memory failed: {e}")

    except Exception as e:
        logging.error(f"after_callback: failed to insert chat message: {e}", exc_info=True)
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
        logging.warning(f"after_callback: rolling summary failed: {e}")

    # Refresh workflows in session state so {workflows} stays current for next turn
    try:
        fresh_workflows = await get_active_workflows(wedding_id)
        if isinstance(fresh_workflows, list):
            try:
                callback_context.state["active_workflows"] = fresh_workflows
            except Exception:
                pass
            try:
                # Keep the unified alias in sync for prompt placeholder {workflows}
                callback_context.state["workflows"] = fresh_workflows
            except Exception:
                pass
    except Exception as e:
        logging.debug(f"after_callback: workflow refresh failed: {e}")

    return None

# Lightweight output sanitizer (optional): collapse odd splits like "K ashi" -> "Kashi".
def _sanitize_text(text: str) -> str:
    try:
        if not text:
            return text
        # Collapse multiple spaces
        t = " ".join(text.split())
        # Fix common ritual-word splits heuristically
        fixes = {
            "K ashi": "Kashi",
            "Sn anam": "Snanam",
            "Pend likoothuru": "Pendlikoothuru",
            "T alambralu": "Talambralu",
            "Mangal asutram": "Mangalsutram",
        }
        for k, v in fixes.items():
            t = t.replace(k, v)
        return t
    except Exception:
        return text


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
    
    result = await execute_supabase_sql(sql, {"wedding_id": wedding_id, "user_id": user_id})
    
    if result.get("status") == "success" and result.get("data"):
        return result["data"][0].get("user_role", "member")
    
    return "member"  # Default fallback

async def _get_wedding_status(wedding_id: str) -> str:
    """Get the status of the wedding from the database."""
    sql = """
        SELECT status FROM weddings WHERE wedding_id = :wedding_id;
    """
    params = {"wedding_id": wedding_id}
    result = await execute_supabase_sql(sql, params)

    if result.get("status") == "success" and result.get("data"):
        return result["data"][0].get("status", "unknown")
    
    logging.warning(f"Wedding {wedding_id} not found or error occurred during status check. Result: {result}")
    return "not_found" # Or appropriate default/error status

orchestrator_agent = LlmAgent(
    name="OrchestratorAgent",
    #model="gemini-2.5-flash",
    model="gemini-2.0-flash-live-001",
    description="Orchestrates the entire user workflow for Sanskara AI, including onboarding, ritual search, budget management, and vendor search. The user only interacts with this agent.",
    instruction=ORCHESTRATOR_AGENT_PROMPT,
    planner=PlanReActPlanner(),
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
        get_active_workflows,
        get_tasks_for_wedding,
        update_workflow_status,
        update_task_details,
        get_current_datetime,
        upsert_workflow,
        upsert_task,
        add_task_feedback,
        get_complete_wedding_context,
        set_task_approval,
        vendor_management_agent_tool,
        budget_and_expense_agent_tool,
        ritual_and_cultural_agent_tool,
        creative_agent_tool,
        task_and_timeline_tool,
        load_artifact_content,
        list_user_artifacts,
        list_user_files_py,
    ],
    before_model_callback=parse_and_load_images_callback,
    before_agent_callback= orchestrator_before_agent_callback,
    after_agent_callback= orchestrator_after_agent_callback,
)
root_agent = orchestrator_agent
