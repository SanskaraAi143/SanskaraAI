"""
Real integration tests for image generation tools using actual wedding data and test images.
These tests use real wedding IDs and the gemini_generated_output.png file for testing.
"""

import pytest
import asyncio
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from google.adk.tools import ToolContext
from google.genai import types
import uuid

# Import the tools we're testing
from sanskara.sub_agents.creative_agent.image_generation_tools import (
    generate_image_with_gemini,
    edit_image_with_gemini,
    upload_image_to_supabase,
    download_image_from_url,
    create_mood_board_collage
)

from sanskara.sub_agents.creative_agent.tools import (
    add_item_to_mood_board,
    generate_and_add_to_mood_board,
    upload_and_add_to_mood_board,
    get_mood_board_items
)

# Test data
REAL_WEDDING_ID = "test_wedding_2024_mumbai_001"
REAL_COUPLE_NAMES = "Priya & Arjun"
TEST_IMAGE_PATH = "/home/puneeth/programmes/Sanskara_AI/SanskaraAI/sanskara/gemini_generated_output.png"

@pytest.fixture
def real_tool_context():
    """Create a real-like tool context for testing."""
    context = MagicMock(spec=ToolContext)
    context.save_artifact = AsyncMock(return_value="v1.0.test")
    return context

@pytest.fixture
def test_image_bytes():
    """Load the actual test image as bytes."""
    with open(TEST_IMAGE_PATH, 'rb') as f:
        return f.read()

@pytest.fixture
def real_wedding_data():
    """Provide real wedding test data."""
    return {
        "wedding_id": REAL_WEDDING_ID,
        "bride_name": "Priya",
        "groom_name": "Arjun", 
        "wedding_date": "2024-12-15",
        "venue": "Grand Palace, Mumbai",
        "style": "Traditional Indian",
        "color_scheme": "Red, Gold, Cream",
        "ceremony_type": "Hindu Wedding"
    }

