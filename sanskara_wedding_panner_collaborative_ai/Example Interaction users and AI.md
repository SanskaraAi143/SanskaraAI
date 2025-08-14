
Of course. This is the perfect way to visualize how all the components—agents, workflows, data, and user experience—come together. Let's narrate the complete journey of our couple, **Priya (Bride)** and **Rohan (Groom)**, as they plan their wedding with your AI assistant.
This story will illustrate the state flow, agent interactions, and data updates at each critical stage.
---
### **Phase 1: Onboarding & The First Spark (12 Months Out)**
**1. Priya's First Interaction:**
*   **User Action:** Priya signs up on SanskaraAI.com.
*   **AI Interaction (Onboarding):** The **Orchestrator Agent** initiates the "First Consultation" workflow. It asks Priya the onboarding questions: her and Rohan's names/emails, the city (Bangalore), estimated guest count (300 total, 150 from her side), and her family's background (Maharashtrian). She assigns "Venue & Decor" and "Catering" to her side, "Entertainment" to Rohan's side, and "Photography" as a Joint Effort. Her side's budget is ~20 Lakhs.
*   **Data Updates:**
	*   `users`: New records for Priya.
	*   `weddings`: A new record for "Priya & Rohan's Wedding" is created.
	*   `wedding_members`: Priya is linked to the new wedding.
	*   `tasks`: Rows are created for each major task (`Venue Selection`, `Catering`, etc.), with the `lead_party` column set according to Priya's answers. Status for all is `'not_started'`.
*   **Agent Flow:**
	*   The **Orchestrator** sends an invite email to Rohan via the **Communication Agent**.
*   **State Flow:** The system state is now `wedding_created`, `bride_onboarded`, `partner_pending`.
**2. Rohan's Onboarding:**
*   **User Action:** Rohan clicks the invite link and completes his separate, streamlined onboarding. He confirms his side's guest count (150) and that his family is Punjabi. He confirms the task assignments.
*   **Data Updates:**
	*   `users`: New record for Rohan.
	*   `wedding_members`: Rohan is linked to the same wedding ID as Priya.
*   **State Flow:** The system state becomes `planning_active`.
---
### **Phase 2: The First Big Task - Venue Selection (11 Months Out)**
**1. Starting the Search:**
*   **User Action:** Priya logs in and says, "Let's find the wedding venue."
*   **Context Management:** The **Orchestrator Agent** queries the `tasks` table for their `wedding_id`. It sees the `Venue Selection` task is assigned to `bride_side`. Its internal context is primed: "User Priya is initiating the venue search, which she is leading. Criteria: Bangalore, ~300 guests, Maharashtrian-friendly."
*   **Agent Flow:**
	*   The **Orchestrator** calls the **Vendor Management Agent** with these criteria.
	*   The **Vendor Agent** queries the `vendors` table in Supabase and returns a list of 10 suitable venues.
	*   The **Orchestrator** presents these to Priya in a user-friendly format.
*   **Priya's Actions:** After some back and forth, Priya shortlists 3 venues: "The Grand Palace," "Royal Gardens," and "Lakeside Manor."
*   **Data Updates:**
	*   `user_shortlisted_vendors`: Three new rows are created linking Priya's `user_id` to these three vendor IDs.
**2. The "Lead and Review" Collaborative Step:**
*   **User Action:** Priya clicks the **"Share Shortlist for Rohan's Feedback"** button.
*   **Data Updates:** The `tasks` table row for "Venue Selection" has its `status` updated to `'pending_review'`.
*   **Agent Flow:** The **Orchestrator** triggers the **Communication Agent** to send Rohan a notification: _"Hi Rohan, Priya has shortlisted 3 venues for your review. Please take a look!"_
*   **Rohan's Feedback:** Rohan logs in, views the three options, and leaves a comment on "Lakeside Manor": _"This looks great, but my uncle mentioned it has tough parking. Let's prioritize the other two."_
*   **Data Updates:** A new row is added to the `task_feedback` table with Rohan's comment.
*   **Priya's Proposal:** Seeing the feedback, Priya proposes "The Grand Palace" as the final choice. The task `status` becomes `'pending_final_approval'`.
*   **Rohan's Consensus:** Rohan gets a final notification and clicks **"Approve & Finalize."**
*   **Data Updates & State Flow:**
	*   The `tasks` table `status` is set to `'completed'`.
	*   A new row is created in the **`bookings`** table, linking the `wedding_id` and the `vendor_id` for "The Grand Palace."
	*   The system's permanent state now knows the venue is booked. It will not suggest searching for venues again.
