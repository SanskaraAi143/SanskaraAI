-- This query will reset the wedding data in the database including budget,tasks,timeline,workflows,wedding,guests etc.

CREATE OR REPLACE FUNCTION reset_wedding_data(p_wedding_id UUID)
RETURNS VOID AS $$
BEGIN
    -- Disable foreign key checks for the session to allow deletion in any order
    -- EXECUTE 'SET session_replication_role = replica';

    -- Delete from tables that depend on mood_boards
    DELETE FROM mood_board_items WHERE mood_board_id IN (SELECT mood_board_id FROM mood_boards WHERE wedding_id = p_wedding_id);

    -- Delete from tables that depend on tasks
    DELETE FROM task_feedback WHERE task_id IN (SELECT task_id FROM tasks WHERE wedding_id = p_wedding_id);
    DELETE FROM task_approvals WHERE task_id IN (SELECT task_id FROM tasks WHERE wedding_id = p_wedding_id);

    -- Delete from tables that depend on bookings
    DELETE FROM booking_services WHERE booking_id IN (SELECT booking_id FROM bookings WHERE wedding_id = p_wedding_id);
    DELETE FROM payments WHERE booking_id IN (SELECT booking_id FROM bookings WHERE wedding_id = p_wedding_id);
    DELETE FROM vendor_tasks WHERE booking_id IN (SELECT booking_id FROM bookings WHERE wedding_id = p_wedding_id);
    DELETE FROM reviews WHERE booking_id IN (SELECT booking_id FROM bookings WHERE wedding_id = p_wedding_id);
    DELETE FROM bookings WHERE wedding_id = p_wedding_id;

    -- Delete from tables that directly depend on weddings
    DELETE FROM user_shortlisted_vendors WHERE wedding_id = p_wedding_id;
    DELETE FROM chat_messages WHERE session_id IN (SELECT session_id FROM chat_sessions WHERE wedding_id = p_wedding_id);
    DELETE FROM chat_sessions WHERE wedding_id = p_wedding_id;
    DELETE FROM timeline_events WHERE wedding_id = p_wedding_id;
    DELETE FROM guest_list WHERE wedding_id = p_wedding_id;
    DELETE FROM budget_items WHERE wedding_id = p_wedding_id;
    DELETE FROM tasks WHERE wedding_id = p_wedding_id;
    DELETE FROM workflows WHERE wedding_id = p_wedding_id;
    DELETE FROM wedding_members WHERE wedding_id = p_wedding_id;
    DELETE FROM mood_boards WHERE wedding_id = p_wedding_id;

    -- Handle users table: set wedding_id to NULL for users associated with this wedding
    UPDATE users SET wedding_id = NULL WHERE wedding_id = p_wedding_id;

    -- Finally, delete the wedding itself
    DELETE FROM weddings WHERE wedding_id = p_wedding_id;

    -- Re-enable foreign key checks
    -- EXECUTE 'SET session_replication_role = origin';

END;
$$ LANGUAGE plpgsql;

-- Example usage (uncomment to use):
-- SELECT reset_wedding_data('3aa1f4fc-ce6c-47da-8d44-55b7c682146e');
-- Example usage (uncomment and replace with your actual wedding ID):
-- SELECT reset_wedding_data('<your-wedding-id-here>');