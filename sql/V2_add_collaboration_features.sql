---------------------------------------------------------------------
-- 1. NEW CORE TABLES FOR COLLABORATION & STATE MANAGEMENT
---------------------------------------------------------------------

-- The Wedding Table (The new central object for the entire application)
CREATE TABLE IF NOT EXISTS weddings (
    wedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_name VARCHAR(255) NOT NULL, -- e.g., "Priya & Rohan's Wedding"
    wedding_date DATE,
    wedding_location TEXT,
    wedding_tradition TEXT,
    wedding_style VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'onboarding_in_progress', -- 'onboarding_in_progress', 'active', 'completed', 'archived'
    details JSONB, -- Stores aggregated onboarding data, other partner email expected, etc.
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Add trigger for updated_at if it doesn't exist
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_weddings_updated_at') THEN
        CREATE TRIGGER set_weddings_updated_at
        BEFORE UPDATE ON weddings
        FOR EACH ROW
        EXECUTE FUNCTION trigger_set_timestamp();
    END IF;
END $$;


-- Wedding Members Table (Links multiple users to a single wedding)
CREATE TABLE IF NOT EXISTS wedding_members (
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- e.g., 'bride', 'groom', 'planner', 'bride_family', 'groom_family'
    PRIMARY KEY (wedding_id, user_id) -- Ensures a user has only one role per wedding
);


-- Workflows Table (Long-term memory for high-level agent processes)
CREATE TABLE IF NOT EXISTS workflows (
    workflow_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    workflow_name VARCHAR(100) NOT NULL, -- e.g., 'CoreVendorBookingWorkflow', 'GuestInvitationWorkflow'
    status VARCHAR(50) NOT NULL DEFAULT 'not_started', -- 'not_started', 'in_progress', 'paused', 'awaiting_feedback', 'completed', 'failed'
    context_summary JSONB, -- Stores key decisions and IDs to re-prime the agent's context
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workflows_wedding_id_status ON workflows (wedding_id, status);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_workflows_updated_at') THEN
        CREATE TRIGGER set_workflows_updated_at
        BEFORE UPDATE ON workflows
        FOR EACH ROW
        EXECUTE FUNCTION trigger_set_timestamp();
    END IF;
END $$;


-- Task Feedback Table (Supports the "Lead and Review" model for comments)
CREATE TABLE IF NOT EXISTS task_feedback (
    feedback_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    feedback_type VARCHAR(50) NOT NULL, -- e.g., 'comment', 'like', 'dislike'
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_feedback_task_id ON task_feedback(task_id);


-- Task Approvals Table (Supports the "Lead and Review" model for final sign-offs)
CREATE TABLE IF NOT EXISTS task_approvals (
    approval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    approving_party VARCHAR(50) NOT NULL, -- 'bride_side', 'groom_side', 'couple'
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    approved_by_user_id UUID REFERENCES users(user_id), -- Optional: who clicked the button
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_task_approvals_updated_at') THEN
        CREATE TRIGGER set_task_approvals_updated_at
        BEFORE UPDATE ON task_approvals
        FOR EACH ROW
        EXECUTE FUNCTION trigger_set_timestamp();
    END IF;
END $$;


---------------------------------------------------------------------
-- 2. MODIFICATIONS TO EXISTING TABLES
---------------------------------------------------------------------

-- ALTER 'users' table to link to the wedding
ALTER TABLE users
    DROP COLUMN IF EXISTS wedding_date,
    DROP COLUMN IF EXISTS wedding_location,
    DROP COLUMN IF EXISTS wedding_tradition,
    ADD COLUMN IF NOT EXISTS wedding_id UUID REFERENCES weddings(wedding_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_users_wedding_id ON users (wedding_id);


-- ALTER 'tasks' table for collaboration
ALTER TABLE tasks
    DROP COLUMN IF EXISTS user_id, -- A task belongs to the wedding, not a single user
    ADD COLUMN IF NOT EXISTS wedding_id UUID,
    ADD COLUMN IF NOT EXISTS lead_party VARCHAR(50); -- 'bride_side', 'groom_side', 'couple'

-- Add foreign key constraint for tasks.wedding_id
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tasks_wedding_id_fkey') THEN
        ALTER TABLE tasks
        ADD CONSTRAINT tasks_wedding_id_fkey FOREIGN KEY (wedding_id) REFERENCES weddings(wedding_id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_task_wedding_id_status ON tasks (wedding_id, is_complete);


-- ALTER 'budget_items' table for collaboration
ALTER TABLE budget_items
    DROP COLUMN IF EXISTS user_id,
    ADD COLUMN IF NOT EXISTS wedding_id UUID,
    ADD COLUMN IF NOT EXISTS contribution_by VARCHAR(50); -- 'bride_side', 'groom_side', 'shared'

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'budget_items_wedding_id_fkey') THEN
        ALTER TABLE budget_items
        ADD CONSTRAINT budget_items_wedding_id_fkey FOREIGN KEY (wedding_id) REFERENCES weddings(wedding_id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_budget_item_wedding_id ON budget_items (wedding_id);


-- ALTER 'guest_list' table for collaboration
ALTER TABLE guest_list
    DROP COLUMN IF EXISTS user_id,
    ADD COLUMN IF NOT EXISTS wedding_id UUID;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'guest_list_wedding_id_fkey') THEN
        ALTER TABLE guest_list
        ADD CONSTRAINT guest_list_wedding_id_fkey FOREIGN KEY (wedding_id) REFERENCES weddings(wedding_id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_guest_list_wedding_id ON guest_list (wedding_id);


-- ALTER 'mood_boards' table for collaboration
ALTER TABLE mood_boards
    DROP COLUMN IF EXISTS user_id,
    ADD COLUMN IF NOT EXISTS wedding_id UUID;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mood_boards_wedding_id_fkey') THEN
        ALTER TABLE mood_boards
        ADD CONSTRAINT mood_boards_wedding_id_fkey FOREIGN KEY (wedding_id) REFERENCES weddings(wedding_id) ON DELETE CASCADE;
    END IF;
END $$;

ALTER TABLE mood_boards
    ADD COLUMN IF NOT EXISTS visibility VARCHAR(50) NOT NULL DEFAULT 'shared',
    ADD COLUMN IF NOT EXISTS owner_party VARCHAR(50); -- 'bride_side', 'groom_side', 'couple'

CREATE INDEX IF NOT EXISTS idx_mood_board_wedding_id ON mood_boards (wedding_id);


-- ALTER 'timeline_events' table for collaboration
ALTER TABLE timeline_events
    DROP COLUMN IF EXISTS user_id,
    ADD COLUMN IF NOT EXISTS wedding_id UUID;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'timeline_events_wedding_id_fkey') THEN
        ALTER TABLE timeline_events
        ADD CONSTRAINT timeline_events_wedding_id_fkey FOREIGN KEY (wedding_id) REFERENCES weddings(wedding_id) ON DELETE CASCADE;
    END IF;
END $$;

ALTER TABLE timeline_events
    ADD COLUMN IF NOT EXISTS visibility VARCHAR(50) NOT NULL DEFAULT 'shared', -- 'shared' or 'private'
    ADD COLUMN IF NOT EXISTS relevant_party VARCHAR(50); -- 'bride_side', 'groom_side', 'couple'

CREATE INDEX IF NOT EXISTS idx_timeline_events_wedding_id_datetime ON timeline_events (wedding_id, event_date_time);


-- ALTER 'chat_sessions' table for collaboration
ALTER TABLE chat_sessions
    DROP COLUMN IF EXISTS user_id,
    ADD COLUMN IF NOT EXISTS wedding_id UUID;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chat_sessions_wedding_id_fkey') THEN
        ALTER TABLE chat_sessions
        ADD CONSTRAINT chat_sessions_wedding_id_fkey FOREIGN KEY (wedding_id) REFERENCES weddings(wedding_id) ON DELETE CASCADE;
    END IF;
END $$;

ALTER TABLE chat_sessions
    ALTER COLUMN summary TYPE JSONB USING summary::jsonb,
    ADD COLUMN IF NOT EXISTS wedding_id UUID; -- This is a duplicate, will be removed by the previous alter

CREATE INDEX IF NOT EXISTS idx_chat_sessions_wedding_id ON chat_sessions (wedding_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_summary_gin ON chat_sessions USING GIN (summary);


-- ALTER 'user_shortlisted_vendors' to link to the wedding
ALTER TABLE user_shortlisted_vendors
    DROP COLUMN IF EXISTS user_id,
    ADD COLUMN IF NOT EXISTS wedding_id UUID;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_shortlisted_vendors_wedding_id_fkey') THEN
        ALTER TABLE user_shortlisted_vendors
        ADD CONSTRAINT user_shortlisted_vendors_wedding_id_fkey FOREIGN KEY (wedding_id) REFERENCES weddings(wedding_id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_shortlisted_vendors_wedding_id ON user_shortlisted_vendors (wedding_id);


-- ALTER 'bookings' table to link to the wedding
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS wedding_id UUID;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'bookings_wedding_id_fkey') THEN
        ALTER TABLE bookings
        ADD CONSTRAINT bookings_wedding_id_fkey FOREIGN KEY (wedding_id) REFERENCES weddings(wedding_id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_bookings_wedding_id ON bookings (wedding_id);


-- Function to handle new auth user, now also setting wedding_id if available (though primarily handled by onboarding)
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (supabase_auth_uid, email, display_name)
    VALUES (new.id, new.email, new.raw_user_meta_data->>'display_name')
    ON CONFLICT (supabase_auth_uid) DO NOTHING;
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Re-create the trigger for new auth users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE PROCEDURE public.handle_new_auth_user();