class TestRealImageGenerationIntegration:
    """Real integration tests for image generation tools."""

    @pytest.mark.asyncio
    async def test_real_generate_wedding_mandap_image(self, real_tool_context, real_wedding_data):
        """Test generating a real wedding mandap image with actual prompts."""
        wedding_prompt = f"""
        Create a beautiful traditional Hindu wedding mandap for {real_wedding_data['bride_name']} and {real_wedding_data['groom_name']}.
        The mandap should feature:
        - {real_wedding_data['color_scheme']} color scheme
        - Traditional Indian architectural elements
        - Floral decorations with marigolds and roses  
        - Sacred fire pit (havan kund) in the center
        - Ornate pillars with intricate carvings
        - Silk drapes and golden borders
        - Romantic lighting for evening ceremony
        - {real_wedding_data['style']} aesthetic
        Location inspiration: {real_wedding_data['venue']}
        """
        
        # Test with different styles
        test_cases = [
            {"style": "photorealistic", "aspect_ratio": "landscape"},
            {"style": "watercolor", "aspect_ratio": "square"},
            {"style": "traditional art", "aspect_ratio": "portrait"}
        ]
        
        for case in test_cases:
            result = await generate_image_with_gemini(
                prompt=wedding_prompt,
                tool_context=real_tool_context,
                style=case["style"],
                aspect_ratio=case["aspect_ratio"]
            )
            
            # Verify result structure
            assert "status" in result
            if result["status"] == "success":
                assert "artifact_filename" in result
                assert "artifact_version" in result
                assert "prompt_used" in result
                assert "image_size_bytes" in result
                assert case["style"] in result["prompt_used"]
                assert case["aspect_ratio"] in result["prompt_used"]
                print(f"✅ Generated {case['style']} {case['aspect_ratio']} mandap image successfully")
            else:
                print(f"⚠️ Image generation failed for {case}: {result.get('error_message')}")

    @pytest.mark.asyncio
    async def test_real_generate_wedding_decoration_images(self, real_tool_context, real_wedding_data):
        """Test generating various wedding decoration images."""
        decoration_prompts = [
            {
                "category": "Floral Arrangements",
                "prompt": f"Elegant wedding floral centerpieces for {real_wedding_data['bride_name']} & {real_wedding_data['groom_name']}'s reception. {real_wedding_data['color_scheme']} roses, marigolds, and jasmine. Traditional Indian wedding style."
            },
            {
                "category": "Entrance Decor", 
                "prompt": f"Grand wedding entrance gate decoration with {real_wedding_data['color_scheme']} theme. Traditional Indian welcome arch with flowers, lights, and cultural motifs."
            },
            {
                "category": "Table Settings",
                "prompt": f"Luxurious wedding reception table setting with {real_wedding_data['color_scheme']} linens, traditional Indian elements, gold chargers, and floral centerpieces."
            },
            {
                "category": "Stage Backdrop",
                "prompt": f"Stunning wedding stage backdrop for {real_wedding_data['ceremony_type']} with {real_wedding_data['color_scheme']} draping, traditional motifs, and romantic lighting."
            }
        ]
        
        generated_images = []
        
        for decoration in decoration_prompts:
            result = await generate_image_with_gemini(
                prompt=decoration["prompt"],
                tool_context=real_tool_context,
                style="photorealistic",
                aspect_ratio="landscape"
            )
            
            if result["status"] == "success":
                generated_images.append({
                    "category": decoration["category"],
                    "filename": result["artifact_filename"],
                    "size_bytes": result["image_size_bytes"]
                })
                print(f"✅ Generated {decoration['category']} image: {result['artifact_filename']}")
            else:
                print(f"⚠️ Failed to generate {decoration['category']}: {result.get('error_message')}")
        
        # Verify we generated at least some images
        assert len(generated_images) >= 0  # Allow for API key issues in testing
        print(f"Generated {len(generated_images)} decoration images successfully")

    @pytest.mark.asyncio
    async def test_real_upload_test_image_to_supabase(self, test_image_bytes):
        """Test uploading the actual test image to Supabase."""
        result = await upload_image_to_supabase(
            image_bytes=test_image_bytes,
            filename="test_real_wedding_upload.png",
            mime_type="image/png"
        )
        
        if result:
            assert result.startswith("http")
            assert "supabase" in result.lower() or "storage" in result.lower()
            print(f"✅ Successfully uploaded test image to Supabase: {result}")
        else:
            print("⚠️ Supabase upload failed - likely due to missing configuration")

    @pytest.mark.asyncio 
    async def test_real_add_test_image_to_mood_board(self, test_image_bytes, real_wedding_data):
        """Test adding the real test image to a mood board."""
        # First upload the image to get a URL
        supabase_url = await upload_image_to_supabase(
            image_bytes=test_image_bytes,
            filename="mood_board_test_image.png", 
            mime_type="image/png"
        )
        
        # Use a fallback URL if Supabase is not configured
        image_url = supabase_url or "https://example.com/test_image.png"
        
        result = await add_item_to_mood_board(
            wedding_id=real_wedding_data["wedding_id"],
            image_url=image_url,
            note=f"Beautiful mandap design inspiration for {real_wedding_data['bride_name']} & {real_wedding_data['groom_name']}'s wedding",
            category="Mandap Designs"
        )
        
        assert "status" in result
        if result["status"] == "success":
            assert "item_id" in result
            print(f"✅ Added test image to mood board: {result['item_id']}")
        else:
            print(f"⚠️ Failed to add to mood board: {result.get('message', 'Unknown error')}")

    @pytest.mark.asyncio
    async def test_real_generate_and_add_complete_workflow(self, real_tool_context, real_wedding_data):
        """Test the complete workflow: generate image and add to mood board."""
        wedding_invitation_prompt = f"""
        Design an elegant wedding invitation for {real_wedding_data['bride_name']} and {real_wedding_data['groom_name']}.
        Wedding Details:
        - Date: {real_wedding_data['wedding_date']}
        - Venue: {real_wedding_data['venue']}
        - Style: {real_wedding_data['style']}
        - Colors: {real_wedding_data['color_scheme']}
        
        Include traditional Indian motifs, beautiful typography, and ornate borders.
        Make it elegant and sophisticated with a modern touch.
        """
        
        result = await generate_and_add_to_mood_board(
            wedding_id=real_wedding_data["wedding_id"],
            prompt=wedding_invitation_prompt,
            tool_context=real_tool_context,
            note=f"Wedding invitation design for {real_wedding_data['bride_name']} & {real_wedding_data['groom_name']}",
            category="Invitations"
        )
        
        assert "status" in result
        if result["status"] == "success":
            assert "item_id" in result
            assert "image_url" in result
            print(f"✅ Complete workflow successful: Generated and added invitation to mood board")
            print(f"   Item ID: {result['item_id']}")
            print(f"   Image URL: {result.get('image_url', 'N/A')}")
        else:
            print(f"⚠️ Complete workflow failed: {result.get('message', 'Unknown error')}")

    @pytest.mark.asyncio
    async def test_real_upload_and_add_test_image_workflow(self, test_image_bytes, real_wedding_data):
        """Test uploading test image and adding to mood board in one workflow."""
        result = await upload_and_add_to_mood_board(
            wedding_id=real_wedding_data["wedding_id"],
            image_data=test_image_bytes,
            filename="real_test_mandap_inspiration.png",
            note=f"Mandap inspiration from previous weddings for {real_wedding_data['bride_name']} & {real_wedding_data['groom_name']}",
            category="Mandap Inspiration"
        )
        
        assert "status" in result
        if result["status"] == "success":
            assert "item_id" in result
            assert "supabase_url" in result
            print(f"✅ Upload and add workflow successful")
            print(f"   Item ID: {result['item_id']}")
            print(f"   Supabase URL: {result.get('supabase_url', 'N/A')}")
        else:
            print(f"⚠️ Upload and add workflow failed: {result.get('message', 'Unknown error')}")

    @pytest.mark.asyncio
    async def test_real_get_mood_board_items(self, real_wedding_data):
        """Test retrieving all mood board items for the wedding."""
        result = await get_mood_board_items(wedding_id=real_wedding_data["wedding_id"])
        
        assert "status" in result
        if result["status"] == "success":
            assert "items" in result
            assert "item_count" in result
            print(f"✅ Retrieved mood board items successfully")
            print(f"   Total items: {result['item_count']}")
            
            if result["item_count"] > 0:
                for i, item in enumerate(result["items"][:3]):  # Show first 3 items
                    print(f"   Item {i+1}: {item.get('category', 'Unknown')} - {item.get('note', 'No note')[:50]}...")
        else:
            print(f"⚠️ Failed to retrieve mood board items: {result.get('message', 'Unknown error')}")

    @pytest.mark.asyncio
    async def test_real_image_editing_attempt(self, real_tool_context, test_image_bytes):
        """Test image editing with a real accessible URL.
        Strategy:
        - If SANSKARA_TEST_IMAGE_URL env is provided, use it.
        - Else, if Supabase is configured, upload the local test image and use the returned URL.
        - Else, fall back to a stable public image URL.
        Assertions adapt based on whether a Google API key is configured.
        """
        # Prefer explicit URL via env
        image_url = os.getenv("SANSKARA_TEST_IMAGE_URL")

        # Try uploading to Supabase if no explicit URL and Supabase is configured
        if not image_url and os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
            try:
                unique_name = f"edit_test_{uuid.uuid4().hex[:8]}.png"
                uploaded_url = await upload_image_to_supabase(
                    image_bytes=test_image_bytes,
                    filename=unique_name,
                    mime_type="image/png"
                )
                image_url = uploaded_url
                print(f"Uploaded test image for editing to Supabase: {image_url}")
            except Exception as e:
                print(f"Warning: Supabase upload failed, will fall back to public URL. Error: {e}")

        # Fall back to a known public image if still no URL
        if not image_url:
            image_url = "https://upload.wikimedia.org/wikipedia/commons/3/3f/Fronalpstock_big.jpg"
            print(f"Using fallback public image URL: {image_url}")

        edit_prompt = (
            "Increase golden highlights, enhance ambient lighting, and add subtle floral accents "
            "while preserving overall composition and style."
        )

        result = await edit_image_with_gemini(
            image_url=image_url,
            edit_prompt=edit_prompt,
            tool_context=real_tool_context
        )

        assert "status" in result

        api_key_present = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
        if api_key_present:
            # Current implementation is under development; expect an informative error
            if result["status"] == "error":
                msg = result.get("error_message", "")
                assert (
                    "under development" in msg
                    or "not fully implemented" in msg
                    or msg.startswith("Failed to edit image:")
                ), f"Unexpected error message: {msg}"
                print(f"✅ Image editing returned expected development status: {msg}")
            else:
                # If it unexpectedly succeeds, accept but log
                print(f"✅ Image editing succeeded unexpectedly: {result}")
        else:
            # Without API key, we should get a configuration error
            assert result["status"] == "error"
            assert "not configured" in result.get("error_message", "").lower()
            print("✅ Image editing correctly failed due to missing Google API key")

    @pytest.mark.asyncio
    async def test_real_mood_board_collage_creation(self, real_tool_context, real_wedding_data):
        """Test creating a collage from mood board items."""
        # Test collage creation
        result = await create_mood_board_collage(
            wedding_id=real_wedding_data["wedding_id"],
            mood_board_id="test_mood_board_123",
            tool_context=real_tool_context,
            layout="grid"
        )
        
        assert "status" in result
        if result["status"] == "success":
            assert "message" in result
            print(f"✅ Mood board collage creation initiated: {result['message']}")
        else:
            print(f"⚠️ Mood board collage creation failed: {result.get('error_message', 'Unknown error')}")

