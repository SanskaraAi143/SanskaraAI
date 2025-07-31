# Sanskara AI - Comprehensive Agent Testing Strategy

This document outlines the testing strategy for the Sanskara AI multi-agent system, building upon the existing test suite and adhering to best practices for robust AI applications using Google ADK. The goal is to ensure the reliability, correctness, and performance of individual components and their interactions.

## 1. Unit Tests for Individual Agent Tools

*   **Purpose:** Verify that the Python functions exposed as tools to agents (e.g., `search_vendors()`, `add_guest()`, `execute_supabase_sql()`) work correctly in isolation. These tests focus on the direct functionality of each tool, including its interactions with external systems (like databases or third-party APIs).
*   **Focus:** Correct input parsing, valid output generation, handling of edge cases, and proper error propagation from external calls.
*   **Methodology:**
    *   Directly call tool functions with various inputs.
    *   Use mocking libraries (e.g., `unittest.mock`) to simulate responses from external services (Supabase, Twilio, etc.) to ensure tests are fast, reliable, and independent of network conditions or external service availability.
    *   Verify database changes using assertions against a mocked or test database client.
*   **Existing Examples:**
    *   [`sanskara/tests/test_budget_agent_tools.py`](sanskara/tests/test_budget_agent_tools.py)
    *   [`sanskara/tests/test_vendor_management_agent_tools.py`](sanskara/tests/test_vendor_management_agent_tools.py)

## 2. Agent Unit Tests (Internal Logic)

*   **Purpose:** Test the internal reasoning and decision-making logic of each specialized agent (e.g., `VendorManagementAgent`, `SetupAgent`, `OrchestratorAgent`) without involving the full LLM inference pipeline or external tool execution. This verifies that the agent correctly interprets prompts and selects/calls its internal tools.
*   **Focus:** Agent's prompt engineering, tool selection logic, and response generation based on mocked tool outputs.
*   **Methodology:**
    *   Instantiate the agent and simulate LLM responses (e.g., by mocking the LLM client or using pre-defined LLM outputs).
    *   Mock the agent's internal tool calls to control their return values, allowing focused testing of how the agent processes these results and generates its own output.
    *   Assert that the agent's `run()` method produces the expected `Event` objects or final `Content`.
*   **Existing Examples:**
    *   [`sanskara/tests/test_budget_agent.py`](sanskara/tests/test_budget_agent.py)
    *   [`sanskara/tests/test_setup_agent_invocation.py`](sanskara/tests/test_setup_agent_invocation.py)

## 3. Orchestrator to Specialized Agent Integration Tests

*   **Purpose:** Verify that the Orchestrator Agent correctly understands complex user intents and effectively delegates tasks to the appropriate specialized agents. This tests the "routing" and communication layer between the Orchestrator and its "smart tools" (the specialized agents).
*   **Focus:** Correct tool invocation by the Orchestrator, proper argument passing, and synthesis of results from specialized agents into a coherent user response.
*   **Methodology:**
    *   Instantiate the Orchestrator Agent.
    *   Mock the specialized agents (or their `run()` methods) that the Orchestrator calls. This ensures that the test focuses on the Orchestrator's delegation logic, rather than the internal workings of the specialized agents.
    *   Simulate user messages to the Orchestrator and assert that the correct specialized agent's `run()` method is called with the expected inputs.
    *   Verify the Orchestrator's final response to the user based on the mocked responses from specialized agents.
*   **Existing Examples:**
    *   [`sanskara/tests/test_orchestrator_agent.py`](sanskara/tests/test_orchestrator_agent.py)
    *   [`sanskara/tests/test_orchestrator_vendor_integration.py`](sanskara/tests/test_orchestrator_vendor_integration.py)

## 4. End-to-End Tests

*   **Purpose:** Validate entire user journeys and system workflows, from the API endpoint to database changes and back. These tests simulate real-world scenarios, ensuring all components work together seamlessly.
*   **Focus:** Overall system functionality, data consistency across the database, and correct handling of multi-step, multi-agent interactions.
*   **Methodology:**
    *   **API-level tests:** Use FastAPI's `TestClient` or `httpx` to send requests to the API endpoints (e.g., `/onboarding/submit`, `/chat`).
    *   **Database assertions:** After simulating actions, query the test database (Supabase or a local equivalent) directly to verify that data has been stored and updated correctly (`weddings`, `tasks`, `workflows`, `chat_messages`, etc.).
    *   **Workflow validation:** Test long-running workflows (e.g., onboarding of both partners, venue selection with feedback and approval) to ensure state transitions and agent triggers occur as expected.
    *   **External service integration tests (optional/staged):** For critical external services (e.g., Twilio for WhatsApp), consider dedicated integration tests in a controlled environment, or use robust mocking for daily builds.
*   **Existing Examples:**
    *   [`sanskara/tests/endpoint_onboard_test.sh`](sanskara/tests/endpoint_onboard_test.sh) (can be converted to Python for better integration with the test suite)
    *   [`sanskara/tests/test_collaboration_integration.py`](sanskara/tests/test_collaboration_integration.py)

## Testing Environment Considerations:

*   **Test Database:** Use a dedicated test database instance (e.g., a separate Supabase project, a local PostgreSQL container, or an in-memory SQLite for simpler tests) to ensure test isolation and prevent interference with development or production data.
*   **Mocking:** Aggressively use mocking for external services (LLMs, Supabase client, Twilio, etc.) to make unit and integration tests fast, deterministic, and independent.
*   **Pytest Fixtures:** Leverage `pytest` fixtures for setting up and tearing down test environments (e.g., creating temporary users, initializing database states).
*   **CI/CD Integration:** Ensure all tests are integrated into the CI/CD pipeline to run automatically on every code change, providing immediate feedback on regressions.

This strategy provides a clear roadmap for ensuring the quality and reliability of the Sanskara AI system across all layers of its multi-agent architecture.