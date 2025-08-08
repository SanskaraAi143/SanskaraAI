from google.adk.agents import LlmAgent
from google.adk.planners.plan_re_act_planner import PlanReActPlanner
from google.genai import types
from logger import json_logger as logger # Import the custom JSON logger

from sanskara.sub_agents.creative_agent.prompt import CREATIVE_AGENT_PROMPT
from sanskara.sub_agents.creative_agent.tools import (
    add_item_to_mood_board,
    generate_and_add_to_mood_board,
    upload_and_add_to_mood_board,  # keep available for programmatic use
    upload_and_add_to_mood_board_b64,  # ADK-exposed variant without bytes param
    get_mood_board_items
)
from sanskara.sub_agents.creative_agent.image_generation_tools import (
    generate_image_with_gemini,
    edit_image_with_gemini,
    create_mood_board_collage
)

creative_agent = LlmAgent(
    name="CreativeAgent",
    model="gemini-2.5-flash",
    description="Agent responsible for assisting users with creative aspects of wedding planning, including image generation, mood boards, and creative ideas.",
    instruction=CREATIVE_AGENT_PROMPT,
    tools=[
        add_item_to_mood_board,
        generate_and_add_to_mood_board,
        # Use the b64 wrapper to satisfy ADK function-calling schema
        upload_and_add_to_mood_board_b64,
        get_mood_board_items,
        generate_image_with_gemini,
        edit_image_with_gemini,
        create_mood_board_collage
    ],
)
logger.info("CreativeAgent initialized with image generation capabilities.")