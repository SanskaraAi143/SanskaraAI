Of course. This is a critical step for translating a complex architectural design into an actionable development plan.
---
### **Phase 1: Foundation & Backend Setup**
*   **Goal:** Establish the core infrastructure, database schema, and basic server environment.
*   **[x] Task 1: Finalize & Deploy Database Schema**
	- [x] Review and confirm all table structures (`users`, `weddings`, `tasks`, `workflows`, `vendors`, etc.) are finalized.
	- [x] Add any missing columns identified in the design phase (e.g., `lead_party` in `tasks`, more `status` enums).
	- [x] Write and execute the SQL script in your Supabase project to create all tables, indexes, and triggers.
	- [x] Configure Supabase auth and RLS (Row Level Security) policies to ensure users can only access their own wedding data. (PARTIALLY COMPLETED)
*   **[x] Task 2: Setup Backend Server & Google ADK Framework**
	- [x] Initialize a new Python project with FastAPI.
	- [x] Set up a virtual environment and install core dependencies
	- [x] Create environment variable management (`.env`) for Supabase URL/keys, Google Cloud credentials, etc.
	- [x] Implement a basic WebSocket endpoint in FastAPI to connect with the frontend.
	- [x] Create the initial directory structure for the project 
*   **[x] Task 3: Implement Core Database Connection Tools**
	- [x] Create a singleton or dependency-injected Supabase client to be used across the application.
	- [x] Implement a few basic, low-level data access functions . These are not agent tools yet, but helpers.

*   **[x] Task 4: Foundational Testing**
	- [x] **Test:** Write unit tests to confirm direct database connections are working.
	- [x] **Test:** Manually test the WebSocket connection from a simple client to ensure the server is running and accessible.
	- [x] **Test:** Manually insert data into Supabase tables and verify RLS policies are working correctly.
---
### **Phase 2: The Setup & Onboarding Workflow**
*   **Goal:** Implement the critical user onboarding and the automated setup process that prepares the system for the main agent interactions.
*   **[x] Task 5: Implement the Onboarding API Endpoint**
	- [x] Create a REST API endpoint (e.g., `/onboarding/submit`) that the frontend can call when a user completes the onboarding questionnaire.
	- [x] Refactor `submit_onboarding_data` to decompose responsibilities into smaller, focused functions (`_handle_first_partner_submission`, `_handle_second_partner_submission`, `_update_existing_partner_details`).
	- [x] Centralize SQL query construction using `db_queries.py` to separate SQL logic from business logic.
	- [x] This endpoint should handle data validation and store the raw onboarding JSON temporarily. - when both partners have submitted their data , use weddings table details jsonb column to store the onboarding data.
	- [x] Once both partners have submitted their data, it should trigger the `SetupAgent`.
*   **[x] Task 6: Implement the `SetupAgent` and its Tools**
	- [x] Create the `SetupAgent` class.
	- [x] Implement the master tool: `commit_and_activate_plan(onboarding_data)`.
	- [x] Implement the sub-functions used by the master tool:
		- [x] `bulk_create_workflows` (creates entries in the `workflows` table).
		- [x] `bulk_create_tasks_from_template` (the complex logic to generate tasks based on cultural background).
		- [x] `set_task_deadlines` (calculates due dates based on wedding date).
		- [x] `populate_initial_budget`.
*   **[x] Task 7: Orchestrate the Onboarding Flow**
	- [x] Wire the `/onboarding/submit` endpoint to trigger the `SetupAgent` _only_ after the second partner has submitted their data.
	- [x] Ensure the entire `SetupAgent` run is wrapped in a database transaction.
*   **[x] Task 8: Onboarding & Setup Testing**
	- [x] **Test:** Create mock onboarding JSON data for different cultural pairings (e.g., Maharashtrian/Punjabi, South Indian/Gujarati).
	- [x] **Test:** Write unit tests for the `SetupAgent`. For a given input, does it produce the expected number of tasks and workflows? Are the deadlines calculated correctly?
	- [x] **Test (End-to-End):** Call the API endpoint with mock data and verify in the Supabase dashboard that all tables (`workflows`, `tasks`, `budget_items`) are populated correctly and the wedding `status` is set to `'active'`.
---
### **Phase 3: The Orchestrator & The First Key Agent**
*   **Goal:** Bring the main conversational agent online and empower it with its first critical capability: vendor management.
*   **[ ] Task 9: Implement the `OrchestratorAgent`**
	- [ ] Plan on the OrchestratorAgent logic , prompt , tools to use check the docs in sanskara_wedding_panner_collaborative_ai for overall architecture and agent funtionality
	- [ ] Create the agent `OrchestratorAgent`  within the ADK framework - use referece_code/agent.py as reference code structure for agents but dont use the same code as it is different design.
	- [ ] Implement its core logic for session management and context priming (querying `workflows` and `tasks` on startup).
	- [ ] Connect the Orchestrator to the main WebSocket endpoint .
	- [ ] Test the Orchestrator's ability to handle basic messages and return a response.
