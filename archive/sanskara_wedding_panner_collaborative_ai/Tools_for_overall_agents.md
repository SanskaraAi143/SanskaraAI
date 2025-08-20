Of course. You've correctly understood the Google ADK paradigm. The framework handles the "routing" and invocation of agents, but the power of those agents comes from the concrete, functional **Tools** they have at their disposal. An agent without tools is just a conversationalist; an agent with the right tools can interact with the world.
Here is a comprehensive list of the tools that would need to be implemented as Python functions. These are the building blocks your specialized agents will use to perform actions, query data, and drive the wedding planning process forward.
---
### **A. Setup Agent Tools**
_(These are used only once per wedding, triggered after onboarding is complete.)_
**1. ****`commit_and_activate_plan(onboarding_data)`**
*   **Description:** A master transactional function that populates the entire initial wedding plan. It internally calls other setup functions. If any part fails, the entire transaction is rolled back.
*   **Primary Agent:** `SetupAgent`
*   **Parameters:** `onboarding_data` (JSON object with all info from both partners).
*   **Returns:** `{ "status": "success" | "failure", "wedding_id": "uuid" }`
*   **Internal Actions:**
	*   Calls `bulk_create_workflows`.
	*   Calls `bulk_create_tasks_from_template`.
	*   Calls `set_task_deadlines`.
	*   Calls `populate_initial_budget`.
	*   Updates the `weddings` table status to `'active'`.
---
### **B. Vendor Management Agent Tools**
**1. ****`search_vendors(category, city, budget_range, style_keywords)`**
*   **Description:** Searches the `vendors` table for suitable vendors. Can use SQL `LIKE` for keywords or even `pgvector` for semantic style matching.
*   **Primary Agent:** `VendorManagementAgent`
*   **Parameters:** `category` (str), `city` (str), `budget_range` (dict), `style_keywords` (list).
*   **Returns:** `[{"vendor_id": "uuid", "name": "str", "rating": "float"}]`

**2. ****`get_vendor_details(vendor_id)`**
*   **Description:** Fetches all details for a specific vendor from the `vendors` table.
*   **Primary Agent:** `VendorManagementAgent`
*   **Parameters:** `vendor_id` (str).
*   **Returns:** A JSON object with all vendor details.

**3. ****`add_to_shortlist(user_id, vendor_id)`**
*   **Description:** Adds a vendor to a user's shortlist in the `user_shortlisted_vendors` table.
*   **Primary Agent:** `VendorManagementAgent`
*   **Parameters:** `user_id` (str), `vendor_id` (str).
*   **Returns:** `{ "status": "success" }`

**4. ****`create_booking(wedding_id, vendor_id, event_date, final_amount)`**
*   **Description:** Creates a formal booking record in the `bookings` table. This is a significant state change.
*   **Primary Agent:** `VendorManagementAgent`
*   **Parameters:** `wedding_id` (str), `vendor_id` (str), `event_date` (str), `final_amount` (float).
*   **Returns:** `{ "booking_id": "uuid" }`

**5. ****`submit_review(booking_id, user_id, rating, comment)`**
*   **Description:** Writes a new review to the `reviews` table.
*   **Primary Agent:** `VendorManagementAgent`
*   **Parameters:** `booking_id` (str), `user_id` (str), `rating` (float), `comment` (str).
*   **Returns:** `{ "review_id": "uuid" }`
---
### **C. Task & Timeline Agent Tools**
**1. ****`get_tasks(wedding_id, filters)`**
*   **Description:** Fetches a list of tasks for a wedding, with optional filters.
*   **Primary Agent:** `TaskAndTimelineAgent`
*   **Parameters:** `wedding_id` (str), `filters` (dict, e.g., `{"status": "pending_review", "lead_party": "bride_side"}`).
*   **Returns:** `[{"task_id": "uuid", "title": "str", "status": "str", "due_date": "str"}]`

**2. ****`update_task_status(task_id, new_status)`**
*   **Description:** Updates the status of a specific task. This is the core of the workflow engine.
*   **Primary Agent:** `TaskAndTimelineAgent`
*   **Parameters:** `task_id` (str), `new_status` (str, e.g., `'pending_review'`, `'completed'`).
*   **Returns:** `{ "status": "success" }`

**3. ****`submit_task_feedback(task_id, user_id, related_entity_id, comment)`**
*   **Description:** Writes feedback for a task (e.g., a comment on a shortlisted vendor) to the `task_feedback` table.
*   **Primary Agent:** `TaskAndTimelineAgent`
*   **Parameters:** `task_id` (str), `user_id` (str), `related_entity_id` (str, e.g., a vendor_id), `comment` (str).
*   **Returns:** `{ "feedback_id": "uuid" }`

