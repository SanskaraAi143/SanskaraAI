from google.adk.agents import LlmAgent
from google.adk.planners.plan_re_act_planner import PlanReActPlanner
from google.genai import types
import logging # Import the custom JSON logger

from sanskara.sub_agents.vendor_management_agent.prompt import VENDOR_MANAGEMENT_AGENT_PROMPT
from sanskara.sub_agents.vendor_management_agent.tools import (
    search_vendors,
    get_vendor_details,
    add_to_shortlist,
    create_booking,
    submit_review
)
from google.adk.tools import google_search
from google.adk.tools import agent_tool

# make google agent as tool

vendor_management_agent = LlmAgent(
    name="VendorManagementAgent",
    model="gemini-2.5-flash",
    #planner=PlanReActPlanner(),
    #model="gemini-2.0-flash-live-001",
    description="Agent responsible for managing vendor interactions, searching, shortlisting, booking, and reviewing vendors.",
    instruction=VENDOR_MANAGEMENT_AGENT_PROMPT,
    include_contents='none',
    tools=[
        google_search
        # search_vendors,
        # get_vendor_details,
        # add_to_shortlist,
        # create_booking,
        # submit_review
    ],
)
logging.info("VendorManagementAgent initialized.")