import json
from typing import Optional, Dict, Any, List
from google.adk.agents import LlmAgent
from google.adk.models import LlmResponse, LlmRequest
from google.adk.sessions import Session
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import agent_tool
import os
from google.genai import types
import agentops

from sanskara.sub_agents.setup_agent.agent import setup_agent
from sanskara.sub_agents.vendor_management_agent.agent import vendor_management_agent

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
)
from sanskara.helpers import execute_supabase_sql # For fetching user and wedding info
from logger import json_logger as logger # Import the custom JSON logger

# Agent Tools
# setup_agent_tool = agent_tool.AgentTool(agent=setup_agent)
vendor_management_agent_tool = agent_tool.AgentTool(agent=vendor_management_agent)

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")
agentops.init(
    api_key=AGENTOPS_API_KEY,
    default_tags=['google adk']
)

async def orchestrator_before_model_callback(session: Session, llm_request: LlmRequest) -> None:
    wedding_id = session.state.get("wedding_id")
    current_user_id = session.state.get("user_id")
    current_user_role = session.state.get("user_user_role")

    with logger.contextualize(wedding_id=wedding_id, user_id=current_user_id, agent_name="OrchestratorAgent"):
        logger.debug(f"Entering orchestrator_before_model_callback. Request: {llm_request.contents[0].parts[0].text[:100]}...")

        if not wedding_id:
            logger.warning("No wedding_id found in session state. Cannot prime OrchestratorAgent context.")
            return

        try:
            logger.debug(f"Fetching wedding context for wedding_id: {wedding_id}")
            wedding_data = await get_wedding_context(wedding_id)
            logger.debug(f"Fetched wedding data. Active workflows for wedding_id: {wedding_id}")
            active_workflows = await get_active_workflows(wedding_id)
            logger.debug(f"Fetched active workflows. All tasks for wedding_id: {wedding_id}")
            all_tasks = await get_tasks_for_wedding(wedding_id)
            logger.debug(f"Fetched all tasks for wedding_id: {wedding_id}")

            tasks_with_feedback_and_approvals = []
            for task in all_tasks:
                task_id = task.get("task_id")
                if task_id:
                    logger.debug(f"Fetching feedback and approvals for task_id: {task_id}")
                    feedback = await get_task_feedback(task_id)
                    approvals = await get_task_approvals(task_id)
                    task["feedback"] = feedback
                    task["approvals"] = approvals
                    logger.debug(f"Fetched feedback and approvals for task_id: {task_id}")
                tasks_with_feedback_and_approvals.append(task)
            logger.info(f"Successfully gathered all task details for wedding {wedding_id}.")

            # Store data in session state for the agent to access
            session.state["wedding_data"] = wedding_data
            session.state["active_workflows"] = active_workflows
            session.state["all_tasks"] = tasks_with_feedback_and_approvals

            logger.info(f"OrchestratorAgent context primed for wedding {wedding_id}. Context keys: {[k for k in session.state.keys() if k.startswith('current_')]}")

        except Exception as e:
            logger.error(f"Error in orchestrator_before_model_callback for wedding {wedding_id}: {e}", exc_info=True)
            raise

orchestrator_agent = LlmAgent(
    name="OrchestratorAgent",
    model="gemini-2.5-flash",
    description="Orchestrates the entire user workflow for Sanskara AI, including onboarding, ritual search, budget management, and vendor search. The user only interacts with this agent.",
    instruction=ORCHESTRATOR_AGENT_PROMPT,
    tools=[
        get_active_workflows,
        update_workflow_status,
        create_workflow,
        update_task_details,
        create_task,
        vendor_management_agent_tool,
    ],
    before_model_callback=orchestrator_before_model_callback,
)
root_agent = orchestrator_agent