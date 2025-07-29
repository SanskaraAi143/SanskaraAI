-- Add index on users.email
CREATE INDEX idx_users_email ON users (email);

-- Add index on weddings.status
CREATE INDEX idx_weddings_status ON weddings (status);

-- Add index on weddings.wedding_date
CREATE INDEX idx_weddings_wedding_date ON weddings (wedding_date);