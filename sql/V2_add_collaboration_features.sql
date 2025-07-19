
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

-- ALTER 'users' table to link to the wedding

-- ALTER 'tasks' table for collaboration
ALTER TABLE tasks
    DROP COLUMN user_id, -- A task belongs to the wedding, not a single user
    ADD COLUMN wedding_id UUID,
    ADD COLUMN lead_party VARCHAR(50); -- 'bride_side', 'groom_side', 'couple'

-- ALTER 'budget_items' table for collaboration
ALTER TABLE budget_items
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID,
    ADD COLUMN contribution_by VARCHAR(50); -- 'bride_side', 'groom_side', 'shared'


-- ALTER 'guest_list' table for collaboration
ALTER TABLE guest_list
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID;

-- ALTER 'mood_boards' table for collaboration
ALTER TABLE mood_boards
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID;


-- ALTER 'timeline_events' table for collaboration
ALTER TABLE timeline_events
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID;


-- ALTER 'chat_sessions' table for collaboration
ALTER TABLE chat_sessions
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID;

-- ALTER 'user_shortlisted_vendors' to link to the wedding
ALTER TABLE user_shortlisted_vendors
    DROP COLUMN user_id,
    ADD COLUMN wedding_id UUID;


-- ALTER 'weddings' to have details column for additional metadata
ALTER TABLE weddings
    ADD COLUMN details JSONB;

-- ALTER 'timeline_events' table to add a visibility scope
ALTER TABLE timeline_events
    ADD COLUMN visibility VARCHAR(50) NOT NULL DEFAULT 'shared', -- 'shared' or 'private'
    ADD COLUMN relevant_party VARCHAR(50); -- 'bride_side', 'groom_side', 'couple'

-- ALTER 'mood_boards' table for visibility control
ALTER TABLE mood_boards
    ADD COLUMN visibility VARCHAR(50) NOT NULL DEFAULT 'shared',
    ADD COLUMN owner_party VARCHAR(50); -- 'bride_side', 'groom_side', 'couple'


-- ALTER 'chat_sessions' table to upgrade the summary field for structured context
ALTER TABLE chat_sessions
    ALTER COLUMN summary TYPE JSONB
    USING summary::jsonb;

-- Optional: Add an index for faster querying of the summary data if needed
CREATE INDEX idx_chat_sessions_summary_gin ON chat_sessions USING GIN (summary);