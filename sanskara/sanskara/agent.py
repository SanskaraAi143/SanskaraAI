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
#from sanskara.sub_agents.creative_agent.agent import creative_agent
#from sanskara.sub_agents.guest_and_communication_agent.agent import guest_and_communication_agent
#from sanskara.sub_agents.task_and_timeline_agent.agent import task_and_timeline_agent


from sanskara.prompt import ORCHESTRATOR_AGENT_PROMPT
from sanskara.tools import (
    get_active_workflows,
    get_tasks_for_wedding,
    update_workflow_status,
    create_workflow,
    update_task_details,
    create_task,
    get_wedding_context, # Added for context priming
    get_task_feedback,   # Added for context priming
    get_task_approvals,  # Added for context priming
    get_complete_wedding_context,  # New optimized function
)
from sanskara.helpers import get_current_datetime # For fetching user and wedding info
from logger import json_logger as logger # Import the custom JSON logger

# Agent Tools
# setup_agent_tool = agent_tool.AgentTool(agent=setup_agent)
vendor_management_agent_tool = agent_tool.AgentTool(agent=vendor_management_agent)
budget_and_expense_agent_tool = agent_tool.AgentTool(agent=budget_and_expense_agent)
ritual_and_cultural_agent_tool = agent_tool.AgentTool(agent=ritual_and_cultural_agent)
#creative_agent_tool = agent_tool.AgentTool(agent=creative_agent)
#guest_and_communication_tool = agent_tool.AgentTool(agent=guest_and_communication_agent)
#task_and_timeline_tool = agent_tool.AgentTool(agent=task_and_timeline_agent)



async def orchestrator_before_agent_callback(
    callback_context: CallbackContext
) -> Optional[LlmResponse]:
    """This function is called before the model is called."""
    wedding_id = callback_context.state.get("current_wedding_id")
    
    with logger.contextualize(
        wedding_id=wedding_id,
        user_id=callback_context.state.get("current_user_id"),
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
                    "current_user_id": callback_context.state.get("user_id"),
                    "current_user_role": "bride"
                }
            )
            return None

        try:
            logger.debug(f"Fetching complete wedding context for wedding_id: {wedding_id}")
            context_data = await get_complete_wedding_context(wedding_id)
            
            if "error" in context_data:
                logger.error(f"Error in fetching wedding context: {context_data['error']}")
                raise Exception(context_data["error"])
            
            wedding_data = context_data["wedding_data"]
            active_workflows = context_data["active_workflows"]
            all_tasks = context_data["all_tasks"]
            
            logger.info(
                f"Successfully gathered all wedding context for wedding {wedding_id} in single query. "
                f"Found {len(active_workflows)} active workflows and {len(all_tasks)} tasks."
            )

            # Store data in session state for the agent to access
            callback_context.state.update(
                {
                    "wedding_data": wedding_data,
                    "active_workflows": active_workflows,
                    "all_tasks": all_tasks,
                    "current_wedding_id": wedding_id,
                    "current_user_id": callback_context.state.get("user_id"),
                    "current_user_role": "bride"
                }
            )

            logger.info(
                f"OrchestratorAgent context primed for wedding {wedding_id}. Context"
                " keys:"
                f" {[k for k in callback_context.state.to_dict().keys() if k.startswith('current_')]}"
            )

        except Exception as e:
            logger.error(
                "Error in orchestrator_before_model_callback for wedding"
                f" {wedding_id}: {e}",
                exc_info=True,
            )
            raise
    return None

orchestrator_agent = LlmAgent(
    name="OrchestratorAgent",
    model="gemini-2.5-flash",
    #model="gemini-2.0-flash-live-001",
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
        create_workflow,
        update_task_details,
        create_task,
        get_current_datetime,
        vendor_management_agent_tool,
        budget_and_expense_agent_tool,
        ritual_and_cultural_agent_tool,
        #creative_agent_tool,
        #guest_and_communication_tool,
        #task_and_timeline_tool,        
    ],
    before_agent_callback= orchestrator_before_agent_callback,
)
root_agent = orchestrator_agent