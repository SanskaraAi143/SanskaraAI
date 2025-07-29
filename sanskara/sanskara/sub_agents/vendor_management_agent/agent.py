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

vendor_management_agent = LlmAgent(
    name="VendorManagementAgent",
    model="gemini-2.5-flash",
    description="Agent responsible for managing vendor interactions, searching, shortlisting, booking, and reviewing vendors.",
    instruction=VENDOR_MANAGEMENT_AGENT_PROMPT,
    tools=[
        search_vendors,
        get_vendor_details,
        add_to_shortlist,
        create_booking,
        submit_review
    ],
)
logger.info("VendorManagementAgent initialized.")