*   **[ ] Task 10: Implement the `VendorManagementAgent`**
	- [ ] Create the `VendorManagementAgent` class. It will be treated as a "Smart Tool" by the Orchestrator.
	- [ ] Implement its core tools as Python functions:
		- [ ] `search_vendors()`
		- [ ] `get_vendor_details()`
		- [ ] `add_to_shortlist()`
		- [ ] `create_booking()`
*   **[ ] Task 11: Integrate Agents**
	- [ ] Within the Orchestrator's setup, register the `VendorManagementAgent` as an available tool.
	- [ ] Develop the logic for the Orchestrator's LLM to recognize when to call the `vendor_management_tool`.
*   **[ ] Task 12: Vendor Workflow Testing**
	- [ ] **Test (Unit):** Write unit tests for each vendor tool (e.g., does `search_vendors` return the correct format?).
	- [ ] **Test (Integration):** Create a test script that directly invokes the `OrchestratorAgent`. Send it a message like "Find me a photographer" and assert that it correctly calls the `VendorManagementAgent`'s tool.
	- [ ] **Test (E2E):** Connect via the WebSocket and have a full conversation about finding, shortlisting, and booking a vendor. Verify every database update in Supabase.
---
### **Phase 4: Expanding Capabilities & The Collaborative Loop**
*   **Goal:** Implement the remaining agents and the critical "Lead and Review" collaboration workflow.
*   **[ ] Task 13: Implement the `TaskAndTimelineAgent` & its Tools**
	- [ ] Create the agent class.
	- [ ] Implement its tools: `get_tasks`, `update_task_status`, `submit_task_feedback`, `approve_task_final_choice`. This is the backbone of collaboration.
*   **[ ] Task 14: Implement the `GuestAndCommunicationAgent` & its Tools**
	- [ ] Create the agent class.
	- [ ] Implement internal tools: `add_guest`, `update_guest_rsvp`.
	- [ ] **(Complex Sub-task):** Integrate with an external service like Twilio for WhatsApp. Implement `send_whatsapp_message`. This involves handling API keys, templates, and error handling.
*   **[ ] Task 15: Implement Remaining Specialist Agents**
	- [ ] Implement `BudgetAndExpenseAgent` and its tools (`add_expense`, `get_budget_summary`).
	- [ ] Implement `RitualAndCulturalAgent` and its `get_ritual_information` tool (this may require setting up a separate vector DB).
*   **[ ] Task 16: Build the "Lead and Review" Logic**
	- [ ] Enhance the `OrchestratorAgent`'s logic to guide users through the collaborative flow. It must know how to prompt a user to "Share for Review" and how to present feedback to the other party.
	- [ ] This involves complex state management using the `tasks` table's status (`'pending_review'`, `'pending_final_approval'`).
*   **[ ] Task 17: Collaboration & Multi-Agent Testing**
	- [ ] **Test (Unit):** Test all new tools for the remaining agents.
	- [ ] **Test (Integration):** Create a test script that directly invokes the `OrchestratorAgent`. Send it a message like "Find me a photographer" and assert that it correctly calls the `VendorManagementAgent`'s tool.
	- [ ] **Test (E2E):** Connect via the WebSocket and have a full conversation about finding, shortlisting, and booking a vendor. Verify every database update in Supabase.
### **Phase 5: Deployment, Monitoring & Final Polish**
*   **Goal:** Deploy the system, ensure it's robust, and add final touches.
*   **[ ] Task 18: Containerize the Application**
	- [ ] Write a `Dockerfile` for the FastAPI application.
	- [ ] Use Docker Compose to manage the server and any local dependencies (like Redis for caching).
*   **[ ] Task 19: Deploy to a Cloud Service**
	- [ ] Choose a cloud provider (e.g., Google Cloud Run, AWS App Runner).
	- [ ] Set up CI/CD pipelines to automate deployment from your Git repository.
*   **[ ] Task 20: Implement Logging & Monitoring**
	- [ ] Integrate a structured logging library (e.g., `loguru`).
	- [ ] Set up monitoring dashboards (e.g., in Google Cloud) to track API latency, error rates, and agent performance. This is crucial for long-term reliability.
*   **[ ] Task 21: Full System Acceptance Testing**
	- [ ] **Test:** Conduct a full, manual run-through of the entire wedding planning process from the perspective of two new users.
	- [ ] **Test:** Perform basic load testing to see how the system handles multiple concurrent users.
	- [ ] **Test:** Review all user-facing text generated by the LLM for tone, clarity, and helpfulness. Refine prompts as needed.