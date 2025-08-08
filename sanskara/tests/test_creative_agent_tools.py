import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Import the tools we're testing
from sanskara.sub_agents.creative_agent.tools import (
    add_item_to_mood_board,
    generate_and_add_to_mood_board,
    upload_and_add_to_mood_board,
    get_mood_board_items
)
from sanskara.helpers import execute_supabase_sql

@pytest.fixture
def mock_db_queries():
    """Mock all database query functions."""
    with patch('sanskara.sub_agents.creative_agent.tools.get_mood_boards_by_wedding_id_query') as mock_get_boards, \
         patch('sanskara.sub_agents.creative_agent.tools.create_mood_board_query') as mock_create_board, \
         patch('sanskara.sub_agents.creative_agent.tools.create_mood_board_item_query') as mock_create_item, \
         patch('sanskara.sub_agents.creative_agent.tools.get_mood_board_items_query') as mock_get_items:
        yield {
            "get_mood_boards": mock_get_boards,
            "create_mood_board": mock_create_board,
            "create_mood_board_item": mock_create_item,
            "get_mood_board_items": mock_get_items
        }

@pytest.fixture
def mock_execute_supabase_sql():
    """Mock the Supabase SQL execution function."""
    with patch('sanskara.sub_agents.creative_agent.tools.execute_supabase_sql', new_callable=AsyncMock) as mock_exec_sql:
        yield mock_exec_sql

@pytest.fixture
def mock_tool_context():
    """Mock ADK tool context."""
    context = MagicMock()
    context.save_artifact = AsyncMock(return_value="v1.0")
    return context

