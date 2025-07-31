from google.adk.agents import LlmAgent
from google.adk.planners.plan_re_act_planner import PlanReActPlanner
from google.genai import types
from logger import json_logger as logger # Import the custom JSON logger

from sanskara.sub_agents.ritual_and_cultural_agent.prompt import RITUAL_AND_CULTURAL_AGENT_PROMPT
from sanskara.sub_agents.ritual_and_cultural_agent.tools import (
    get_ritual_information
)
from sanskara.sub_agents.google_search_agent.agent import google_search_agent
from google.adk.tools.agent_tool import AgentTool

ritual_google_search_tool = AgentTool(agent=google_search_agent)
# TODO data_management_plan.md need to implement a feedback loop for hindu , wedding ritual data 
ritual_and_cultural_agent = LlmAgent(
    name="RitualAndCulturalAgent",
    model="gemini-2.5-flash",
    description="Agent responsible for providing information and guidance related to wedding rituals, traditions, and cultural aspects.",
    instruction=RITUAL_AND_CULTURAL_AGENT_PROMPT,
    tools=[
        get_ritual_information,
        ritual_google_search_tool
    ],
)
logger.info("RitualAndCulturalAgent initialized.")