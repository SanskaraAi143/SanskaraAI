import json
import logging
from typing import Optional, Dict, Any, List
from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool
import os
from google.adk.models import LlmResponse, LlmRequest
from .sub_agents.setup_agent.agent import setup_agent
from .sub_agents.vendor_management_agent.agent import vendor_management_agent
import agentops
# Import other specialized agents as they are implemented
# from .sub_agents.task_and_timeline_agent.agent import task_and_timeline_agent
# from .sub_agents.guest_and_communication_agent.agent import guest_and_communication_agent
# from .sub_agents.budget_and_expense_agent.agent import budget_and_expense_agent
# from .sub_agents.ritual_and_cultural_agent.agent import ritual_and_cultural_agent
# from .sub_agents.creative_agent.agent import creative_agent
# from .sub_agents.collaboration_consensus_agent.agent import collaboration_consensus_agent

from .prompt import ROOT_AGENT_PROMPT
from .tools import (
    get_active_workflows,
    get_tasks_for_wedding,
    update_workflow_status,
    create_workflow,
    update_task_details,
    create_task,
)
from .helpers import execute_supabase_sql # For fetching user and wedding info

setup_agent_tool = agent_tool.AgentTool(agent=setup_agent)
vendor_management_agent_tool = agent_tool.AgentTool(agent=vendor_management_agent)
# Initialize other specialized agent tools as they are implemented
# task_and_timeline_agent_tool = agent_tool.AgentTool(agent=task_and_timeline_agent)
# guest_and_communication_agent_tool = agent_tool.AgentTool(agent=guest_and_communication_agent)
# budget_and_expense_agent_tool = agent_tool.AgentTool(agent=budget_and_expense_agent)
# ritual_and_cultural_agent_tool = agent_tool.AgentTool(agent=ritual_and_cultural_agent)
# creative_agent_tool = agent_tool.AgentTool(agent=creative_agent)
# collaboration_consensus_agent_tool = agent_tool.AgentTool(agent=collaboration_consensus_agent)
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")
agentops.init(
    api_key=AGENTOPS_API_KEY,
    default_tags=['google adk']
)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

root_agent = LlmAgent(
    name="RootAgent",
    #model="gemini-2.0-flash-live-001",
    model="gemini-2.5-flash",
    description="Orchestrates the entire wedding planning workflow, delegates to specialized agents, and manages conversational context.",
    instruction=ROOT_AGENT_PROMPT,
    sub_agents=[], # RootAgent will use other agents as tools, not as sub_agents in the ADK sense
    tools=[
        # Direct tools for RootAgent (e.g., for database interactions at a high level)
        get_active_workflows,
        get_tasks_for_wedding,
        update_workflow_status,
        create_workflow,
        update_task_details,
        create_task,

        # Specialized Agents wrapped as AgentTools
        #setup_agent_tool,
        vendor_management_agent_tool,
        # task_and_timeline_agent_tool,
        # guest_and_communication_agent_tool,
        # budget_and_expense_agent_tool,
        # ritual_and_cultural_agent_tool,
        # creative_agent_tool,
        # collaboration_consensus_agent_tool,
    ],
    output_key="root_response" # Key for the output of this agent
)