---
### **Phase 3: Parallel Work & Proactive AI (9 Months Out)**
**1. Handling Multiple Threads:**
*   **User Action:** While the venue is being finalized, Rohan logs in and says, "Let's figure out the Sangeet entertainment."
*   **Context Management:** The **Orchestrator**, seeing a new request, queries the `tasks` table. It sees "Entertainment" is assigned to `groom_side` and is `not_started`. It starts a new conversational thread with Rohan, calling the **Vendor Management Agent** to find DJs and bands, _without losing the state_ of the ongoing venue decision.
**2. Proactive Assistance (The Magic):**
*   **AI Action (Scheduled Task):** The **Task & Timeline Agent** runs its nightly check. It sees the wedding date is 9 months away and the joint task "Book Photographer" is still `not_started`.
*   **Agent Flow:** It triggers the **Communication Agent**.
*   **AI Interaction:** Both Priya and Rohan receive a notification: _"Friendly reminder: Top wedding photographers in Bangalore get booked up to a year in advance. Shall we start exploring some whose style you might like?"_
**3. Guest Management:**
*   **User Action:** Priya starts adding guests to her side of the list.
*   **Agent Flow:** The **Orchestrator** routes this to the **Guest & Communication Agent**.
*   **Data Updates:** As Priya adds names and contact info, new rows are created in the `guest_list` table with `side = 'bride_side'`. The AI can then use this data to calculate accurate headcounts for the caterer.
---
### **Phase 4: The Home Stretch (1 Month Out)**
**1. Finalizing Details:**
*   **AI Action:** The **Task & Timeline Agent** is now the lead actor. It sees the date is approaching.
*   **AI Interaction:** "Hi Priya & Rohan, your wedding is just a month away! I've used all our booking information to generate a detailed day-of timeline. I've also created separate, simplified versions for each of your key vendors."
*   **Data Updates:** The `timeline_events` table is populated with dozens of entries (e.g., "3:00 PM: Caterer Arrival at The Grand Palace," "6:00 PM: Baraat Assembly").
**2. Vendor & Guest Communication:**
*   **Agent Flow:** The **Orchestrator** directs the **Communication Agent** to:
	*   **Email the vendors:** A professional email is sent to the photographer, caterer, and DJ with their specific call times, venue address, and a contact person's number.
	*   **Send RSVP Reminders:** A polite WhatsApp message is sent to all guests on the `guest_list` whose `status` is still `'Pending'`.
---
### **Phase 5: Post-Wedding & Closing the Loop (1 Week After)**
**1. Final Payments & Reviews:**
*   **AI Action:** The **Task & Timeline Agent** sees the wedding date has passed.
*   **AI Interaction:** "Welcome back, and congratulations! I hope everything was perfect. We just have a few wrap-up items:"
	*   _"A final payment of [Amount] is due to [Caterer Name]. Would you like me to process that?"_
	*   _"You both loved your photographer! Would you like to leave them a review? This helps other couples."_
*   **Data Updates:**
	*   `payments` table is updated.
	*   `reviews` table gets a new entry.
**2. Long-Term Memory & State:**
*   The `workflows` table for the "Priya & Rohan Wedding" now shows almost all workflows as `'completed'`. The entire journey—from the first question to the final thank you note—is permanently stored in a structured, queryable format in Supabase, creating a beautiful digital record of their planning process. The AI's context for them is now complete.