**4. ****`approve_task_final_choice(task_id, user_id)`**
*   **Description:** Records a final approval for a task, creating a row in the `task_approvals` table.
*   **Primary Agent:** `TaskAndTimelineAgent`
*   **Parameters:** `task_id` (str), `user_id` (str).
*   **Returns:** `{ "status": "success", "is_fully_approved": true | false }`

**5. ****`create_timeline_event(wedding_id, event_name, event_date_time, location)`**
*   **Description:** Adds a new event to the detailed wedding timeline in the `timeline_events` table.
*   **Primary Agent:** `TaskAndTimelineAgent`
*   **Parameters:** `wedding_id`, `event_name`, `event_date_time`, `location` (all str).
*   **Returns:** `{ "event_id": "uuid" }`
---
### **D. Guest & Communication Agent Tools**

**1. ****`add_guest(wedding_id, guest_name, side, contact_info)`**
*   **Description:** Adds a new guest to the `guest_list` table.
*   **Primary Agent:** `GuestAndCommunicationAgent`
*   **Parameters:** `wedding_id`, `guest_name`, `side` (`'bride_side'` or `'groom_side'`), `contact_info` (all str).
*   **Returns:** `{ "guest_id": "uuid" }`

**2. ****`update_guest_rsvp(guest_id, rsvp_status)`**
*   **Description:** Updates the RSVP status for a specific guest.
*   **Primary Agent:** `GuestAndCommunicationAgent`
*   **Parameters:** `guest_id` (str), `rsvp_status` (str).
*   **Returns:** `{ "status": "success" }`

**3. ****`send_email(recipient_email, subject, body)`**
*   **Description:** An external API tool that interfaces with a service like SendGrid or AWS SES.
*   **Primary Agent:** `GuestAndCommunicationAgent`
*   **Parameters:** `recipient_email`, `subject`, `body` (all str).
*   **Returns:** `{ "status": "sent" | "failed" }`

**4. ****`send_whatsapp_message(phone_number, message_template_id, params)`**
*   **Description:** An external API tool that interfaces with the WhatsApp Business API (e.g., Twilio).
*   **Primary Agent:** `GuestAndCommunicationAgent`
*   **Parameters:** `phone_number` (str), `message_template_id` (str), `params` (list of strings for the template).
*   **Returns:** `{ "status": "sent" | "failed" }`
---
### **E. Budget, Ritual, and Creative Tools**

**1. ****`add_expense(wedding_id, item_name, category, amount, vendor_name)`**
*   **Description:** Adds a new expense line item to the `budget_items` table.
*   **Primary Agent:** `BudgetAndExpenseAgent`
*   **Parameters:** All string/float values.
*   **Returns:** `{ "item_id": "uuid" }`

**2. ****`get_budget_summary(wedding_id)`**
*   **Description:** Queries and aggregates the `budget_items` table to provide a summary by category.
*   **Primary Agent:** `BudgetAndExpenseAgent`
*   **Parameters:** `wedding_id` (str).
*   **Returns:** `[{"category": "str", "spent": "float", "budgeted": "float"}]`

**3. ****`get_ritual_information(query, culture_filter)`**
*   **Description:** A retrieval tool that searches a knowledge base (likely powered by a vector database on top of your ritual data) for information about traditions.
*   **Primary Agent:** `RitualAndCulturalAgent`
*   **Parameters:** `query` (str, e.g., "significance of saptapadi"), `culture_filter` (str, e.g., "Punjabi").
*   **Returns:** A string containing the retrieved information.
**4. ****`add_item_to_mood_board(wedding_id, image_url, note, category)`**
*   **Description:** Adds a new item to the user's mood board.
*   **Primary Agent:** `CreativeAgent`
*   **Parameters:** All string values.
*   **Returns:** `{ "item_id": "uuid" }`
---
### **F. Cross-Agent (System) Tools**

_(Available to multiple agents, especially the Orchestrator.)_
**1. ****`web_search(query)`**
*   **Description:** Interfaces with a search API like Google or Serper to find real-time information.
*   **Parameters:** `query` (str).
*   **Returns:** A string with search results.

**2. ****`calculator(expression)`**
*   **Description:** A simple tool to perform mathematical calculations.
*   **Parameters:** `expression` (str).
*   **Returns:** A number.

**3. ****`get_current_datetime()`**
*   **Description:** Returns the current date and time.
*   **Parameters:** None.
*   **Returns:** A formatted datetime string.
