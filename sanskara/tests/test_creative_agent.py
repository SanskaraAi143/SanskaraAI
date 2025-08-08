import pytest
from unittest.mock import AsyncMock, patch
from sanskara.sub_agents.creative_agent.tools import add_item_to_mood_board

@pytest.mark.asyncio
async def test_add_item_to_mood_board_success_existing_board():
    """Tests successful addition of an item to an existing mood board."""
    mock_get_mood_boards = AsyncMock(return_value={"status": "success", "data": [{"mood_board_id": "existing-mb-id"}]})
    mock_create_mood_board = AsyncMock() # Should not be called
    mock_execute_supabase_sql = AsyncMock(return_value={"status": "success", "data": [{"item_id": "new-item-id"}]})

    with patch('sanskara.sub_agents.creative_agent.tools.get_mood_boards_by_wedding_id_query', mock_get_mood_boards), \
         patch('sanskara.sub_agents.creative_agent.tools.create_mood_board_query', mock_create_mood_board), \
         patch('sanskara.sub_agents.creative_agent.tools.execute_supabase_sql', mock_execute_supabase_sql):
        
        result = await add_item_to_mood_board("wedding-123", "http://example.com/image.jpg", "Beautiful flowers")
        
        assert result == {"status": "success", "item_id": "new-item-id"}
        mock_get_mood_boards.assert_called_once_with("wedding-123")
        mock_create_mood_board.assert_not_called()
        mock_execute_supabase_sql.assert_called_once()

@pytest.mark.asyncio
async def test_add_item_to_mood_board_success_new_board():
    """Tests successful addition of an item to a newly created mood board."""
    mock_get_mood_boards = AsyncMock(return_value={"status": "success", "data": []}) # No existing board
    mock_create_mood_board = AsyncMock(return_value={"status": "success", "mood_board_id": "newly-created-mb-id"})
    mock_execute_supabase_sql = AsyncMock(return_value={"status": "success", "data": [{"item_id": "new-item-id"}]})

    with patch('sanskara.sub_agents.creative_agent.tools.get_mood_boards_by_wedding_id_query', mock_get_mood_boards), \
         patch('sanskara.sub_agents.creative_agent.tools.create_mood_board_query', mock_create_mood_board), \
         patch('sanskara.sub_agents.creative_agent.tools.execute_supabase_sql', mock_execute_supabase_sql):
        
        result = await add_item_to_mood_board("wedding-123", "http://example.com/image.jpg", "Beautiful flowers")
        
        assert result == {"status": "success", "item_id": "new-item-id"}
        mock_get_mood_boards.assert_called_once_with("wedding-123")
        mock_create_mood_board.assert_called_once_with("wedding-123", name="Wedding Mood Board")
        mock_execute_supabase_sql.assert_called_once()

@pytest.mark.asyncio
async def test_add_item_to_mood_board_failure_create_board():
    """Tests failure when creating a new mood board fails."""
    mock_get_mood_boards = AsyncMock(return_value={"status": "success", "data": []})
    mock_create_mood_board = AsyncMock(return_value={"status": "error", "error": "Failed to create"})
    mock_execute_supabase_sql = AsyncMock() # Should not be called

    with patch('sanskara.sub_agents.creative_agent.tools.get_mood_boards_by_wedding_id_query', mock_get_mood_boards), \
         patch('sanskara.sub_agents.creative_agent.tools.create_mood_board_query', mock_create_mood_board), \
         patch('sanskara.sub_agents.creative_agent.tools.execute_supabase_sql', mock_execute_supabase_sql):
        
        result = await add_item_to_mood_board("wedding-123", "http://example.com/image.jpg", "Beautiful flowers")
        
        assert result == {"status": "error", "message": "Failed to create mood board: Failed to create"}
        mock_get_mood_boards.assert_called_once_with("wedding-123")
        mock_create_mood_board.assert_called_once_with("wedding-123", name="Wedding Mood Board")
        mock_execute_supabase_sql.assert_not_called()

@pytest.mark.asyncio
async def test_add_item_to_mood_board_failure_add_item():
    """Tests failure when adding an item to the mood board fails."""
    mock_get_mood_boards = AsyncMock(return_value={"status": "success", "data": [{"mood_board_id": "existing-mb-id"}]})
    mock_create_mood_board = AsyncMock() # Should not be called
    mock_execute_supabase_sql = AsyncMock(return_value={"status": "error", "error": "DB insert error"})

    with patch('sanskara.sub_agents.creative_agent.tools.get_mood_boards_by_wedding_id_query', mock_get_mood_boards), \
         patch('sanskara.sub_agents.creative_agent.tools.create_mood_board_query', mock_create_mood_board), \
         patch('sanskara.sub_agents.creative_agent.tools.execute_supabase_sql', mock_execute_supabase_sql):
        
        result = await add_item_to_mood_board("wedding-123", "http://example.com/image.jpg", "Beautiful flowers")
        
        assert result == {"status": "error", "message": "Failed to add item to mood board: DB insert error"}
        mock_get_mood_boards.assert_called_once_with("wedding-123")
        mock_create_mood_board.assert_not_called()
        mock_execute_supabase_sql.assert_called_once()