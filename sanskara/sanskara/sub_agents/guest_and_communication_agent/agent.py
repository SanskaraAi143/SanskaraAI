# TODO: Implement email and WhatsApp response handling based on sanskara/sub_agents/guest_and_communication_agent/email_whatsapp_handling_plan.md

from google.adk.agents import LlmAgent
from sanskara.sub_agents.guest_and_communication_agent.tools import (
    add_guest,
    update_guest_rsvp,
    send_email,
    send_whatsapp_message,
)
from sanskara.sub_agents.guest_and_communication_agent.prompt import (
    GUEST_AND_COMMUNICATION_AGENT_PROMPT,
)
import logging # Import the custom JSON logger


guest_and_communication_agent = LlmAgent(
    name="GuestAndCommunicationAgent",
    model="gemini-2.5-flash",
    description="Manages guest lists and communication for the wedding. Can add guests, update RSVP status, send emails, and send WhatsApp messages.",
    instruction=GUEST_AND_COMMUNICATION_AGENT_PROMPT,
    include_contents='none',
    tools=[
        add_guest,
        update_guest_rsvp,
        send_email,
        send_whatsapp_message,
    ],
)
logging.info("GuestAndCommunicationAgent initialized.")