import pytest
from unittest.mock import patch, MagicMock
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

# Mock Supabase and db_queries for unit tests
@pytest.fixture
def mock_execute_supabase_sql():
    with patch('sanskara.helpers.execute_supabase_sql') as mock_execute:
        yield mock_execute

@pytest.fixture
def mock_db_queries():
    with patch('sanskara.sub_agents.vendor_management_agent.tools.search_vendors_query') as mock_search_vendors_query, \
         patch('sanskara.sub_agents.vendor_management_agent.tools.get_vendor_details_query') as mock_get_vendor_details_query, \
         patch('sanskara.sub_agents.vendor_management_agent.tools.add_to_shortlist_query') as mock_add_to_shortlist_query, \
         patch('sanskara.sub_agents.vendor_management_agent.tools.create_booking_query') as mock_create_booking_query, \
         patch('sanskara.sub_agents.vendor_management_agent.tools.submit_review_query') as mock_submit_review_query:
        yield {
            "search_vendors_query": mock_search_vendors_query,
            "get_vendor_details_query": mock_get_vendor_details_query,
            "add_to_shortlist_query": mock_add_to_shortlist_query,
            "create_booking_query": mock_create_booking_query,
            "submit_review_query": mock_submit_review_query
        }

# Unit tests for search_vendors
def test_search_vendors_success(mock_execute_supabase_sql, mock_db_queries):
    mock_execute_supabase_sql.return_value = {"data": [
        {"vendor_id": "v1", "vendor_name": "Photo Pro", "rating": 4.5},
        {"vendor_id": "v2", "vendor_name": "Snap Shots", "rating": 3.9}
    ]}
    mock_db_queries["search_vendors_query"].return_value = "mock_query_search"

    result = search_vendors(category="photographer", city="New York")
    assert result == [
        {"vendor_id": "v1", "name": "Photo Pro", "rating": 4.5},
        {"vendor_id": "v2", "name": "Snap Shots", "rating": 3.9}
    ]
    mock_execute_supabase_sql.assert_called_once_with("mock_query_search")
    mock_db_queries["search_vendors_query"].assert_called_once_with("photographer", "New York", None, None)

def test_search_vendors_no_results(mock_execute_supabase_sql, mock_db_queries):
    mock_execute_supabase_sql.return_value = {"data": []}
    mock_db_queries["search_vendors_query"].return_value = "mock_query_search"

    result = search_vendors(category="florist", city="Los Angeles")
    assert result == []
    mock_execute_supabase_sql.assert_called_once_with("mock_query_search")
    mock_db_queries["search_vendors_query"].assert_called_once_with("florist", "Los Angeles", None, None)

def test_search_vendors_with_budget_and_style(mock_execute_supabase_sql, mock_db_queries):
    mock_execute_supabase_sql.return_value = {"data": [
        {"vendor_id": "v3", "vendor_name": "Budget Blooms", "rating": 4.0}
    ]}
    mock_db_queries["search_vendors_query"].return_value = "mock_query_search"

    budget = {"min": 1000.0, "max": 2000.0}
    style = ["modern", "elegant"]
    result = search_vendors(category="decorator", city="Chicago", budget_range=budget, style_keywords=style)
    assert result == [
        {"vendor_id": "v3", "name": "Budget Blooms", "rating": 4.0}
    ]
    mock_execute_supabase_sql.assert_called_once_with("mock_query_search")
    mock_db_queries["search_vendors_query"].assert_called_once_with("decorator", "Chicago", budget, style)

# Unit tests for get_vendor_details
def test_get_vendor_details_success(mock_execute_supabase_sql, mock_db_queries):
    mock_execute_supabase_sql.return_value = {"data": [
        {"vendor_id": "v1", "vendor_name": "Photo Pro", "address": "123 Main St"}
    ]}
    mock_db_queries["get_vendor_details_query"].return_value = "mock_query_details"

    result = get_vendor_details(vendor_id="v1")
    assert result == {"vendor_id": "v1", "vendor_name": "Photo Pro", "address": "123 Main St"}
    mock_execute_supabase_sql.assert_called_once_with("mock_query_details")
    mock_db_queries["get_vendor_details_query"].assert_called_once_with("v1")

