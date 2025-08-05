from google.adk.agents import LlmAgent
from google.adk.planners.plan_re_act_planner import PlanReActPlanner
from google.genai import types
from logger import json_logger as logger # Import the custom JSON logger

from sanskara.sub_agents.vendor_management_agent.prompt import VENDOR_MANAGEMENT_AGENT_PROMPT
from sanskara.sub_agents.vendor_management_agent.tools import (
    search_vendors,
    get_vendor_details,
    add_to_shortlist,
    create_booking,
    submit_review
)
from sanskara.sub_agents.google_search_agent.agent import google_search_agent,google_search
from google.adk.tools import agent_tool

# make google agent as tool

google_search_agent_tool = agent_tool.AgentTool(agent=google_search_agent)

vendor_management_agent = LlmAgent(
    name="VendorManagementAgent",
    model="gemini-2.5-flash",
    #planner=PlanReActPlanner(),
    #model="gemini-2.0-flash-live-001",
    description="Agent responsible for managing vendor interactions, searching, shortlisting, booking, and reviewing vendors.",
    instruction=VENDOR_MANAGEMENT_AGENT_PROMPT,
    tools=[
        google_search
        #google_search_agent_tool,  # Google Search Tool for vendor-related queries
        # search_vendors,
        # get_vendor_details,
        # add_to_shortlist,
        # create_booking,
        # submit_review
    ],
)
logger.info("VendorManagementAgent initialized.")