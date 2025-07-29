import pytest
from unittest.mock import patch, AsyncMock
from sanskara.sub_agents.vendor_management_agent.tools import (
    search_vendors,
    get_vendor_details,
    add_to_shortlist,
    create_booking,
    submit_review
)
from sanskara.db_queries import (
    search_vendors_query,
    get_vendor_details_query,
    add_to_shortlist_query,
    create_booking_query,
    submit_review_query
)

# Mock the execute_supabase_sql function globally for all tests in this file
@patch('sanskara.sub_agents.vendor_management_agent.tools.execute_supabase_sql', new_callable=AsyncMock)
class TestVendorManagementAgentTools:

    # Test cases for search_vendors
    def test_search_vendors_success(self, mock_execute_supabase_sql):
        # Mock successful database response
        mock_execute_supabase_sql.return_value = {"status": "success", "data": [{"vendor_id": "v1", "vendor_name": "Vendor A", "rating": 4.5}]}
        
        # Call the function
        result = search_vendors(category="photographer", city="New York")
        
        # Assertions
        assert result == [{"vendor_id": "v1", "name": "Vendor A", "rating": 4.5}] # Expected: List of dictionaries with vendor info
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    def test_search_vendors_no_results(self, mock_execute_supabase_sql):
        # Mock empty database response
        mock_execute_supabase_sql.return_value = {"status": "success", "data": []}
        
        # Call the function
        result = search_vendors(category="florist", city="Los Angeles")
        
        # Assertions
        assert result == [] # Expected: Empty list
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    def test_search_vendors_error(self, mock_execute_supabase_sql):
        # Mock database error
        mock_execute_supabase_sql.side_effect = Exception("DB error")
        
        # Call the function
        result = search_vendors(category="caterer", city="Chicago")
        
        # Assertions
        assert result == [] # Expected: Empty list on error
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    def test_search_vendors_with_budget_and_style(self, mock_execute_supabase_sql):
        # Mock successful database response
        mock_execute_supabase_sql.return_value = {"status": "success", "data": [{"vendor_id": "v2", "vendor_name": "Vendor B", "rating": 4.0}]}
        
        # Call the function with optional parameters
        result = search_vendors(
            category="venue",
            city="Miami",
            budget_range={"min": 5000, "max": 10000},
            style_keywords=["modern", "beachfront"]
        )
        
        # Assertions
        assert result == [{"vendor_id": "v2", "name": "Vendor B", "rating": 4.0}] # Expected: List of dictionaries with vendor info
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    # Test cases for get_vendor_details
    def test_get_vendor_details_success(self, mock_execute_supabase_sql):
        # Mock successful database response
        mock_execute_supabase_sql.return_value = {"status": "success", "data": [{"vendor_id": "v1", "vendor_name": "Vendor A", "address": "123 Main St"}]}
        
        # Call the function
        result = get_vendor_details(vendor_id="v1")
        
        # Assertions
        assert result == {"vendor_id": "v1", "vendor_name": "Vendor A", "address": "123 Main St"} # Expected: Dictionary of vendor details
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    def test_get_vendor_details_not_found(self, mock_execute_supabase_sql):
        # Mock empty database response
        mock_execute_supabase_sql.return_value = {"status": "success", "data": []}
        
        # Call the function
        result = get_vendor_details(vendor_id="v_nonexistent")
        
        # Assertions
        assert result == {} # Expected: Empty dictionary
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    def test_get_vendor_details_error(self, mock_execute_supabase_sql):
        # Mock database error
        mock_execute_supabase_sql.side_effect = Exception("DB error")
        
        # Call the function
        result = get_vendor_details(vendor_id="v1")
        
        # Assertions
        assert result == {} # Expected: Empty dictionary on error
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    # Test cases for add_to_shortlist
    def test_add_to_shortlist_success(self, mock_execute_supabase_sql):
        # Mock successful database response
        mock_execute_supabase_sql.return_value = {"status": "success", "data": [{"user_vendor_id": "uv1"}]}
        
        # Call the function
        result = add_to_shortlist(wedding_id="w1", linked_vendor_id="v1", vendor_name="Vendor A", vendor_category="photographer")
        
        # Assertions
        assert result == {"status": "success", "user_vendor_id": "uv1"} # Expected: Success status and user_vendor_id
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    def test_add_to_shortlist_failure(self, mock_execute_supabase_sql):
        # Mock failed database response (e.g., no data returned)
        mock_execute_supabase_sql.return_value = {"status": "failure", "data": []}
        
        # Call the function
        result = add_to_shortlist(wedding_id="w1", linked_vendor_id="v1", vendor_name="Vendor A", vendor_category="photographer")
        
        # Assertions
        assert result == {"status": "failure"} # Expected: Failure status
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    def test_add_to_shortlist_error(self, mock_execute_supabase_sql):
        # Mock database error
        mock_execute_supabase_sql.side_effect = Exception("DB error")
        
        # Call the function
        result = add_to_shortlist(wedding_id="w1", linked_vendor_id="v1", vendor_name="Vendor A", vendor_category="photographer")
        
        # Assertions
        assert result == {"status": "failure", "message": "An unexpected error occurred during shortlisting."} # Expected: Failure status with error message
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    # Test cases for create_booking
    def test_create_booking_success(self, mock_execute_supabase_sql):
        # Mock successful database response
        mock_execute_supabase_sql.return_value = {"status": "success", "data": [{"booking_id": "b1"}]}
        
        # Call the function
        result = create_booking(
            wedding_id="w1",
            user_id="u1",
            vendor_id="v1",
            event_date="2025-10-26",
            total_amount=1000.0,
            advance_amount_due=200.0,
            paid_amount=0.0,
            booking_status="pending_confirmation"
        )
        
        # Assertions
        assert result == {"booking_id": "b1"} # Expected: Booking ID
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    def test_create_booking_failure(self, mock_execute_supabase_sql):
        # Mock failed database response
        mock_execute_supabase_sql.return_value = {"status": "failure", "data": []}
        
        # Call the function
        result = create_booking(
            wedding_id="w1",
            user_id="u1",
            vendor_id="v1",
            event_date="2025-10-26",
            total_amount=1000.0
        )
        
        # Assertions
        assert result == {"status": "failure"} # Expected: Failure status
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    def test_create_booking_error(self, mock_execute_supabase_sql):
        # Mock database error
        mock_execute_supabase_sql.side_effect = Exception("DB error")
        
        # Call the function
        result = create_booking(
            wedding_id="w1",
            user_id="u1",
            vendor_id="v1",
            event_date="2025-10-26",
            total_amount=1000.0
        )
        
        # Assertions
        assert result == {"status": "failure", "message": "An unexpected error occurred during booking creation."} # Expected: Failure status with error message
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    # Test cases for submit_review
    def test_submit_review_success(self, mock_execute_supabase_sql):
        # Mock successful database response
        mock_execute_supabase_sql.return_value = {"status": "success", "data": [{"review_id": "r1"}]}
        
        # Call the function
        result = submit_review(
            booking_id="b1",
            user_id="u1",
            vendor_id="v1",
            rating=5.0,
            comment="Excellent service!"
        )
        
        # Assertions
        assert result == {"review_id": "r1"} # Expected: Review ID
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    def test_submit_review_failure(self, mock_execute_supabase_sql):
        # Mock failed database response
        mock_execute_supabase_sql.return_value = {"status": "failure", "data": []}
        
        # Call the function
        result = submit_review(
            booking_id="b1",
            user_id="u1",
            vendor_id="v1",
            rating=3.0,
            comment="Okay service."
        )
        
        # Assertions
        assert result == {"status": "failure"} # Expected: Failure status
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called

    def test_submit_review_error(self, mock_execute_supabase_sql):
        # Mock database error
        mock_execute_supabase_sql.side_effect = Exception("DB error")
        
        # Call the function
        result = submit_review(
            booking_id="b1",
            user_id="u1",
            vendor_id="v1",
            rating=1.0,
            comment="Bad service."
        )
        
        # Assertions
        assert result == {"status": "failure", "message": "An unexpected error occurred during review submission."} # Expected: Failure status with error message
        assert mock_execute_supabase_sql.called # Expected: execute_supabase_sql was called