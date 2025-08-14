
It appears you've embarked on an exciting and ambitious project with SanskaraAI. Building a truly comprehensive and reliable AI wedding planner, especially one that navigates the beautiful complexities of Hindu traditions and the delicate dynamics between two families, is a significant undertaking. The provided SQL schema and detailed task list offer a fantastic foundation.
Let's architect a robust AI agent system using Google's Agent Development Kit (ADK) that can bring your vision to life. This design will be optimized for reliability, speed, and intelligent context management, all while addressing the unique challenges of a collaborative wedding planning process.
### **1. Technology Stack**
For the backend, we'll focus on a modern, scalable, and integrated stack. Given your preference for Google ADK, here's a recommended setup:
*   **Framework:** **Google Agent Development Kit (ADK)** will serve as the core for building and orchestrating your multi-agent system. Its design for composing specialized agents is a perfect fit for the varied tasks in wedding planning.
*   **Language:** **Python** is the primary language for Google ADK and the lingua franca of AI development, with extensive libraries for any required task.
*   **AI Models:** **Google's Gemini models (via Vertex AI)** are a natural choice, being tightly integrated with ADK. Their advanced reasoning and multi-modal capabilities will be invaluable.
*   **Database:** **Supabase (PostgreSQL)** is an excellent choice. You're already using it, and its real-time capabilities, authentication, and storage solutions are a great fit. Our agents will interact with it extensively.
*   **Real-time Communication:** **WebSockets** are the right choice for the connection to your front end, enabling a responsive, chat-like experience. The backend framework we choose will handle this.
*   **Backend Server:** A Python web framework like **FastAPI** or **Flask** will expose the WebSocket and REST endpoints for your front end. They are lightweight, high-performance, and integrate well with the AI ecosystem.
*   **Caching:** **Redis** will be crucial for caching frequent database queries (e.g., vendor lists, ritual information) and for managing session state information, which will improve speed and reduce costs.
*   **Task Queue:** For long-running or asynchronous tasks like sending emails or processing images, a message broker like **RabbitMQ** or a simpler solution like **Celery with a Redis broker** will be essential for reliability.
### **2. The Multi-Agent System Architecture with Google ADK**
At the heart of your system will be a hierarchy of specialized AI agents, orchestrated by a central agent. Crucially, the user only ever interacts with one primary interface, which in turn is managed by the orchestrator.
#### **The Orchestrator Agent (The "Maestro")**
The **Orchestrator Agent** is the user-facing brain of the operation. It doesn't perform the tasks itself but intelligently routes requests to the appropriate specialized agent or workflow. It is responsible for:
*   **Maintaining the primary conversation flow.**
*   **Understanding user intent** and decomposing complex requests (e.g., "Find me a Maharashtrian caterer in Bangalore for around 200 people and check their availability for next March").
*   **Delegating tasks** to specialized agents.
*   **Synthesizing information** from multiple agents to provide a coherent response to the user.
*   **Managing conversational context** and switching between different planning threads.
#### **Specialized Agents (The "Expert Team")**
These are non-conversational, tool-using agents that are called by the Orchestrator. They are designed for specific tasks:
*   **Vendor Management Agent:** Handles all interactions with the `vendors`, `user_shortlisted_vendors`, and `vendor_services` tables.
*   **Ritual & Cultural Agent:** Provides information about Hindu wedding traditions, drawing from a knowledge base. Your website already highlights this as a key feature.
*   **Guest & Communication Agent:** Manages the `guest_list` and sends out communications via integrated channels.
*   **Budget & Expense Agent:** Interacts with the `budget_items` and `payments` tables.
*   **Task & Timeline Agent:** Manages the `tasks` and `timeline_events` for both the user and vendors.
*   **Creative Agent:** Assists with `mood_boards` and generating creative ideas.
*   **Collaboration & Consensus Agent:** A crucial addition to facilitate communication and decision-making between the bride and groom's sides.
### **3. Mapping To-Do List to Workflows and Timelines**
Instead of a rigid, linear process, we'll use dynamic, parallel workflows. A "workflow" in this context is a sequence of tasks managed by the Orchestrator, often involving multiple specialized agents.
Here's how the to-do list maps to these workflows, with suggested timelines (from the wedding date):
|To-Do Task Category|Workflow Name|Responsible Agents|Suggested Deadline|
|---|---|---|---|
|**Budget & Financials**|`FinancialPlanningWorkflow`|Budget & Expense Agent|12+ Months Out|
|**Vision & Guest List**|`InitialPlanningWorkflow`|Creative Agent, Guest & Comm. Agent|12+ Months Out|
|**Key Bookings (Venue, Planner)**|`CoreVendorBookingWorkflow`|Vendor Management Agent, Task & Timeline Agent|10-12 Months Out|
|**Photographer, Videographer, Priest**|`KeyPersonnelBookingWorkflow`|Vendor Management Agent, Ritual & Cultural Agent|9-11 Months Out|
|**Attire & Styling**|`StylingAndAttireWorkflow`|Creative Agent, Vendor Management Agent|8-10 Months Out|
|**Caterer, Decorator, Entertainment**|`MajorVendorSelectionWorkflow`|Vendor Management Agent, Budget & Expense Agent|6-9 Months Out|
|**Guest Management & Invitations**|`GuestInvitationWorkflow`|Guest & Communication Agent|3-5 Months Out|
|**Pre-Wedding Rituals & Pooja Items**|`RitualLogisticsWorkflow`|Ritual & Cultural Agent, Task & Timeline Agent|2-4 Months Out|
|**Final Confirmations & Timeline**|`FinalizationWorkflow`|All Agents (coordinated by Orchestrator)|1-2 Months Out|
|**Wedding Week & Day-Of**|`ExecutionWorkflow`|Task & Timeline Agent, Guest & Comm. Agent|The Wedding Week|
|**Post-Wedding Activities**|`PostWeddingWorkflow`|Task & Timeline Agent, Vendor Management Agent|1-3 Months Post-Wedding|
### **4. Handling Parallelism and Asynchronous Operations**
A user won't follow a strict order. They might want to research photographers while still finalizing the guest list. Our system is designed for this:
*   **Parallel Workflows:** The Orchestrator can initiate multiple workflows simultaneously. For instance, the `StylingAndAttireWorkflow` and the `MajorVendorSelectionWorkflow` can run in parallel.
*   **State Management:** The state of each workflow (e.g., 'venue search in progress', 'caterer quotes received') is stored in the Supabase database. This is crucial for long-running processes and for providing status updates to the user.
*   **Notifications:** When a workflow reaches a milestone or a deadline is approaching, the **Task & Timeline Agent** will use the **Guest & Communication Agent** to send notifications via WhatsApp, email, or in-app alerts. This brings the user back into the loop at the right moment.
### **5. Robust Context and Conversation History Management**
This is critical for a good user experience and for keeping LLM costs down.
*   **Session-Based Caching (Short-term Memory):** For the immediate back-and-forth of a conversation, we'll use Redis to store the recent message history. This keeps the conversation fluid.
*   **Database-backed History (Long-term Memory):** Every interaction is saved to the `chat_messages` table, linked to a `chat_sessions`.
*   **Summarization and Retrieval:** To avoid blowing up the context window, we'll use a **Summarization Agent**. After a user completes a sub-task (e.g., shortlisting three decorators), this agent will summarize the interaction (e.g., "User shortlisted decorators A, B, and C based on a rustic theme preference and a budget of X."). This summary, along with the IDs of the shortlisted vendors, is saved. When the user revisits this topic, the Orchestrator will use this summary and retrieve the relevant data, rather than re-injecting the entire chat history. This is a form of Retrieval-Augmented Generation (RAG).
### **6. External Tools and Functions for Agents**
The specialized agents will be equipped with a variety of tools to interact with the outside world and your database.
**Internal Tools (Interacting with Supabase):**
Each agent will have functions to perform CRUD (Create, Read, Update, Delete) operations on the relevant tables. For example, the `VendorManagementAgent` will have:
*   `search_vendors(category, location, budget)`
*   `get_vendor_details(vendor_id)`
*   `add_to_shortlist(user_id, vendor_id)`
*   `update_shortlist_status(user_vendor_id, new_status)`
**External Tools:**
*   **Communication:**
	*   **WhatsApp API:** To send notifications, reminders, and potentially facilitate direct communication with vendors.
	*   **Email (SendGrid/AWS SES):** For more formal communications like sending contracts or summaries.
	*   **(Future) Twilio:** For programmatic voice calls for critical alerts.
