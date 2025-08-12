-- Enable Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

-- Helper Function for updated_at columns
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

---------------------------------------------------------------------
-- CORE TABLES FOR COLLABORATION & STATE MANAGEMENT
---------------------------------------------------------------------

-- The Wedding Table (The new central object for the entire application)
CREATE TABLE weddings (
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

CREATE TRIGGER set_weddings_updated_at
BEFORE UPDATE ON weddings
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();


-- Users Table (Links Supabase Auth to Application Profile - PRIMARILY CUSTOMERS)
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Internal App User ID
    supabase_auth_uid UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, -- Supabase Auth User ID
    email VARCHAR(255) UNIQUE NOT NULL,                 -- Synced from Supabase Auth
    display_name VARCHAR(255),                          -- User Profile Name
    wedding_id UUID REFERENCES weddings(wedding_id) ON DELETE SET NULL, -- Link to the primary wedding
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    preferences JSONB, -- { "budget_min": 5000, "budget_max": 10000, ... }
    user_type VARCHAR(50) NOT NULL DEFAULT 'customer' -- New column to differentiate user types
);
CREATE INDEX idx_users_supabase_auth_uid ON users (supabase_auth_uid);
CREATE INDEX idx_users_wedding_id ON users (wedding_id);

CREATE TRIGGER set_users_updated_at
BEFORE UPDATE ON users
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
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (wedding_id, workflow_name)
);

CREATE INDEX idx_workflows_wedding_id_status ON workflows (wedding_id, status);

CREATE TRIGGER set_workflows_updated_at
BEFORE UPDATE ON workflows
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();


-- Tasks Table
CREATE TABLE tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    is_complete BOOLEAN DEFAULT FALSE,
    due_date DATE,
    priority VARCHAR(10) DEFAULT 'medium',
    category VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'No Status',
    lead_party VARCHAR(50), -- 'bride_side', 'groom_side', 'couple'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (wedding_id, title)
);
CREATE INDEX idx_task_wedding_id_status ON tasks (wedding_id, is_complete);

CREATE TRIGGER set_tasks_updated_at
BEFORE UPDATE ON tasks
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


-- Budget Items Table
CREATE TABLE budget_items (
    item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    vendor_name TEXT,
    status VARCHAR(50) DEFAULT 'Pending',
    contribution_by VARCHAR(50), -- 'bride_side', 'groom_side', 'shared'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (wedding_id, item_name, category)
);
CREATE INDEX idx_budget_item_wedding_id ON budget_items (wedding_id);

CREATE TRIGGER set_budget_items_updated_at
BEFORE UPDATE ON budget_items
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();


