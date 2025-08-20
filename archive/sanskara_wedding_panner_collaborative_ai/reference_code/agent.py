# main_orchestrator_agent.py - Main Orchestrator for the Sanskara AI application
from google.adk.agents import LlmAgent

from .sub_agents.onboarding import onboarding_agent
from .sub_agents.ritual_search import ritual_search_agent
from .sub_agents.budget import budget_agent
from .sub_agents.vendor_search import vendor_search_agent

# Import tools that the orchestrator itself might use (if any)
# For example, if timeline tools are directly used by the orchestrator
from .tools import create_timeline_event, get_timeline_events, update_timeline_event
from .tools.orchestrator_tools import task_decomposition_tool, state_tracking_tool
# Assuming the orchestrator might need these. If not, this import can be removed.

from .prompt import ORCHESTRATOR_PROMPT # Import the prompt

import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Orchestrator Agent Definition ---

# Note: The sub_agents list will be populated after the sub_agents themselves are defined and imported.
# For now, it will be an empty list or commented out.
root_agent = LlmAgent(
    name="OrchestratorAgent", # Renamed from RootAgent
    model="gemini-2.0-flash-exp-image-generation",
    description="Orchestrates the entire user workflow for Sanskara AI, including onboarding, ritual search, budget management, and vendor search. The user only interacts with this agent.",
    instruction=ORCHESTRATOR_PROMPT,
    sub_agents=[
        onboarding_agent,
        ritual_search_agent,
        budget_agent,
        vendor_search_agent
    ],
    tools=[ # Adding timeline tools as per test implications
        create_timeline_event,
        get_timeline_events,
        update_timeline_event,
        task_decomposition_tool,
        state_tracking_tool
    ],
    output_key="session_preferences",
)

# The old `if __name__ == "__main__":` block will be moved to an example script later.
# Sub-agent definitions (onboarding_agent, ritual_search_agent, etc.) are removed from here.
# Their respective PROMPT variables are also removed.
# Imports specific to sub-agents or their tools (like get_user_id from sanskara.tools) are removed from here.
