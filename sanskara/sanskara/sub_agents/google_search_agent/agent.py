from google.adk.agents import LlmAgent
from google.adk.planners.plan_re_act_planner import PlanReActPlanner
from google.genai import types
from sanskara.sub_agents.google_search_agent.prompt import GOOGLE_SEARCH_AGENT_PROMPT
import logging # Import the custom JSON logger

# This is google search tool agent which gets context from google search 
from google.adk.tools import google_search
google_search_agent = LlmAgent(
    name="GoogleSearchAgent",
    model="gemini-2.5-flash",
    planner=PlanReActPlanner(),
    #model="gemini-2.0-flash-live-001",
    description="Agent responsible for performing Google searches to gather information.",
    instruction=GOOGLE_SEARCH_AGENT_PROMPT,
    tools=[
        google_search,  # Google Search Tool for vendor-related queries
       
    ],
)
logging.info("GoogleSearchAgent initialized.")