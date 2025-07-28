from google.adk.agents import LlmAgent
from google.adk.planners.plan_re_act_planner import PlanReActPlanner
from google.genai import types

from .prompt import SETUP_AGENT_PROMPT
from .tools import get_current_datetime, bulk_create_workflows, bulk_create_tasks, populate_initial_budget,setup_agent_before_agent_callback


setup_agent = LlmAgent(
    name="SetupAgent",
    model="gemini-2.5-flash",
    description="Agent responsible for initializing a new wedding plan, including generating workflows, tasks, and budget items based on onboarding data.",
    instruction=SETUP_AGENT_PROMPT,
    tools=[
        get_current_datetime,
        bulk_create_workflows,
        bulk_create_tasks,
        populate_initial_budget
    ],
    before_model_callback=setup_agent_before_agent_callback
)