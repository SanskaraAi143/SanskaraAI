from google.adk.agents import LlmAgent
from google.adk.planners.plan_re_act_planner import PlanReActPlanner
from google.genai import types
import logging # Import the custom JSON logger

from sanskara.sub_agents.ritual_and_cultural_agent.prompt import RITUAL_AND_CULTURAL_AGENT_PROMPT
from sanskara.sub_agents.ritual_and_cultural_agent.tools import (
    get_ritual_information
)
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool

# TODO data_management_plan.md need to implement a feedback loop for hindu , wedding ritual data 
ritual_and_cultural_agent = LlmAgent(
    name="RitualAndCulturalAgent",
    model="gemini-2.5-flash",
    description="Agent responsible for providing information and guidance related to wedding rituals, traditions, and cultural aspects.",
    instruction=RITUAL_AND_CULTURAL_AGENT_PROMPT,
    include_contents='none',
    tools=[
        get_ritual_information,
        google_search
    ],
)
logging.info("RitualAndCulturalAgent initialized.")