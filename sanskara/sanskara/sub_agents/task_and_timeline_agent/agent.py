from google.adk.agents import LlmAgent
from sanskara.sub_agents.task_and_timeline_agent.tools import (
    get_tasks,
    update_task_status,
    submit_task_feedback,
    approve_task_final_choice,
    create_timeline_event,
)
from sanskara.sub_agents.task_and_timeline_agent.prompt import (
    TASK_AND_TIMELINE_AGENT_PROMPT,
)
import logging # Import the custom JSON logger


task_and_timeline_agent = LlmAgent(
    name="TaskAndTimelineAgent",
    model="gemini-2.5-flash",
    description="Manages wedding tasks and timeline events. Can fetch tasks, update their status, record feedback, handle approvals, and create timeline events.",
    instruction=TASK_AND_TIMELINE_AGENT_PROMPT,
    include_contents='none',
    tools=[
        get_tasks,
        update_task_status,
        submit_task_feedback,
        approve_task_final_choice,
        create_timeline_event,
    ],
)
logging.info("TaskAndTimelineAgent initialized.")