class TestCreativeAgentTools:
    """Test suite for Creative Agent tools."""

    @pytest.mark.asyncio
    async def test_add_item_to_mood_board_existing_board(self, mock_db_queries, mock_execute_supabase_sql):
        """Test successful addition of an item to an existing mood board."""
        wedding_id = "test_wedding_id_1"
        image_url = "http://example.com/image1.jpg"
        note = "Beautiful flowers"
        category = "Flowers"
        existing_mood_board_id = "mb_id_123"
        new_item_id = "item_id_456"

        # Mock database queries
        mock_db_queries["get_mood_boards"].return_value = "SELECT mood_board_id FROM mood_boards WHERE wedding_id = 'test_wedding_id_1'"
        mock_db_queries["create_mood_board_item"].return_value = "INSERT INTO mood_board_items ..."

        # Mock database responses
        mock_execute_supabase_sql.side_effect = [
            {"status": "success", "data": [{"mood_board_id": existing_mood_board_id}]},  # Get mood board
            {"status": "success", "data": [{"item_id": new_item_id}]}  # Create item
        ]

        # Call the function under test
        result = await add_item_to_mood_board(wedding_id, image_url, note, category)

        # Assertions
        assert result["status"] == "success"
        assert result["item_id"] == new_item_id
        mock_db_queries["get_mood_boards"].assert_called_once_with(wedding_id)
        assert mock_execute_supabase_sql.call_count == 2

    @pytest.mark.asyncio
    async def test_add_item_to_mood_board_new_board_creation(self, mock_db_queries, mock_execute_supabase_sql):
        """Test addition when a new mood board needs to be created."""
        wedding_id = "test_wedding_id_2"
        image_url = "http://example.com/image2.jpg"
        new_mood_board_id = "new_mb_id_789"
        new_item_id = "item_id_987"

        # Mock database queries
        mock_db_queries["get_mood_boards"].return_value = "SELECT ..."
        mock_db_queries["create_mood_board"].return_value = "INSERT ..."
        mock_db_queries["create_mood_board_item"].return_value = "INSERT ..."

        # Mock database responses - no existing board, then successful creation
        mock_execute_supabase_sql.side_effect = [
            {"status": "success", "data": []},  # No existing mood board
            {"status": "success", "data": [{"mood_board_id": new_mood_board_id}]},  # Create board
            {"status": "success", "data": [{"item_id": new_item_id}]}  # Create item
        ]

        result = await add_item_to_mood_board(wedding_id, image_url)

        assert result["status"] == "success"
        assert result["item_id"] == new_item_id
        mock_db_queries["create_mood_board"].assert_called_once_with(wedding_id, name="Wedding Mood Board")
        assert mock_execute_supabase_sql.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_and_add_to_mood_board_success(self, mock_tool_context, mock_db_queries, mock_execute_supabase_sql):
        """Test successful image generation and addition to mood board."""
        wedding_id = "wedding_123"
        prompt = "Beautiful Indian wedding mandap"
        
        # Mock image generation
        with patch('sanskara.sub_agents.creative_agent.tools.generate_image_with_gemini') as mock_generate:
            mock_generate.return_value = {
                "status": "success",
                "artifact_filename": "generated_image_abc123.png",
                "supabase_url": "https://supabase.com/test.png"
            }
            
            # Mock mood board operations
            mock_db_queries["get_mood_boards"].return_value = "SELECT ..."
            mock_db_queries["create_mood_board_item"].return_value = "INSERT ..."
            
            mock_execute_supabase_sql.side_effect = [
                {"status": "success", "data": [{"mood_board_id": "mb_123"}]},
                {"status": "success", "data": [{"item_id": "item_456"}]}
            ]
            
            result = await generate_and_add_to_mood_board(
                wedding_id=wedding_id,
                prompt=prompt,
                tool_context=mock_tool_context,
                category="Decorations"
            )
        
        assert result["status"] == "success"
        assert result["item_id"] == "item_456"
        assert result["image_url"] == "https://supabase.com/test.png"
        mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_and_add_to_mood_board_success(self, mock_db_queries, mock_execute_supabase_sql):
        """Test successful image upload and addition to mood board."""
        wedding_id = "wedding_123"
        image_data = b"fake_image_data"
        filename = "test.jpg"
        
        with patch('sanskara.sub_agents.creative_agent.tools.upload_image_to_supabase') as mock_upload:
            mock_upload.return_value = "https://supabase.com/uploaded_test.jpg"
            
            # Mock mood board operations
            mock_db_queries["get_mood_boards"].return_value = "SELECT ..."
            mock_db_queries["create_mood_board_item"].return_value = "INSERT ..."
            
            mock_execute_supabase_sql.side_effect = [
                {"status": "success", "data": [{"mood_board_id": "mb_123"}]},
                {"status": "success", "data": [{"item_id": "item_789"}]}
            ]
            
            result = await upload_and_add_to_mood_board(
                wedding_id=wedding_id,
                image_data=image_data,
                filename=filename,
                category="Photography"
            )
        
        assert result["status"] == "success"
        assert result["item_id"] == "item_789"
        assert result["supabase_url"] == "https://supabase.com/uploaded_test.jpg"

    @pytest.mark.asyncio
    async def test_get_mood_board_items_success(self, mock_db_queries, mock_execute_supabase_sql):
        """Test successful retrieval of mood board items."""
        wedding_id = "wedding_123"
        
        # Mock database queries
        mock_db_queries["get_mood_boards"].return_value = "SELECT ..."
        mock_db_queries["get_mood_board_items"].return_value = "SELECT ..."
        
        mock_execute_supabase_sql.side_effect = [
            {"status": "success", "data": [{"mood_board_id": "mb_123"}]},  # Get mood board
            {"status": "success", "data": [  # Get items
                {"item_id": "item_1", "image_url": "https://example.com/img1.jpg", "note": "Test 1", "category": "Decorations"},
                {"item_id": "item_2", "image_url": "https://example.com/img2.jpg", "note": "Test 2", "category": "Flowers"}
            ]}
        ]
        
        result = await get_mood_board_items(wedding_id=wedding_id)
        
        assert result["status"] == "success"
        assert result["item_count"] == 2
        assert len(result["items"]) == 2
        assert result["items"][0]["note"] == "Test 1"

    @pytest.mark.asyncio
    async def test_add_item_error_handling(self, mock_db_queries, mock_execute_supabase_sql):
        """Test error handling in add_item_to_mood_board."""
        wedding_id = "test_wedding_id"
        image_url = "http://example.com/test.jpg"
        
        # Mock database query
        mock_db_queries["get_mood_boards"].return_value = "SELECT ..."
        
        # Mock database error
        mock_execute_supabase_sql.return_value = {
            "status": "error",
            "error": "Database connection failed"
        }
        
        result = await add_item_to_mood_board(wedding_id, image_url)
        
        # Should try to create a mood board when initial query fails
        assert "error" in result["status"] or "Failed" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_generate_and_add_generation_failure(self, mock_tool_context):
        """Test handling when image generation fails."""
        wedding_id = "wedding_123"
        prompt = "Test prompt"
        
        with patch('sanskara.sub_agents.creative_agent.tools.generate_image_with_gemini') as mock_generate:
            mock_generate.return_value = {
                "status": "error",
                "error_message": "API key not configured"
            }
            
            result = await generate_and_add_to_mood_board(
                wedding_id=wedding_id,
                prompt=prompt,
                tool_context=mock_tool_context
            )
        
        assert result["status"] == "error"
        assert "Image generation failed" in result["message"]

    @pytest.mark.asyncio
    async def test_upload_and_add_upload_failure(self):
        """Test handling when image upload fails."""
        wedding_id = "wedding_123"
        image_data = b"test_data"
        filename = "test.jpg"
        
        with patch('sanskara.sub_agents.creative_agent.tools.upload_image_to_supabase') as mock_upload:
            mock_upload.return_value = None  # Upload failed
            
            result = await upload_and_add_to_mood_board(
                wedding_id=wedding_id,
                image_data=image_data,
                filename=filename
            )
        
        assert result["status"] == "error"
        assert "Failed to upload image to storage" in result["message"]

    @pytest.mark.asyncio
    async def test_get_mood_board_items_no_board(self, mock_db_queries, mock_execute_supabase_sql):
        """Test retrieval when no mood board exists."""
        wedding_id = "wedding_123"
        
        mock_db_queries["get_mood_boards"].return_value = "SELECT ..."
        mock_execute_supabase_sql.return_value = {
            "status": "success",
            "data": []  # No mood board found
        }
        
        result = await get_mood_board_items(wedding_id=wedding_id)
        
        assert result["status"] == "error"
        assert "No mood board found" in result["message"]