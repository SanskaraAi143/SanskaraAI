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
    get_active_workflows,
    get_tasks_for_wedding,
    update_workflow_status,
    update_task_details,
    get_wedding_context, # Added for context priming
    get_task_feedback,   # Added for context priming
    get_task_approvals,  # Added for context priming
    get_complete_wedding_context,  # New optimized function
    upsert_workflow, # New tool for creating or updating workflows
    upsert_task, # New tool for creating or updating tasks
)
from sanskara.context_manager import context_manager
from sanskara.context_debugger import context_debugger
from sanskara.context_debugger import context_debugger
from sanskara.helpers import get_current_datetime # For fetching user and wedding info
from logger import json_logger as logger # Import the custom JSON logger

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
    """This function is called before the model is called."""
    wedding_id = callback_context.state.get("current_wedding_id")
    user_id = callback_context.state.get("current_user_id")
    
    with logger.contextualize(
        wedding_id=wedding_id,
        user_id=user_id,
        agent_name="OrchestratorAgent",
    ):
        logger.debug(
            "Entering orchestrator_before_agent_callback with state:"
            f"user content {callback_context.user_content}"
        )

        if not wedding_id:
            logger.warning(
                "No wedding_id found in session state. Cannot prime"
                " OrchestratorAgent context."
            )
            # TODO need to implement a fallback or error handling here
            # set as not implemented for each key
            callback_context.state.update(
                {
                    "wedding_data": None,
                    "active_workflows": None,
                    "all_tasks": None,
                    "current_wedding_id": None,
                    "current_user_id": user_id,
                    "current_user_role": "bride"
                }
            )
            return None

        try:
            # Get user role (fix the hardcoded issue)
            user_role = await _get_user_role(wedding_id, user_id)
            
            # Extract user message for intent detection
            user_message = ""
            if (callback_context.user_content and 
                hasattr(callback_context.user_content, 'parts') and 
                callback_context.user_content.parts):
                user_message = callback_context.user_content.parts[0].text if callback_context.user_content.parts[0].text else ""
            
            # Create smart context request based on user intent
            context_request = context_manager.create_context_request(
                wedding_id=wedding_id,
                user_id=user_id,
                user_role=user_role,
                user_message=user_message
            )
            
            logger.info(f"Smart context request: intent={context_request.intent}, scope={context_request.scope}")
            
            # Get optimized context
            context_data = await context_manager.get_smart_context(context_request)
            
            # Debug context efficiency (optional - can be disabled in production)
            context_debugger.log_context_request(context_request, context_data)
            
            # Check wedding status for Orchestrator activation
            wedding_data = context_data.get("wedding_data", {})
            if wedding_data and wedding_data.get("status") != "active":
                logger.info(f"Wedding {wedding_id} is not active (status: {wedding_data.get('status')}). Orchestrator will not process requests.")
                return LlmResponse(
                    text=f"Your wedding planning setup is currently in '{wedding_data.get('status')}' status. Please complete the onboarding process before I can fully assist you. I'll be ready to help once your wedding status is 'active'!"
                )

            logger.info(
                f"Successfully gathered smart context for wedding {wedding_id}. "
                f"Intent: {context_request.intent}, Scope: {context_request.scope}, "
                f"Context keys: {list(context_data.keys())}"
            )

            # Store data in session state for the agent to access
            callback_context.state.update(context_data)

            logger.info(
                f"OrchestratorAgent smart context primed for wedding {wedding_id}. "
                f"Final context keys: {list(context_data.keys())}"
            )

        except Exception as e:
            logger.error(
                "Error in orchestrator_before_agent_callback for wedding"
                f" {wedding_id}: {e}",
                exc_info=True,
            )
            raise
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
        get_active_workflows,
        update_workflow_status,
        update_task_details,
        get_current_datetime,
        upsert_workflow, # Using the new upsert tool
        upsert_task, # Using the new upsert tool
        vendor_management_agent_tool,
        budget_and_expense_agent_tool,
        ritual_and_cultural_agent_tool,
        creative_agent_tool,
        #guest_and_communication_tool,
        task_and_timeline_tool,
    ],
    before_agent_callback= orchestrator_before_agent_callback,
)
root_agent = orchestrator_agent