-- Guest List Table
CREATE TABLE guest_list (
    guest_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    guest_name TEXT NOT NULL,
    contact_info TEXT,
    relation TEXT,
    side VARCHAR(50),
    status VARCHAR(50) DEFAULT 'Pending',
    dietary_requirements TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_guest_list_wedding_id ON guest_list (wedding_id);

CREATE TRIGGER set_guest_list_updated_at
BEFORE UPDATE ON guest_list
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();


-- Mood Boards Table
CREATE TABLE mood_boards (
    mood_board_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL DEFAULT 'Wedding Mood Board',
    description TEXT,
    visibility VARCHAR(50) NOT NULL DEFAULT 'shared',
    owner_party VARCHAR(50), -- 'bride_side', 'groom_side', 'couple'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_mood_board_wedding_id ON mood_boards (wedding_id);

CREATE TRIGGER set_mood_boards_updated_at
BEFORE UPDATE ON mood_boards
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();


-- Mood Board Items Table
CREATE TABLE mood_board_items (
    item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mood_board_id UUID NOT NULL REFERENCES mood_boards(mood_board_id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    note TEXT,
    category VARCHAR(100) DEFAULT 'Decorations',
    artifact_id UUID NULL REFERENCES image_artifacts(artifact_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_mood_board_item_board_id ON mood_board_items (mood_board_id);
CREATE INDEX idx_mood_board_items_artifact_id ON mood_board_items (artifact_id);
DROP TRIGGER IF EXISTS set_mood_board_items_updated_at ON mood_board_items;
CREATE TRIGGER set_mood_board_items_updated_at
BEFORE UPDATE ON mood_board_items
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();


-- Timeline Events Table
CREATE TABLE timeline_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    event_name TEXT NOT NULL,
    event_date_time TIMESTAMPTZ NOT NULL,
    location TEXT,
    description TEXT,
    visibility VARCHAR(50) NOT NULL DEFAULT 'shared', -- 'shared' or 'private'
    relevant_party VARCHAR(50), -- 'bride_side', 'groom_side', 'couple'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_timeline_events_wedding_id_datetime ON timeline_events (wedding_id, event_date_time);

CREATE TRIGGER set_timeline_events_updated_at
BEFORE UPDATE ON timeline_events
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();


-- Chat Sessions Table (updated to include adk_session_id, final_summary, updated_at)
CREATE TABLE chat_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    adk_session_id UUID NULL, -- Maps to live ADK session identifier
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    summary JSONB NULL,              -- (Legacy / optional structured summary)
    final_summary TEXT NULL          -- (LLM generated compact summary stored also in memories)
);
CREATE INDEX idx_chat_sessions_wedding_id ON chat_sessions (wedding_id);
CREATE INDEX idx_chat_sessions_summary_gin ON chat_sessions USING GIN (summary);
CREATE INDEX idx_chat_sessions_adk_session_id ON chat_sessions (adk_session_id);

DROP TRIGGER IF EXISTS set_chat_sessions_updated_at ON chat_sessions;
CREATE TRIGGER set_chat_sessions_updated_at
BEFORE UPDATE ON chat_sessions
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();


-- Chat Messages Table
CREATE TABLE chat_messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system', 'tool'
    sender_name VARCHAR(100) NOT NULL, -- Specific agent or user name
    content JSONB NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_chat_message_session_id_ts ON chat_messages (session_id, timestamp);


-- User Shortlisted Vendors Table (User's selected/tracked vendors)
CREATE TABLE user_shortlisted_vendors (
    user_vendor_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    vendor_name TEXT NOT NULL,
    vendor_category VARCHAR(100) NOT NULL,
    contact_info TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'contacted',
    booked_date DATE,
    notes TEXT,
    linked_vendor_id UUID REFERENCES vendors(vendor_id) NULL,
    estimated_cost DECIMAL(12,2) NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_user_shortlisted_vendors_wedding_id ON user_shortlisted_vendors (wedding_id);
CREATE INDEX idx_user_shortlisted_vendors_vendor_name ON user_shortlisted_vendors USING gin (vendor_name gin_trgm_ops);
CREATE INDEX idx_user_shortlisted_vendors_vendor_category ON user_shortlisted_vendors (vendor_category);

CREATE TRIGGER set_user_shortlisted_vendors_updated_at
BEFORE UPDATE ON user_shortlisted_vendors
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();


---------------------------------------------------------------------
-- VENDOR SIDE TABLES
---------------------------------------------------------------------

-- Vendors Table (Global Vendor Directory)
CREATE TABLE vendors (
    vendor_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_name VARCHAR(255) NOT NULL,
    vendor_category VARCHAR(100) NOT NULL, -- 'Venue', 'Photographer', etc.
    contact_email VARCHAR(255),
    phone_number VARCHAR(50),
    website_url TEXT,
    address JSONB, -- {"full_address": "", "city": "", ...}
    pricing_range JSONB, -- {"min": 5000, "max": 15000, ...}
    rating FLOAT CHECK (rating >= 0 AND rating <= 5),
    description TEXT,
    details JSONB, -- Additional details 
    portfolio_image_urls TEXT[], -- URLs to Supabase Storage
    is_active BOOLEAN DEFAULT true,
    status VARCHAR(50) DEFAULT 'active', -- New column for overall vendor status
    supabase_auth_uid UUID UNIQUE NULL REFERENCES auth.users(id), -- Supabase Auth ID of primary vendor owner/admin
    is_verified BOOLEAN DEFAULT false, -- For platform admins to verify vendors
    commission_rate DECIMAL(5,2) DEFAULT 0.05, -- Platform's commission rate for this vendor
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_vendor_category ON vendors (vendor_category);
CREATE INDEX idx_vendor_city ON vendors USING gin ((address ->> 'city'));
CREATE INDEX idx_gin_vendor_name_trgm ON vendors USING gin (vendor_name gin_trgm_ops);
CREATE INDEX idx_vendors_supabase_auth_uid ON vendors (supabase_auth_uid) WHERE supabase_auth_uid IS NOT NULL;

CREATE TRIGGER set_vendors_updated_at
BEFORE UPDATE ON vendors
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Vendor Staff / Team Members (for login and roles within a vendor's organization)
CREATE TABLE vendor_staff (
    staff_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    supabase_auth_uid UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, -- Supabase Auth ID for login
    email VARCHAR(255) UNIQUE NOT NULL, -- Synced from Supabase Auth, used for invitation
    phone_number VARCHAR(50) NULL,
    display_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'staff', -- 'owner', 'manager', 'service_contact'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_vendor_staff_vendor_id ON vendor_staff (vendor_id);
CREATE INDEX idx_vendor_staff_supabase_auth_uid ON vendor_staff (supabase_auth_uid);
CREATE INDEX idx_vendor_staff_email ON vendor_staff (email);

CREATE TRIGGER set_vendor_staff_updated_at
BEFORE UPDATE ON vendor_staff
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Services offered by Vendors (Granular)
CREATE TABLE vendor_services (
    service_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    service_name VARCHAR(255) NOT NULL,
    service_category VARCHAR(100) NOT NULL,
    description TEXT,
    base_price DECIMAL(12, 2),
    price_unit VARCHAR(50),
    min_capacity INT,
    max_capacity INT,
    customizability_details JSONB,
    is_in_house BOOLEAN DEFAULT true,
    is_negotiable BOOLEAN DEFAULT false,
    responsible_staff_id UUID NULL REFERENCES vendor_staff(staff_id) ON DELETE SET NULL,
    portfolio_image_urls TEXT[],
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_vendor_services_vendor_id ON vendor_services (vendor_id);
CREATE INDEX idx_vendor_services_category ON vendor_services (service_category);

CREATE TRIGGER set_vendor_services_updated_at
BEFORE UPDATE ON vendor_services
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Vendor Availability Calendar
CREATE TABLE vendor_availability (
    availability_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    available_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'available', -- 'available', 'booked_tentative', 'booked_confirmed', 'unavailable_custom'
    notes TEXT,
    UNIQUE (vendor_id, available_date),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_vendor_availability_vendor_date ON vendor_availability (vendor_id, available_date);

CREATE TRIGGER set_vendor_availability_updated_at
BEFORE UPDATE ON vendor_availability
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Bookings Table (Formal agreement between User and Vendor)
CREATE TABLE bookings (
    booking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE, -- Link to wedding
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE, -- User who made the booking
    vendor_id UUID NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    user_shortlisted_vendor_id UUID NULL REFERENCES user_shortlisted_vendors(user_vendor_id) ON DELETE SET NULL,
    event_date DATE NOT NULL,
    booking_status VARCHAR(50) NOT NULL DEFAULT 'pending_confirmation',
    total_amount DECIMAL(12, 2),
    advance_amount_due DECIMAL(12, 2),
    paid_amount DECIMAL(12, 2) DEFAULT 0.00,
    commission_rate_applied DECIMAL(5,4),
    commission_amount DECIMAL(12,2),
    contract_details_url TEXT,
    notes_for_vendor TEXT,
    notes_for_user TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_bookings_wedding_id ON bookings (wedding_id);
CREATE INDEX idx_bookings_user_id ON bookings (user_id);
CREATE INDEX idx_bookings_vendor_id ON bookings (vendor_id);
CREATE INDEX idx_bookings_event_date ON bookings (event_date);

CREATE TRIGGER set_bookings_updated_at
BEFORE UPDATE ON bookings
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Services included in a Booking
CREATE TABLE booking_services (
    booking_service_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    vendor_service_id UUID NOT NULL REFERENCES vendor_services(service_id) ON DELETE RESTRICT,
    negotiated_price DECIMAL(12,2),
    quantity INT DEFAULT 1,
    service_specific_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    -- No updated_at usually, but add if details can change after initial add
);
CREATE INDEX idx_booking_services_booking_id ON booking_services (booking_id);
CREATE INDEX idx_booking_services_vendor_service_id ON booking_services (vendor_service_id);

-- Payments Table
CREATE TABLE payments (
    payment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id),
    amount DECIMAL(12, 2) NOT NULL,
    payment_method VARCHAR(100),
    transaction_id VARCHAR(255) NULL,
    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    payment_type VARCHAR(50) NOT NULL DEFAULT 'advance',
    notes TEXT,
    paid_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- This should be set when payment is confirmed
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_payments_booking_id ON payments (booking_id);
CREATE INDEX idx_payments_user_id ON payments (user_id);

CREATE TRIGGER set_payments_updated_at
BEFORE UPDATE ON payments
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Vendor Tasks
CREATE TABLE vendor_tasks (
    vendor_task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    assigned_staff_id UUID NULL REFERENCES vendor_staff(staff_id) ON DELETE SET NULL,
    vendor_id UUID NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    is_complete BOOLEAN DEFAULT FALSE,
    due_date DATE,
    priority VARCHAR(10) DEFAULT 'medium',
    category VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'To Do',
    dependency_task_id UUID NULL REFERENCES vendor_tasks(vendor_task_id),
    user_facing BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_vendor_task_booking_id ON vendor_tasks (booking_id);
CREATE INDEX idx_vendor_task_assigned_staff_id ON vendor_tasks (assigned_staff_id);
CREATE INDEX idx_vendor_task_vendor_id ON vendor_tasks (vendor_id);

CREATE TRIGGER set_vendor_tasks_updated_at
BEFORE UPDATE ON vendor_tasks
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Reviews Table
CREATE TABLE reviews (
    review_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID UNIQUE NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    vendor_id UUID NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    rating FLOAT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    review_visibility VARCHAR(20) DEFAULT 'public',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    -- No updated_at typically, as reviews are usually final.
);
CREATE INDEX idx_reviews_vendor_id ON reviews (vendor_id);
CREATE INDEX idx_reviews_user_id ON reviews (user_id);

-- Notifications Table
CREATE TABLE notifications (
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_user_id UUID NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recipient_staff_id UUID NULL REFERENCES vendor_staff(staff_id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    notification_type VARCHAR(100),
    related_entity_type VARCHAR(50),
    related_entity_id UUID,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_recipient CHECK (recipient_user_id IS NOT NULL OR recipient_staff_id IS NOT NULL)
);
CREATE INDEX idx_notifications_recipient_user_id ON notifications (recipient_user_id) WHERE recipient_user_id IS NOT NULL;
CREATE INDEX idx_notifications_recipient_staff_id ON notifications (recipient_staff_id) WHERE recipient_staff_id IS NOT NULL;
-- No updated_at for notifications typically, but add if needed.

-- Task Templates Table (Optional but recommended)
CREATE TABLE task_templates (
    template_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_name VARCHAR(255) UNIQUE NOT NULL,
    target_actor VARCHAR(10) NOT NULL, -- 'user', 'vendor'
    trigger_event VARCHAR(100), -- e.g., 'booking_confirmed', 'service_X_added'
    tasks JSONB NOT NULL -- [{"title": "...", "description": "...", "default_priority": "...", "offset_days_from_event": -30}, ...]
);

-- Create staff_portfolios table
CREATE TABLE staff_portfolios (
    portfolio_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    staff_id UUID NOT NULL REFERENCES vendor_staff(staff_id) ON DELETE CASCADE,
    vendor_id UUID NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    portfolio_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NULL,
    description TEXT NULL,
    image_urls TEXT[] NULL,
    video_urls TEXT[] NULL,
    generic_attributes JSONB NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_staff_portfolios_staff_id ON staff_portfolios(staff_id);
CREATE INDEX idx_staff_portfolios_vendor_id ON staff_portfolios(vendor_id);
CREATE INDEX idx_staff_portfolios_portfolio_type ON staff_portfolios(portfolio_type);

-- Create trigger for updated_at
CREATE TRIGGER set_staff_portfolios_updated_at
BEFORE UPDATE ON staff_portfolios
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Staff-Service Assignment Table (Many-to-Many: staff can be assigned to multiple services, and services can have multiple staff)
CREATE TABLE vendor_service_staff (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES vendor_services(service_id) ON DELETE CASCADE,
    staff_id UUID NOT NULL REFERENCES vendor_staff(staff_id) ON DELETE CASCADE,
    assigned_role VARCHAR(50), -- e.g., 'lead', 'assistant', etc.
    is_active BOOLEAN DEFAULT true,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (service_id, staff_id)
);
CREATE INDEX idx_vendor_service_staff_service_id ON vendor_service_staff(service_id);
CREATE INDEX idx_vendor_service_staff_staff_id ON vendor_service_staff(staff_id);
CREATE INDEX idx_vendor_service_staff_vendor_id ON vendor_service_staff(vendor_id);

CREATE TRIGGER set_vendor_service_staff_updated_at
BEFORE UPDATE ON vendor_service_staff
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Vendor Staff Availability Table (tracks individual staff availability, not just vendor-wide)
CREATE TABLE vendor_staff_availability (
    staff_availability_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    staff_id UUID NOT NULL REFERENCES vendor_staff(staff_id) ON DELETE CASCADE,
    vendor_id UUID NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    available_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'available', -- 'available', 'booked_tentative', 'booked_confirmed', 'unavailable_custom'
    notes TEXT,
    UNIQUE (staff_id, available_date),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_vendor_staff_availability_staff_id ON vendor_staff_availability(staff_id);
CREATE INDEX idx_vendor_staff_availability_vendor_id ON vendor_staff_availability(vendor_id);
CREATE INDEX idx_vendor_staff_availability_date ON vendor_staff_availability(available_date);

CREATE TRIGGER set_vendor_staff_availability_updated_at
BEFORE UPDATE ON vendor_staff_availability
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- SUPABASE AUTH TRIGGER
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (supabase_auth_uid, email, display_name)
    VALUES (new.id, new.email, new.raw_user_meta_data->>'display_name')
    ON CONFLICT (supabase_auth_uid) DO NOTHING;
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE PROCEDURE public.handle_new_auth_user();

-- Add Image Artifacts table (supports generated / uploaded images + metadata)
CREATE TABLE IF NOT EXISTS image_artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wedding_id UUID NOT NULL REFERENCES weddings(wedding_id) ON DELETE CASCADE,
    artifact_filename TEXT NOT NULL,
    supabase_url TEXT NOT NULL,
    generation_prompt TEXT NULL,
    image_type VARCHAR(30) NOT NULL DEFAULT 'generated', -- generated | uploaded | external
    metadata JSONB NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_image_artifacts_wedding_id ON image_artifacts (wedding_id);
CREATE INDEX IF NOT EXISTS idx_image_artifacts_type ON image_artifacts (image_type);
DROP TRIGGER IF EXISTS set_image_artifacts_updated_at ON image_artifacts;
CREATE TRIGGER set_image_artifacts_updated_at
BEFORE UPDATE ON image_artifacts
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- Semantic Memories (pgvector) updated for 1024-dim model static-retrieval-mrl-en-v1
CREATE TABLE IF NOT EXISTS memories (
  memory_id   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  app_name    text        NOT NULL,
  user_id     text        NOT NULL,          -- using wedding_id grouping
  content     jsonb       NOT NULL,          -- {"text": "..", "metadata": {...}}
  embedding   vector(1024) NOT NULL,         -- updated to 1024 dims
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_memories_app_user ON memories(app_name, user_id);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories (created_at DESC);
-- (Optional ANN index; may require re-create if dimension changed from previous 1536)
DROP INDEX IF EXISTS idx_memories_embedding_ivfflat;
CREATE INDEX idx_memories_embedding_ivfflat ON memories USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
