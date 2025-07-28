import asyncio
import json
import os
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from google.adk.tools import ToolContext

# Set up logging for visibility during the test run
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# # Mock the execute_supabase_sql function
# # This prevents actual database calls during the test
# # and allows us to inspect what SQL queries would have been executed.
# @patch('sanskara.sanskara.shared_libraries.helpers.execute_supabase_sql')
# async def mock_execute_supabase_sql(mock_sql_executor, sql: str, params: dict = None):
#     logger.info(f"MOCK DB CALL: SQL: {sql}, Params: {params}")
#     # Simulate a successful database operation
#     return {"status": "success", "data": []}
# Import the SetupAgent
from sanskara.sub_agents.setup_agent.agent import setup_agent
from google.adk.agents import Agent
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig
from google.genai import types

async def run_setup_agent_test(onboarding_data, wedding_id  ):
    # # Mock onboarding data (based on the user's provided JSON)
    # mock_onboarding_data = {
    #     "wedding_id": "e8d96e6b-c08e-4c1e-bfaa-50f1b6f728d1",
    #     "partner_data": {
    #         "fds@gmail.com": {
    #             "name": "fdsa",
    #             "role": "Groom",
    #             "email": "fds@gmail.com",
    #             "ceremonies": ["Pendlikoothuru", "Snathakam", "Kanyadaan", "Jeelakarra-Bellam"],
    #             "priorities": ["Venue & Ambiance", "Food & Catering"],
    #             "budget_range": "8L",
    #             "teamwork_agreement": False,
    #             "cultural_background": "andhra pradesh, rayalaseema, balija"
    #         },
    #         "kpuneeth714@gmail.com": {
    #             "name": "Puneeth Kamatam",
    #             "role": "Bride",
    #             "email": "kpuneeth714@gmail.com",
    #             "phone": "+917674051127",
    #             "ceremonies": [],
    #             "priorities": ["Food & Catering"],
    #             "attire_main": "fsda",
    #             "color_theme": "fds",
    #             "guest_split": "not sure",
    #             "other_style": "",
    #             "attire_other": "fds",
    #             "budget_range": "12L",
    #             "partner_name": "fdsa",
    #             "wedding_city": "fds",
    #             "wedding_date": "2025-09-19", # Crucial for date calculations
    #             "partner_email": "fds@gmail.com",
    #             "teamwork_plan": {
    #                 "catering": "Joint Effort",
    #                 "guest_list": "Joint Effort",
    #                 "venue_decor": "Joint Effort",
    #                 "sangeet_entertainment": "Joint Effort"
    #             },
    #             "wedding_style": "Grand & Traditional",
    #             "guest_estimate": "400",
    #             "budget_flexibility": "Strict",
    #             "cultural_background": "andhra pradesh, rayalaseema (balija)",
    #             "custom_instructions": ""
    #         }
    #     },
    #     "other_partner_email_expected": "fds@gmail.com"
    # }

    # # Extract wedding_id (example - you'd likely have a proper way to get this)
    # # For this test, let's just use a dummy UUID. In a real scenario, this would come from the DB after wedding creation.
    # wedding_id = "e8d96e6b-c08e-4c1e-bfaa-50f1b6f728d1" 

    # Create a mock session service and runner
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="sanskara_wedding_planner",
        user_id="test-user",
        
    )

    runner = Runner(
        app_name="sanskara_wedding_planner",
        agent=setup_agent,
        session_service=session_service,
    )

    # Provide the onboarding data as the user's initial input to the SetupAgent
    # The SetupAgent's prompt will guide it to parse this data and call tools.
    user_message_content = types.Content(
        role="user",
        parts=[types.Part(text=str(json.dumps(onboarding_data)))]
    )

    logger.info("Invoking SetupAgent with mock onboarding data...")

    # Define run_config
    run_config = RunConfig()
    final_response_text = "Agent did not produce a final response." # Default
    async for event in runner.run_async(user_id=session.user_id, session_id=session.id, new_message=user_message_content, run_config=run_config):
      # You can uncomment the line below to see *all* events during execution
      # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

      # Key Concept: is_final_response() marks the concluding message for the turn.
      if event.is_final_response():
          if event.content and event.content.parts:
             # Assuming text response in the first part
             final_response_text = event.content.parts[0].text
          elif event.actions and event.actions.escalate: # Handle potential errors/escalations
             final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
          # Add more checks here if needed (e.g., specific error codes)
          break # Stop processing events once the final response is found

    print(f"<<< Agent Response: {final_response_text}")
    return final_response_text
    # # Use the mock_execute_supabase_sql context manager
    # with patch('sanskara.sanskara.shared_libraries.helpers.execute_supabase_sql', new_callable=AsyncMock) as mock_sql_executor:
    #     mock_sql_executor.return_value = {"status": "success", "data": []} # Default success for mocks

    #     # # Mock the get_current_datetime tool's return value for deterministic tests
    #     # @patch('sanskara.sanskara.sub_agents.setup_agent.tools.get_current_datetime')
    #     # def mock_get_current_datetime_tool(tool_context: ToolContext):
    #     #     return {"current_datetime_utc": datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat()}

    #     # # Temporarily replace the actual tool with our mock
    #     # original_get_current_datetime = setup_agent.tools[0] # Assuming it's the first tool
    #     # setup_agent.tools[0] = mock_get_current_datetime_tool
    #     final_response_text=None
    #     # Run the agent and process events
    #     async for event in runner.run_async(
    #         user_id=session.user_id,
    #         session_id=session.id,
    #         new_message=user_message_content,
    #         run_config=run_config,
    #     ):
    #         # if event.tool_code:
    #         #     logger.info(f"Tool Code Executed: {event.tool_code}")
    #         # if event.text:
    #         #     logger.info(f"Agent Response: {event.text}")
    #         # if event.tool_response:
    #         #     logger.info(f"Tool Response: {event.tool_response}")
            
    #         # Check for final response (as per the provided example)
    #         if event.is_final_response():
    #             if event.content and event.content.parts:
    #                 # Assuming text response in the first part
    #                 final_response_text = event.content.parts[0].text
    #         elif event.actions and event.actions.escalate: # Handle potential errors/escalations
    #             final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
    #             # Add more checks here if needed (e.g., specific error codes)
    #             break # Stop processing events once the final response is found

    #         print(f"<<< Agent Response: {final_response_text}")

 
if __name__ == "__main__":
    asyncio.run(run_setup_agent_test())
