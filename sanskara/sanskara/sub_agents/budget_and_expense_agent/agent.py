from google.adk.agents import LlmAgent
from google.adk.planners.plan_re_act_planner import PlanReActPlanner
from google.genai import types
import logging # Import the custom JSON logger
from sanskara.sub_agents.google_search_agent.agent import google_search_agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.code_executors import BuiltInCodeExecutor

# Example Interactions for BudgetAndExpenseAgent:
#
# --- Expense Management ---
#
# User: "Add an expense for flowers, $500, from vendor 'Floral Fantasy'."
# Agent Response: "Expense for flowers of $500 from Floral Fantasy added successfully."
#
# User: "Update the expense for flowers to $550."
# Agent Response: "Expense for flowers updated to $550 successfully."
#
# User: "Delete the expense for 'catering deposit'."
# Agent Response: "Expense 'catering deposit' deleted successfully."
#
# User: "What are my current expenses?"
# Agent Response: "Your current expenses are: Flowers: $550, Catering Deposit: $2000, Venue Rental: $10000."
#
# --- Budget Overview ---
#
# User: "What is my total budget for the wedding?"
# Agent Response: "Your total budget is $30,000. You have spent $12,550 so far, with $17,450 remaining."
#
# --- Tool Demonstrations ---
#
# User: "Calculate 15% of my remaining budget." (Demonstrates `code_execution_tool` for calculations)
# Agent Response: "15% of your remaining budget ($17,450) is $2,617.50."
#
# User: "Find average wedding flower costs in California." (Demonstrates `google_search` for external data)
# Agent Response: "Searching Google for 'average wedding flower costs California'... [Search results summary]"
#
# --- Insights and Optimization Suggestions ---
#
# User: "How can I optimize my wedding budget?"
# Agent Response: "Based on your current spending, you could consider:
# - Reviewing your catering options for more cost-effective menus.
# - Exploring alternative flower arrangements or seasonal blooms.
# - Negotiating with vendors for potential discounts or package deals.
# Would you like me to find some budget-friendly venue options?"
#
# User: "What are the biggest categories of my spending?"
# Agent Response: "Your largest spending categories are Venue Rental ($10,000), followed by Catering ($2,000), and Flowers ($550). These three categories account for a significant portion of your budget."
#
from sanskara.sub_agents.budget_and_expense_agent.prompt import BUDGET_AND_EXPENSE_AGENT_PROMPT
from sanskara.sub_agents.budget_and_expense_agent.tools import (
    get_total_budget,
    update_expense,
    delete_expense,
    get_all_expenses,
    #code_execution_tool,
    upsert_budget_item, # Using the new upsert tool
)
budget_google_search_tool = AgentTool(agent=google_search_agent)

budget_and_expense_agent = LlmAgent(
    name="BudgetAndExpenseAgent",
    model="gemini-2.5-flash",
    description="Agent responsible for managing the wedding budget and tracking expenses.",
    instruction=BUDGET_AND_EXPENSE_AGENT_PROMPT,
    include_contents='none',
    #code_executor=BuiltInCodeExecutor(),
    tools=[
        get_total_budget,
        update_expense,
        delete_expense,
        get_all_expenses,
        #code_execution_tool,
        upsert_budget_item, # Using the new upsert tool
        budget_google_search_tool, # Using the Google Search Agent tool
    ],
)
logging.info("BudgetAndExpenseAgent initialized.")