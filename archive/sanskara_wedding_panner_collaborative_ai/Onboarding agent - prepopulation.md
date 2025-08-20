You have asked the perfect question. This is a critical architectural step that separates a prototype from a robust, production-ready system. The Orchestrator is the pilot of the plane, but it cannot build the plane while trying to fly it.
You are absolutely right. A separate, specialized agent must handle the initial setup. We'll call this the **Provisioning Agent**.
### The Provisioning Agent: The "Master Architect"
The **Provisioning Agent** is a non-conversational, backend-only agent. Its sole purpose is to take the raw materials from the onboarding process and construct the entire initial framework of the wedding plan. It runs **once** per wedding, immediately after the _second_ partner completes their onboarding, signifying that all initial data has been collected.
Think of it this way:
*   **The Onboarding Flow** is the client interview where the architect gathers requirements.
*   **The Provisioning Agent** is the architect drawing up the official blueprints (`tasks`), construction phases (`workflows`), and project deadlines (`timeline_events`).
*   **The Orchestrator Agent** is the on-site project manager who uses those blueprints to manage the day-to-day work.
---
### The Trigger: Completion of Onboarding
The Provisioning Agent is triggered by a specific business event: **When the ****`wedding_members`**** table for a given ****`wedding_id`**** contains both a 'bride' and a 'groom'.** This ensures it doesn't run prematurely with only half the information.
### The Tasks Performed by the Provisioning Agent
Here is the step-by-step checklist of what the Provisioning Agent does before the Orchestrator takes over for the first time.
**Step 1: Ingest All Onboarding Data**
*   **Action:** The agent reads all the answers provided by both Priya and Rohan during their separate onboarding sessions.
*   **Input Data:** It queries the database for user profiles, wedding details (city, date, guest count), cultural preferences, and—most importantly—the **task delegation answers** (who is leading Venue, Catering, etc.).
**Step 2: Create Task Instances from Templates**
*   **Action:** This is the core logic. The agent uses a pre-defined `task_templates` table in your database to generate the actual to-do list. It doesn't have tasks hard-coded.
*   **Input Data:** It reads from `task_templates`. Each template might look like this:`{
  "template_name": "Select Wedding Venue",
  "category": "Vendor Booking",
  "default_deadline_offset_months": -10, // 10 months before wedding
  "related_ceremony": "main_wedding"
}
`
*   **Logic:**
	1.  The agent iterates through every template.
	1.  For each template, it checks if the related ceremony is part of the couple's plan (e.g., if there's no "Sangeet" ceremony planned, it skips the "Book Sangeet DJ" task).
	1.  It then uses the **delegation answers** from onboarding to set the `lead_party` column (`'bride_side'`, `'groom_side'`, or `'couple'`).
*   **Database Table Updated:** It performs a bulk insert into the **`tasks`** table, creating 30-50 specific, assigned tasks.
**Step 3: Initialize High-Level Workflows**
*   **Action:** The agent looks at the generated tasks and groups them into logical workflows.
*   **Input Data:** The categorized list of tasks it just created.
*   **Logic:** It creates rows in the `workflows` table to track the state of major planning phases. For example, all tasks in the "Vendor Booking" category will be associated with a `MajorVendorSelectionWorkflow`.
*   **Database Table Updated:** It inserts initial records into the **`workflows`** table, all with a `status` of `'not_started'`.
**Step 4: Populate Key Timeline Milestones**
*   **Action:** It creates the high-level deadlines that will be used for proactive reminders.
*   **Input Data:** The wedding date and the `default_deadline_offset_months` from the `task_templates`.
*   **Logic:** For each critical task, it calculates the deadline (Wedding Date + Offset) and creates an event.
*   **Database Table Updated:** It inserts key events into the **`timeline_events`** table. Examples:
	*   `event_name`: "Deadline: Finalize Venue Selection", `event_date_time`: "[Wedding Date] - 10 months"
	*   `event_name`: "Deadline: Send Out Invitations", `event_date_time`: "[Wedding Date] - 4 months"
**Step 5: The "Welcome & Handover" Notification**
*   **Action:** The user experience requires a clear starting signal. The Provisioning Agent's final job is to tell the couple that their plan is ready.
*   **Logic:** It makes a final tool call to the **Communication Agent**.
*   **Output:** Both Priya and Rohan receive a welcome notification:_"Welcome, Priya and Rohan! Your personalized wedding plan is now ready. We've created your initial to-do list, timeline, and budget framework based on your preferences. You can start by tackling your first task: Venue Selection. I'm here to help whenever you're ready!"_
**Step 6: Setting the Final State for the Orchestrator**
*   **Action:** The agent performs the final "handover."
*   **Database Table Updated:** It can update a field in the main **`weddings`** table, like setting `planning_status` from `'provisioning'` to `'active'`.
*   **State Change:** This is the flag the Orchestrator looks for. The next time Priya or Rohan logs in, the Orchestrator sees the `active` status, queries the now-populated `tasks` and `workflows` tables, and is fully equipped to begin the conversation with complete context.
### Summary: Provisioning Agent vs. Orchestrator
|Aspect|Provisioning Agent|Orchestrator Agent|
|---|---|---|
|**Role**|The Architect|The Project Manager|
|**Trigger**|Onboarding Completion (a one-time event)|User Interaction (anytime, ongoing)|
|**Type**|Non-conversational, Backend Process|Conversational, User-Facing|
|**Core Task**|**Populates** the initial plan framework|**Executes and updates** the plan|
|**Main DB Writes**|Bulk inserts into `tasks`, `workflows`, `timeline_events`|Updates status fields, adds feedback/comments|
|**Output**|A fully structured, ready-to-use wedding plan|A single, helpful response to a user's query|
By separating these concerns, you create a system that is incredibly robust. The Orchestrator's logic is simplified because it can always assume the basic structure of the plan exists, allowing it to focus entirely on its complex job of managing the live, evolving conversation.