def test_get_vendor_details_not_found(mock_execute_supabase_sql, mock_db_queries):
    mock_execute_supabase_sql.return_value = {"data": []}
    mock_db_queries["get_vendor_details_query"].return_value = "mock_query_details"

    result = get_vendor_details(vendor_id="v99")
    assert result == {}
    mock_execute_supabase_sql.assert_called_once_with("mock_query_details")
    mock_db_queries["get_vendor_details_query"].assert_called_once_with("v99")

# Unit tests for add_to_shortlist
def test_add_to_shortlist_success(mock_execute_supabase_sql, mock_db_queries):
    mock_execute_supabase_sql.return_value = {"data": [{"user_vendor_id": "uv123"}]}
    mock_db_queries["add_to_shortlist_query"].return_value = "mock_query_shortlist"

    result = add_to_shortlist(wedding_id="w1", linked_vendor_id="v1", vendor_name="Photo Pro", vendor_category="photographer")
    assert result == {"status": "success", "user_vendor_id": "uv123"}
    mock_execute_supabase_sql.assert_called_once_with("mock_query_shortlist")
    mock_db_queries["add_to_shortlist_query"].assert_called_once_with("w1", "v1", "Photo Pro", "photographer")

def test_add_to_shortlist_failure(mock_execute_supabase_sql, mock_db_queries):
    mock_execute_supabase_sql.return_value = {"data": []}
    mock_db_queries["add_to_shortlist_query"].return_value = "mock_query_shortlist"

    result = add_to_shortlist(wedding_id="w1", linked_vendor_id="v1", vendor_name="Photo Pro", vendor_category="photographer")
    assert result == {"status": "failure"}
    mock_execute_supabase_sql.assert_called_once_with("mock_query_shortlist")
    mock_db_queries["add_to_shortlist_query"].assert_called_once_with("w1", "v1", "Photo Pro", "photographer")

# Unit tests for create_booking
def test_create_booking_success(mock_execute_supabase_sql, mock_db_queries):
    mock_execute_supabase_sql.return_value = {"data": [{"booking_id": "b123"}]}
    mock_db_queries["create_booking_query"].return_value = "mock_query_booking"

    result = create_booking(wedding_id="w1", user_id="u1", vendor_id="v1", event_date="2025-10-20", total_amount=1500.0, advance_amount_due=0.0, paid_amount=0.0)
    assert result == {"booking_id": "b123"}
    mock_execute_supabase_sql.assert_called_once_with("mock_query_booking")
    mock_db_queries["create_booking_query"].assert_called_once_with("w1", "u1", "v1", "2025-10-20", 1500.0, 0.0, 0.0, 'pending_confirmation')

def test_create_booking_failure(mock_execute_supabase_sql, mock_db_queries):
    mock_execute_supabase_sql.return_value = {"data": []}
    mock_db_queries["create_booking_query"].return_value = "mock_query_booking"

    result = create_booking(wedding_id="w1", user_id="u1", vendor_id="v1", event_date="2025-10-20", total_amount=1500.0, advance_amount_due=0.0, paid_amount=0.0)
    assert result == {"status": "failure"}
    mock_execute_supabase_sql.assert_called_once_with("mock_query_booking")
    mock_db_queries["create_booking_query"].assert_called_once_with("w1", "u1", "v1", "2025-10-20", 1500.0, 0.0, 0.0, 'pending_confirmation')

# Unit tests for submit_review
def test_submit_review_success(mock_execute_supabase_sql, mock_db_queries):
    mock_execute_supabase_sql.return_value = {"data": [{"review_id": "r123"}]}
    mock_db_queries["submit_review_query"].return_value = "mock_query_review"

    result = submit_review(booking_id="b123", user_id="u1", vendor_id="v1", rating=4.0, comment="Great service!")
    assert result == {"review_id": "r123"}
    mock_execute_supabase_sql.assert_called_once_with("mock_query_review")
    mock_db_queries["submit_review_query"].assert_called_once_with("b123", "u1", "v1", 4.0, "Great service!")

def test_submit_review_failure(mock_execute_supabase_sql, mock_db_queries):
    mock_execute_supabase_sql.return_value = {"data": []}
    mock_db_queries["submit_review_query"].return_value = "mock_query_review"

    result = submit_review(booking_id="b123", user_id="u1", vendor_id="v1", rating=4.0, comment="Great service!")
    assert result == {"status": "failure"}
    mock_execute_supabase_sql.assert_called_once_with("mock_query_review")
    mock_db_queries["submit_review_query"].assert_called_once_with("b123", "u1", "v1", 4.0, "Great service!")