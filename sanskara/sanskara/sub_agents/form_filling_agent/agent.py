from google.adk.agents import LlmAgent
from google.adk.planners.plan_re_act_planner import PlanReActPlanner
from sanskara.sub_agents.form_filling_agent.tools import generate_onboarding_json_output
from typing import Dict, Any, Literal

FORM_FILLING_PROMPT_VENDOR = """
You are a form-filling assistant for vendor onboarding. Your task is to collect initial information from the user
by asking a series of questions. Ask one question at a time and wait for the user's response.
Once all the initial information is collected, use the 'generate_onboarding_json_output' tool to provide the collected data as JSON.

Here are the initial questions you need to ask for a vendor:

1. Business & Contact Information
   * What is the legal name of your business?
   * Who is our primary point of contact? (Name, Email, Phone Number)
   * What is your business address?

2. Service Details
* What types of services do you offer? (e.g., Priest services, catering, venue rental, photography)
* Can you provide a short description of your business for your public profile?
* What cities or regions do you operate in? (Your service area)

3. Pricing & Logistics
* What is your basic pricing structure? (e.g., per hour, per event, package deals)
* Do you have a portfolio or website we can link to? (URL to website, social media, etc.)


Start by introducing yourself and asking the first question.
"""

FORM_FILLING_PROMPT_STAFF = """
You are a form-filling assistant for staff onboarding. Your task is to collect initial information from the user
by asking a series of questions. Ask one question at a time and wait for the user's response.
Once all the initial information is collected, use the 'generate_onboarding_json_output' tool to provide the collected data as JSON.

Here are the initial questions you need to ask for staff:

1. Personal & Role Information
   * What is your full name?
   * What is your primary role or specialization? (e.g., Photographer, Caterer, Decorator)
   * Could you provide a title for your professional portfolio?
   * Please give a brief description of your portfolio or your work experience.

Start by introducing yourself and asking the first question.
"""

def get_form_filling_agent(user_type: Literal["vendor", "staff"]) -> LlmAgent:
    """
    Returns a configured LlmAgent instance based on the user type.
    """
    agent_instruction = ""
    if user_type == "vendor":
        agent_instruction = FORM_FILLING_PROMPT_VENDOR
    elif user_type == "staff":
        agent_instruction = FORM_FILLING_PROMPT_STAFF
    else:
        # Default to vendor prompt or raise an error for unknown user type
        agent_instruction = FORM_FILLING_PROMPT_VENDOR
        # raise ValueError(f"Unknown user type: {user_type}")

    return LlmAgent(
        name="FormFillingAgent",
        model="gemini-2.0-flash-live-001",
        #model="gemini-2.5-flash-preview-native-audio-dialog", # Uncomment if using preview audio model
        description="An agent that fills a form by asking a series of questions.",
        instruction=agent_instruction,
        #planner=PlanReActPlanner(), # Uncomment if using a planner
        tools=[generate_onboarding_json_output],
    )