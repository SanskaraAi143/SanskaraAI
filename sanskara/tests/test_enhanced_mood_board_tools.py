"""
Tests for enhanced mood board tools with image generation capabilities.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sanskara.sub_agents.creative_agent.tools import (
    generate_and_add_to_mood_board,
    upload_and_add_to_mood_board,
    get_mood_board_items
)


@pytest.fixture
def mock_tool_context():
    """Mock ADK tool context."""
    context = MagicMock()
    context.save_artifact = AsyncMock(return_value="v1.0")
    return context


@pytest.fixture
def mock_execute_supabase_sql():
    """Mock Supabase SQL execution."""
    with patch('sanskara.sub_agents.creative_agent.tools.execute_supabase_sql') as mock:
        yield mock


@pytest.fixture
def mock_db_queries():
    """Mock database query functions."""
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


class TestEnhancedMoodBoardTools:

    @pytest.mark.asyncio
    async def test_generate_and_add_to_mood_board_success(
        self, 
        mock_tool_context, 
        mock_execute_supabase_sql, 
        mock_db_queries
    ):
        """Test successful image generation and addition to mood board."""
        wedding_id = "wedding_123"
        prompt = "Beautiful Indian wedding mandap with marigolds"
        
        # Mock successful image generation
        with patch('sanskara.sub_agents.creative_agent.tools.generate_image_with_gemini') as mock_generate:
            mock_generate.return_value = {
                "status": "success",
                "artifact_filename": "generated_image_abc123.png",
                "supabase_url": "https://supabase.com/wedding-images/generated_image_abc123.png",
                "prompt_used": "Beautiful Indian wedding mandap with marigolds"
            }
            
            # Mock mood board operations
            mock_db_queries["get_mood_boards"].return_value = "SELECT * FROM mood_boards"
            mock_db_queries["create_mood_board_item"].return_value = "INSERT INTO mood_board_items"
            
            mock_execute_supabase_sql.side_effect = [
                {"status": "success", "data": [{"mood_board_id": "mb_123"}]},  # Existing mood board
                {"status": "success", "data": [{"item_id": "item_456"}]}        # Created item
            ]
            
            result = await generate_and_add_to_mood_board(
                wedding_id=wedding_id,
                prompt=prompt,
                tool_context=mock_tool_context,
                category="Decorations",
                style="traditional"
            )
        
        # Assertions
        assert result["status"] == "success"
        assert result["item_id"] == "item_456"
        assert result["image_url"] == "https://supabase.com/wedding-images/generated_image_abc123.png"
        assert result["artifact_filename"] == "generated_image_abc123.png"
        
        mock_generate.assert_called_once_with(
            prompt=prompt,
            tool_context=mock_tool_context,
            style="traditional",
            aspect_ratio="square"
        )

    @pytest.mark.asyncio
    async def test_generate_and_add_generation_failure(
        self, 
        mock_tool_context
    ):
        """Test handling of image generation failure."""
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
    async def test_generate_and_add_mood_board_failure(
        self, 
        mock_tool_context, 
        mock_execute_supabase_sql, 
        mock_db_queries
    ):
        """Test handling when image generation succeeds but mood board addition fails."""
        wedding_id = "wedding_123"
        prompt = "Test prompt"
        
        with patch('sanskara.sub_agents.creative_agent.tools.generate_image_with_gemini') as mock_generate:
            mock_generate.return_value = {
                "status": "success",
                "artifact_filename": "test.png",
                "supabase_url": "https://supabase.com/test.png"
            }
            
            with patch('sanskara.sub_agents.creative_agent.tools.add_item_to_mood_board') as mock_add:
                mock_add.return_value = {
                    "status": "error",
                    "message": "Database error"
                }
                
                result = await generate_and_add_to_mood_board(
                    wedding_id=wedding_id,
                    prompt=prompt,
                    tool_context=mock_tool_context
                )
        
        assert result["status"] == "partial_success"
        assert "Image generated successfully but failed to add to mood board" in result["message"]

    @pytest.mark.asyncio
    async def test_upload_and_add_to_mood_board_success(
        self, 
        mock_execute_supabase_sql, 
        mock_db_queries
    ):
        """Test successful image upload and addition to mood board."""
        wedding_id = "wedding_123"
        image_data = b"fake_image_data"
        filename = "uploaded_image.jpg"
        
        with patch('sanskara.sub_agents.creative_agent.tools.upload_image_to_supabase') as mock_upload:
            mock_upload.return_value = "https://supabase.com/wedding-images/uploaded_image.jpg"
            
            with patch('sanskara.sub_agents.creative_agent.tools.add_item_to_mood_board') as mock_add:
                mock_add.return_value = {
                    "status": "success",
                    "item_id": "item_789"
                }
                
                result = await upload_and_add_to_mood_board(
                    wedding_id=wedding_id,
                    image_data=image_data,
                    filename=filename,
                    category="Photography"
                )
        
        assert result["status"] == "success"
        assert result["item_id"] == "item_789"
        assert result["supabase_url"] == "https://supabase.com/wedding-images/uploaded_image.jpg"
        assert result["filename"] == filename

    @pytest.mark.asyncio
    async def test_upload_and_add_upload_failure(self):
        """Test handling of upload failure."""
        wedding_id = "wedding_123"
        image_data = b"fake_image_data"
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
    async def test_get_mood_board_items_success(
        self, 
        mock_execute_supabase_sql, 
        mock_db_queries
    ):
        """Test successful retrieval of mood board items."""
        wedding_id = "wedding_123"
        mood_board_id = "mb_123"
        
        mock_db_queries["get_mood_board_items"].return_value = "SELECT * FROM mood_board_items"
        mock_execute_supabase_sql.return_value = {
            "status": "success",
            "data": [
                {
                    "item_id": "item_1",
                    "image_url": "https://example.com/img1.jpg",
                    "note": "Beautiful flowers",
                    "category": "Decorations"
                },
                {
                    "item_id": "item_2",
                    "image_url": "https://example.com/img2.jpg",
                    "note": "Traditional attire",
                    "category": "Clothing"
                }
            ]
        }
        
        result = await get_mood_board_items(
            wedding_id=wedding_id,
            mood_board_id=mood_board_id
        )
        
        assert result["status"] == "success"
        assert result["mood_board_id"] == mood_board_id
        assert result["item_count"] == 2
        assert len(result["items"]) == 2
        assert result["items"][0]["note"] == "Beautiful flowers"

    @pytest.mark.asyncio
    async def test_get_mood_board_items_no_mood_board_id(
        self, 
        mock_execute_supabase_sql, 
        mock_db_queries
    ):
        """Test retrieval when no mood board ID is provided."""
        wedding_id = "wedding_123"
        
        # Mock getting mood board by wedding ID
        mock_db_queries["get_mood_boards"].return_value = "SELECT * FROM mood_boards"
        mock_db_queries["get_mood_board_items"].return_value = "SELECT * FROM mood_board_items"
        
        mock_execute_supabase_sql.side_effect = [
            {"status": "success", "data": [{"mood_board_id": "mb_123"}]},  # Found mood board
            {"status": "success", "data": []}  # No items
        ]
        
        result = await get_mood_board_items(wedding_id=wedding_id)
        
        assert result["status"] == "success"
        assert result["mood_board_id"] == "mb_123"
        assert result["item_count"] == 0

    @pytest.mark.asyncio
    async def test_get_mood_board_items_no_mood_board_found(
        self, 
        mock_execute_supabase_sql, 
        mock_db_queries
    ):
        """Test retrieval when no mood board exists for wedding."""
        wedding_id = "wedding_123"
        
        mock_db_queries["get_mood_boards"].return_value = "SELECT * FROM mood_boards"
        mock_execute_supabase_sql.return_value = {
            "status": "success",
            "data": []  # No mood board found
        }
        
        result = await get_mood_board_items(wedding_id=wedding_id)
        
        assert result["status"] == "error"
        assert "No mood board found" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_and_add_default_note_creation(
        self, 
        mock_tool_context, 
        mock_execute_supabase_sql, 
        mock_db_queries
    ):
        """Test that default note is created from prompt when none provided."""
        wedding_id = "wedding_123"
        long_prompt = "A very long prompt that exceeds one hundred characters and should be truncated in the default note"
        
        with patch('sanskara.sub_agents.creative_agent.tools.generate_image_with_gemini') as mock_generate:
            mock_generate.return_value = {
                "status": "success",
                "supabase_url": "https://supabase.com/test.png",
                "prompt_used": long_prompt
            }
            
            with patch('sanskara.sub_agents.creative_agent.tools.add_item_to_mood_board') as mock_add:
                mock_add.return_value = {"status": "success", "item_id": "item_123"}
                
                result = await generate_and_add_to_mood_board(
                    wedding_id=wedding_id,
                    prompt=long_prompt,
                    tool_context=mock_tool_context
                )
        
        # Verify that add_item_to_mood_board was called with a truncated note
        call_args = mock_add.call_args
        note_used = call_args[1]["note"]  # keyword argument
        assert note_used.startswith("AI generated:")
        assert len(note_used) <= 104  # "AI generated: " + 100 chars max

    @pytest.mark.asyncio
    async def test_upload_and_add_default_note_creation(self):
        """Test that default note is created from filename when none provided."""
        wedding_id = "wedding_123"
        filename = "beautiful_wedding_photo.jpg"
        
        with patch('sanskara.sub_agents.creative_agent.tools.upload_image_to_supabase') as mock_upload:
            mock_upload.return_value = "https://supabase.com/test.jpg"
            
            with patch('sanskara.sub_agents.creative_agent.tools.add_item_to_mood_board') as mock_add:
                mock_add.return_value = {"status": "success", "item_id": "item_123"}
                
                result = await upload_and_add_to_mood_board(
                    wedding_id=wedding_id,
                    image_data=b"test_data",
                    filename=filename
                )
        
        # Verify that add_item_to_mood_board was called with filename-based note
        call_args = mock_add.call_args
        note_used = call_args[1]["note"]
        assert note_used == f"Uploaded image: {filename}"


@pytest.mark.asyncio
async def test_error_handling_in_tools():
    """Test comprehensive error handling across all enhanced tools."""
    
    # Test exception in generate_and_add_to_mood_board
    with patch('sanskara.sub_agents.creative_agent.tools.generate_image_with_gemini') as mock_generate:
        mock_generate.side_effect = Exception("Unexpected error")
        
        result = await generate_and_add_to_mood_board(
            wedding_id="test_123",
            prompt="test",
            tool_context=MagicMock()
        )
        
        assert result["status"] == "error"
        assert "Unexpected error" in result["message"]