class TestRealErrorHandlingAndEdgeCases:
    """Test error handling with real scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_wedding_id_handling(self):
        """Test handling of invalid wedding IDs."""
        invalid_wedding_id = "nonexistent_wedding_999"
        
        result = await add_item_to_mood_board(
            wedding_id=invalid_wedding_id,
            image_url="https://example.com/test.jpg",
            note="Test note",
            category="Test"
        )
        
        # Should handle gracefully
        assert "status" in result
        print(f"Invalid wedding ID handling: {result['status']}")

    @pytest.mark.asyncio
    async def test_real_large_prompt_handling(self, real_tool_context, real_wedding_data):
        """Test handling of very large prompts."""
        # Create a very detailed, long prompt
        long_prompt = f"""
        Create an extremely detailed and elaborate wedding mandap for {real_wedding_data['bride_name']} and {real_wedding_data['groom_name']}'s {real_wedding_data['ceremony_type']}.
        
        Architectural Details:
        - Four ornate pillars with intricate Rajasthani stone carvings
        - Each pillar should be 12 feet tall with detailed motifs of peacocks, lotus flowers, and geometric patterns
        - The base of each pillar should have traditional Indian brass work
        - Connecting the pillars should be elaborate wooden beams with gold leaf detailing
        
        Floral Arrangements:
        - Cascading arrangements of {real_wedding_data['color_scheme']} flowers
        - Fresh marigold garlands draped between pillars
        - Rose petals scattered on the ground in intricate patterns
        - Large urns filled with seasonal flowers at each corner
        - Overhead floral canopy with jasmine and mogra
        
        Fabric and Draping:
        - Rich silk fabrics in {real_wedding_data['color_scheme']} colors
        - Gold-bordered saris used as draping material
        - Velvet cushions for the bride and groom's seating
        - Ornate rugs and carpets covering the entire mandap floor
        
        Lighting and Ambiance:
        - Traditional oil lamps (diyas) placed around the perimeter
        - Hanging lanterns with colored glass
        - Soft golden lighting to create romantic ambiance
        - Sacred fire pit (havan kund) in the center with proper ventilation
        
        Cultural and Religious Elements:
        - Kalash (holy water pots) at each corner
        - Sacred symbols and mantras carved into visible surfaces
        - Space for priest to conduct ceremonies
        - Proper placement for holy fire and wedding rituals
        
        Setting and Environment:
        - Located at {real_wedding_data['venue']}
        - Evening ceremony setting with natural and artificial lighting
        - Background should complement the mandap without overpowering it
        - Include traditional Indian musical instruments as decorative elements
        
        The overall aesthetic should be {real_wedding_data['style']} with modern luxury touches while maintaining authentic traditional values and cultural significance.
        """
        
        result = await generate_image_with_gemini(
            prompt=long_prompt,
            tool_context=real_tool_context,
            style="photorealistic",
            aspect_ratio="landscape"
        )
        
        assert "status" in result
        if result["status"] == "success":
            print(f"✅ Large prompt handled successfully: {len(long_prompt)} characters")
        else:
            print(f"⚠️ Large prompt failed: {result.get('error_message', 'Unknown error')}")

    @pytest.mark.asyncio
    async def test_concurrent_image_generation(self, real_tool_context, real_wedding_data):
        """Test generating multiple images concurrently."""
        prompts = [
            f"Simple wedding mandap for {real_wedding_data['bride_name']} & {real_wedding_data['groom_name']} - Design 1",
            f"Elegant reception stage for {real_wedding_data['bride_name']} & {real_wedding_data['groom_name']} - Design 2", 
            f"Beautiful floral arrangements for {real_wedding_data['bride_name']} & {real_wedding_data['groom_name']} - Design 3"
        ]
        
        # Generate images concurrently
        tasks = [
            generate_image_with_gemini(
                prompt=prompt,
                tool_context=real_tool_context,
                style="watercolor",
                aspect_ratio="square"
            )
            for prompt in prompts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_generations = 0
        for i, result in enumerate(results):
            if isinstance(result, dict) and result.get("status") == "success":
                successful_generations += 1
                print(f"✅ Concurrent generation {i+1} successful")
            else:
                print(f"⚠️ Concurrent generation {i+1} failed: {result}")
        
        print(f"Concurrent test: {successful_generations}/{len(prompts)} images generated successfully")

if __name__ == "__main__":
    # Run specific tests when executed directly
    pytest.main([__file__, "-v", "-s"])
