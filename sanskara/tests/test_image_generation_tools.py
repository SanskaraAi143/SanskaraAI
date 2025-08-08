"""
Tests for image generation tools in the Creative Agent.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sanskara.sub_agents.creative_agent.image_generation_tools import (
    generate_image_with_gemini,
    edit_image_with_gemini,
    upload_image_to_supabase,
    create_mood_board_collage,
    download_image_from_url
)


@pytest.fixture
def mock_tool_context():
    """Mock tool context for testing."""
    context = MagicMock()
    context.save_artifact = AsyncMock(return_value="v1.0")
    return context


@pytest.fixture
def mock_genai():
    """Mock Google GenerativeAI."""
    with patch('sanskara.sub_agents.creative_agent.image_generation_tools.genai') as mock:
        yield mock


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client."""
    with patch('sanskara.sub_agents.creative_agent.image_generation_tools.create_client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


class TestImageGenerationTools:

    @pytest.mark.asyncio
    async def test_generate_image_with_gemini_success(self, mock_tool_context, mock_genai):
        """Test successful image generation with Gemini."""
        # Setup mock response
        mock_image_part = MagicMock()
        mock_image_part.inline_data.data = b"fake_image_data"
        mock_image_part.inline_data.mime_type = "image/png"
        
        mock_response = MagicMock()
        mock_response.parts = [mock_image_part]
        
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Mock environment variables
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'}):
            with patch('sanskara.sub_agents.creative_agent.image_generation_tools.upload_image_to_supabase') as mock_upload:
                mock_upload.return_value = "https://supabase.com/test-image.png"
                
                result = await generate_image_with_gemini(
                    prompt="A beautiful wedding mandap",
                    tool_context=mock_tool_context,
                    style="traditional",
                    aspect_ratio="landscape"
                )
        
        # Assertions
        assert result["status"] == "success"
        assert "artifact_filename" in result
        assert result["supabase_url"] == "https://supabase.com/test-image.png"
        assert "traditional style" in result["prompt_used"]
        assert "landscape orientation" in result["prompt_used"]
        mock_tool_context.save_artifact.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_image_missing_api_key(self, mock_tool_context):
        """Test image generation with missing API key."""
        with patch.dict('os.environ', {}, clear=True):
            result = await generate_image_with_gemini(
                prompt="Test prompt",
                tool_context=mock_tool_context
            )
        
        assert result["status"] == "error"
        assert "Google API key not configured" in result["error_message"]

    @pytest.mark.asyncio
    async def test_generate_image_no_image_in_response(self, mock_tool_context, mock_genai):
        """Test handling when no image is returned from Gemini."""
        mock_response = MagicMock()
        mock_response.parts = []  # No image parts
        
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'}):
            result = await generate_image_with_gemini(
                prompt="Test prompt",
                tool_context=mock_tool_context
            )
        
        assert result["status"] == "error"
        assert "Image data not found" in result["error_message"]

    @pytest.mark.asyncio
    async def test_upload_image_to_supabase_success(self, mock_supabase_client):
        """Test successful image upload to Supabase."""
        # Setup mock storage response
        mock_storage = MagicMock()
        mock_storage.from_.return_value.upload.return_value.status_code = 200
        mock_storage.from_.return_value.get_public_url.return_value = "https://supabase.com/test.png"
        mock_supabase_client.storage = mock_storage
        
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test_key'
        }):
            result = await upload_image_to_supabase(
                image_bytes=b"test_image_data",
                filename="test.png",
                mime_type="image/png"
            )
        
        assert result == "https://supabase.com/test.png"
        mock_storage.from_.assert_called_with("wedding-images")

    @pytest.mark.asyncio
    async def test_upload_image_to_supabase_missing_config(self):
        """Test upload with missing Supabase configuration."""
        with patch.dict('os.environ', {}, clear=True):
            result = await upload_image_to_supabase(
                image_bytes=b"test_data",
                filename="test.png",
                mime_type="image/png"
            )
        
        assert result is None

    @pytest.mark.asyncio
    async def test_download_image_from_url_success(self):
        """Test successful image download from URL."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"image_data")
        
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('sanskara.sub_agents.creative_agent.image_generation_tools.aiohttp.ClientSession') as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await download_image_from_url("https://example.com/image.jpg")
        
        assert result == b"image_data"

    @pytest.mark.asyncio
    async def test_download_image_from_url_failure(self):
        """Test failed image download."""
        mock_response = MagicMock()
        mock_response.status = 404
        
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('sanskara.sub_agents.creative_agent.image_generation_tools.aiohttp.ClientSession') as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await download_image_from_url("https://example.com/notfound.jpg")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_edit_image_with_gemini_not_implemented(self, mock_tool_context):
        """Test that image editing returns not implemented message."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'}):
            with patch('sanskara.sub_agents.creative_agent.image_generation_tools.download_image_from_url') as mock_download:
                mock_download.return_value = b"fake_image_data"
                
                result = await edit_image_with_gemini(
                    image_url="https://example.com/image.jpg",
                    edit_prompt="Make it brighter",
                    tool_context=mock_tool_context
                )
        
        assert result["status"] == "error"
        assert "not fully implemented" in result["error_message"]

    @pytest.mark.asyncio
    async def test_create_mood_board_collage_insufficient_images(self):
        """Test collage creation with insufficient images."""
        with patch('sanskara.sub_agents.creative_agent.image_generation_tools.execute_supabase_sql') as mock_sql:
            mock_sql.return_value = {
                "status": "success",
                "data": [{"image_url": "https://example.com/img1.jpg"}]  # Only 1 image
            }
            
            with patch('sanskara.sub_agents.creative_agent.image_generation_tools.get_mood_board_items_query') as mock_query:
                mock_query.return_value = "SELECT * FROM mood_board_items"
                
                result = await create_mood_board_collage(
                    wedding_id="wedding_123",
                    mood_board_id="mood_123",
                    tool_context=MagicMock(),
                    layout="grid"
                )
        
        assert result["status"] == "error"
        assert "Need at least 2 images" in result["error_message"]

    @pytest.mark.asyncio
    async def test_create_mood_board_collage_success(self):
        """Test successful collage creation request."""
        with patch('sanskara.sub_agents.creative_agent.image_generation_tools.execute_supabase_sql') as mock_sql:
            mock_sql.return_value = {
                "status": "success",
                "data": [
                    {"image_url": "https://example.com/img1.jpg"},
                    {"image_url": "https://example.com/img2.jpg"},
                    {"image_url": "https://example.com/img3.jpg"}
                ]
            }
            
            with patch('sanskara.sub_agents.creative_agent.image_generation_tools.get_mood_board_items_query') as mock_query:
                mock_query.return_value = "SELECT * FROM mood_board_items"
                
                result = await create_mood_board_collage(
                    wedding_id="wedding_123",
                    mood_board_id="mood_123",
                    tool_context=MagicMock(),
                    layout="magazine"
                )
        
        assert result["status"] == "success"
        assert result["image_count"] == 3
        assert result["layout"] == "magazine"

    @pytest.mark.asyncio
    async def test_generate_image_exception_handling(self, mock_tool_context, mock_genai):
        """Test exception handling in image generation."""
        mock_genai.GenerativeModel.side_effect = Exception("API Error")
        
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'}):
            result = await generate_image_with_gemini(
                prompt="Test prompt",
                tool_context=mock_tool_context
            )
        
        assert result["status"] == "error"
        assert "Failed to generate image" in result["error_message"]
        assert "API Error" in result["error_message"]


@pytest.mark.asyncio
async def test_style_and_aspect_ratio_modifications():
    """Test that prompts are properly enhanced with style and aspect ratio."""
    mock_tool_context = MagicMock()
    mock_tool_context.save_artifact = AsyncMock(return_value="v1.0")
    
    with patch('sanskara.sub_agents.creative_agent.image_generation_tools.genai') as mock_genai:
        mock_image_part = MagicMock()
        mock_image_part.inline_data.data = b"fake_image_data"
        mock_image_part.inline_data.mime_type = "image/png"
        
        mock_response = MagicMock()
        mock_response.parts = [mock_image_part]
        
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'}):
            with patch('sanskara.sub_agents.creative_agent.image_generation_tools.upload_image_to_supabase') as mock_upload:
                mock_upload.return_value = "https://supabase.com/test.png"
                
                result = await generate_image_with_gemini(
                    prompt="A wedding scene",
                    tool_context=mock_tool_context,
                    style="watercolor",
                    aspect_ratio="portrait"
                )
        
        # Verify the prompt was enhanced
        enhanced_prompt = result["prompt_used"]
        assert "watercolor style" in enhanced_prompt
        assert "portrait orientation" in enhanced_prompt
        assert "9:16 ratio" in enhanced_prompt