*   **Information & Logistics:**
	*   **Google Search API:** For general knowledge and finding information not in your database.
	*   **Google Maps API:** For calculating distances between venues, hotels, and airports.
*   **Productivity:**
	*   **Google Calendar API:** To sync event timelines and booking dates with the user's personal calendar.
	*   **Image Generation (DALL-E 3/Midjourney API):** The Creative Agent can use this to generate mood board concepts.
### **7. Facilitating Bride and Groom Side Collaboration**
This is your unique selling proposition and requires careful design.
**Schema Enhancement:**
We need to associate tasks and decisions with specific "sides" or the couple jointly. Let's add a `responsible_party` column to a few key tables:
*   **`tasks`**** table:** `responsible_party VARCHAR(50) -- 'bride_side', 'groom_side', 'couple'`
*   **`guest_list`**** table:** The existing `side` column is perfect for this.
*   **`budget_items`**** table:** `contribution_by VARCHAR(50) -- 'bride_side', 'groom_side', 'shared'`
**The Collaboration & Consensus Agent:**
This new agent is key. Its functions will include:
*   **Assigning Tasks:** When a new task is created, the Orchestrator can ask the user, "Who will be responsible for this? The bride's side, the groom's side, or both?" The Collaboration agent then updates the `tasks` table accordingly.
*   **Facilitating Discussions:** For contentious decisions (e.g., budget allocation for a specific event), the agent can create a temporary "discussion space." It can present options to both parties, gather their feedback asynchronously, and even suggest compromises based on their stated priorities. For example: _"The bride's side prefers a more elaborate floral arrangement, while the groom's side is focused on the catering budget. Would you consider allocating 10% more to florals if we can find a caterer with a comparable menu for 5% less?"_
*   **Shared Checklists:** The agent can generate and display filtered to-do lists for each side, as well as a common list, ensuring everyone knows their responsibilities.
*   **Consensus Tracking:** For key decisions, the agent can require a "sign-off" from both a designated bride's side member and a groom's side member before marking the task as complete.
By implementing this robust, multi-agent architecture with clear separation of concerns, intelligent state management, and a focus on collaborative tools, SanskaraAI can evolve from a planning tool into an indispensable, AI-powered wedding partner.
