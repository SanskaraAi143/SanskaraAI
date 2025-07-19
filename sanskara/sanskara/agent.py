from google.adk.agents import Agent
from google.adk.tools import google_search
from .common import SYSTEM_INSTRUCTION, MODEL

class SanskaraAgent(Agent):
    def __init__(self):
        super().__init__(
            name="sanskara_wedding_planner",
            model=MODEL,
            instruction=SYSTEM_INSTRUCTION,
            tools=[google_search],
        )