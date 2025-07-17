Of course. Based on our entire conversation, here is a comprehensive and consolidated list of all the schema updates required. These changes are designed to transform your single-user-centric schema into a robust, multi-user, collaborative platform ready to be powered by our multi-agent system.
The core principles behind these updates are:
*   **Introducing the ****`wedding`**** as the Central Object:** Almost all data will now be linked to a single `wedding_id`, allowing multiple users to collaborate on one event.
*   **Enabling Collaboration:** Adding fields like `role`, `lead_party`, and `contribution_by` to track responsibilities between the bride's and groom's side.
*   **Supporting Agent Statefulness:** Creating new tables (`workflows`, `task_feedback`, `task_approvals`) that serve as the long-term memory and state-tracking mechanism for the AI agents.
---
### **Consolidated Schema Updates SQL Script**
Here is the complete script of necessary changes.
```sql
---------------------------------------------------------------------
-- 1. NEW CORE TABLES FOR COLLABORATION & STATE MANAGEMENT
---------------------------------------------------------------------

-- The Wedding Table (The new central object for the entire application)
CREATE TABLE weddings (
    wedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_name VARCHAR(255) NOT NULL, -- e.g., "Priya & Rohan's Wedding"
    wedding_date DATE,
    status VARCHAR(50) NOT NULL DEFAULT 'onboarding_in_progress', -- 'onboarding_in_progress', 'active', 'completed', 'archived'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER set_weddings_updated_at
BEFORE UPDATE ON weddings
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();


-- Wedding Members Table (Links multiple users to a single wedding)
CREATE TABLE wedding_members (
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- e.g., 'bride', 'groom', 'planner', 'bride_family', 'groom_family'
    PRIMARY KEY (wedding_id, user_id) -- Ensures a user has only one role per wedding
);


-- Workflows Table (Long-term memory for high-level agent processes)
CREATE TABLE workflows (
    workflow_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    workflow_name VARCHAR(100) NOT NULL, -- e.g., 'CoreVendorBookingWorkflow', 'GuestInvitationWorkflow'
    status VARCHAR(50) NOT NULL DEFAULT 'not_started', -- 'not_started', 'in_progress', 'paused', 'awaiting_feedback', 'completed', 'failed'
    context_summary JSONB, -- Stores key decisions and IDs to re-prime the agent's context
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_workflows_wedding_id_status ON workflows (wedding_id, status);

CREATE TRIGGER set_workflows_updated_at
BEFORE UPDATE ON workflows
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();


-- Task Feedback Table (Supports the "Lead and Review" model for comments)
CREATE TABLE task_feedback (
    feedback_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    feedback_type VARCHAR(50) NOT NULL, -- e.g., 'comment', 'like', 'dislike'
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_task_feedback_task_id ON task_feedback(task_id);


-- Task Approvals Table (Supports the "Lead and Review" model for final sign-offs)
CREATE TABLE task_approvals (
    approval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    approving_party VARCHAR(50) NOT NULL, -- 'bride_side', 'groom_side', 'couple'
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    approved_by_user_id UUID REFERENCES users(user_id), -- Optional: who clicked the button
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER set_task_approvals_updated_at
BEFORE UPDATE ON task_approvals
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();


---------------------------------------------------------------------
-- 2. MODIFICATIONS TO EXISTING TABLES
---------------------------------------------------------------------

-- ALTER 'tasks' table for collaboration
ALTER TABLE tasks
    DROP COLUMN user_id, -- A task belongs to the wedding, not a single user
    ADD COLUMN wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    ADD COLUMN lead_party VARCHAR(50); -- 'bride_side', 'groom_side', 'couple'
-- Note: You might need to drop the old index on user_id and create a new one on wedding_id
-- The 'status' column should be understood to now include states like 'pending_review' and 'pending_final_approval'.


-- ALTER 'budget_items' table for collaboration
ALTER TABLE budget_items
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    ADD COLUMN contribution_by VARCHAR(50); -- 'bride_side', 'groom_side', 'shared'


-- ALTER 'guest_list' table for collaboration
ALTER TABLE guest_list
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE;
-- The existing 'side' column ('bride', 'groom') already works perfectly for this.


-- ALTER 'mood_boards' table for collaboration
ALTER TABLE mood_boards
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE;


-- ALTER 'timeline_events' table for collaboration
ALTER TABLE timeline_events
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE;


-- ALTER 'chat_sessions' table for collaboration
ALTER TABLE chat_sessions
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE;
-- This allows viewing a combined chat history for the entire wedding plan.


-- ALTER 'user_shortlisted_vendors' to link to the wedding
ALTER TABLE user_shortlisted_vendors
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE;
```
### Summary of Changes and Why They Matter:
1.  **`weddings`**: This is the new parent table for everything. It allows your system to handle thousands of different weddings simultaneously. The `status` field is the master switch that tells the **Setup Agent** when to run and the **Orchestrator** when to start.
1.  **`wedding_members`**: This table is key to the multi-user experience. It defines who is part of the wedding and what their role is, which can be used for permissions and filtering what users see.
1.  **`workflows`**: This is the agent's brain. It's how the Orchestrator remembers the high-level status of major planning activities (like "Vendor Search") over weeks or months.
1.  **`task_feedback`**** & ****`task_approvals`**: These two tables are the explicit implementation of the **"Lead and Review"** model. They provide the structure needed for one side to propose options and the other side to comment and formally approve them, preventing miscommunication.
1.  **`ALTER TABLE ... DROP COLUMN user_id`**: This is the most consistent change across your existing tables. By replacing the direct `user_id` link with a `wedding_id`, you transform these features from "my personal mood board" to "**our** wedding mood board."
1.  **`ADD COLUMN lead_party / contribution_by`**: These new fields on `tasks` and `budget_items` are the primary way the AI will assign responsibility and know who to talk to about which topic, making the interaction feel intelligent and context-aware.
With these schema updates, your database will have the perfect foundation to support the sophisticated, collaborative, and stateful multi-agent system we have designed.
