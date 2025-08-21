#!/usr/bin/env python3
"""
Demo script for Creative Agent Image Generation and Mood Board functionality.
This script demonstrates the complete workflow of the enhanced Creative Agent.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from sanskara.sub_agents.creative_agent.image_generation_tools import (
    generate_image_with_gemini,
    upload_image_to_supabase
)
from sanskara.sub_agents.creative_agent.tools import (
    generate_and_add_to_mood_board,
    upload_and_add_to_mood_board,
    get_mood_board_items,
    add_item_to_mood_board
)
from sanskara.helpers import execute_supabase_sql
import logging
from unittest.mock import MagicMock


class CreativeAgentDemo:
    """Demo class to showcase Creative Agent capabilities."""
    
    def __init__(self):
        self.wedding_id = "demo_wedding_123"
        self.mock_tool_context = self._create_mock_tool_context()
        
    def _create_mock_tool_context(self):
        """Create a mock tool context for demonstration."""
        context = MagicMock()
        context.save_artifact = asyncio.coroutine(lambda **kwargs: "v1.0")
        return context
    
    async def setup_demo_environment(self):
        """Set up the demo environment with required data."""
        logging.info("Setting up demo environment...")
        
        # Check environment variables
        required_vars = ["GOOGLE_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logging.warning(f"Missing environment variables: {missing_vars}")
            logging.info("Demo will run in simulation mode")
            return False
        
        logging.info("All required environment variables found")
        return True
    
    async def demo_image_generation(self):
        """Demonstrate AI image generation capabilities."""
        logging.info("=== DEMO: AI Image Generation ===")
        
        prompts = [
            {
                "prompt": "Traditional Indian wedding mandap decorated with marigolds and roses",
                "style": "traditional",
                "aspect_ratio": "landscape"
            },
            {
                "prompt": "Elegant bride in red lehenga with intricate golden embroidery",
                "style": "photorealistic",
                "aspect_ratio": "portrait"
            },
            {
                "prompt": "Beautiful rangoli design with diyas for wedding entrance",
                "style": "artistic",
                "aspect_ratio": "square"
            }
        ]
        
        for i, config in enumerate(prompts, 1):
            logging.info(f"Generating image {i}/3: {config['prompt'][:50]}...")
            
            try:
                result = await generate_image_with_gemini(
                    prompt=config["prompt"],
                    tool_context=self.mock_tool_context,
                    style=config["style"],
                    aspect_ratio=config["aspect_ratio"]
                )
                
                if result["status"] == "success":
                    logging.info(f"✅ Image {i} generated successfully!")
                    logging.info(f"   Artifact: {result.get('artifact_filename')}")
                    logging.info(f"   URL: {result.get('supabase_url', 'N/A')}")
                    logging.info(f"   Size: {result.get('image_size_bytes', 0)} bytes")
                else:
                    logging.error(f"❌ Image {i} generation failed: {result.get('error_message')}")
            
            except Exception as e:
                logging.error(f"❌ Exception during image {i} generation: {e}")
            
            # Small delay between generations
            await asyncio.sleep(1)
    
    async def demo_mood_board_operations(self):
        """Demonstrate mood board management operations."""
        logging.info("=== DEMO: Mood Board Operations ===")
        
        # Test 1: Generate and add to mood board
        logging.info("Test 1: Generate image and add to mood board")
        try:
            result = await generate_and_add_to_mood_board(
                wedding_id=self.wedding_id,
                prompt="Beautiful wedding cake with traditional Indian motifs",
                tool_context=self.mock_tool_context,
                category="Catering",
                style="elegant",
                note="Inspiration for wedding cake design"
            )
            
            if result["status"] == "success":
                logging.info("✅ Successfully generated and added image to mood board")
                logging.info(f"   Item ID: {result.get('item_id')}")
                logging.info(f"   Image URL: {result.get('image_url')}")
            else:
                logging.warning(f"⚠️ Partial success or failure: {result.get('message')}")
        
        except Exception as e:
            logging.error(f"❌ Exception in generate_and_add_to_mood_board: {e}")
        
        # Test 2: Simulate upload and add to mood board
        logging.info("Test 2: Upload image and add to mood board")
        try:
            # Create fake image data for demo
            fake_image_data = b"\\x89PNG\\r\\n\\x1a\\n" + b"\\x00" * 100  # Minimal PNG header + data
            
            result = await upload_and_add_to_mood_board(
                wedding_id=self.wedding_id,
                image_data=fake_image_data,
                filename="demo_upload.png",
                category="Photography",
                note="Demo uploaded image"
            )
            
            if result["status"] == "success":
                logging.info("✅ Successfully uploaded and added image to mood board")
                logging.info(f"   Item ID: {result.get('item_id')}")
                logging.info(f"   Supabase URL: {result.get('supabase_url')}")
            else:
                logging.warning(f"⚠️ Upload failed: {result.get('message')}")
        
        except Exception as e:
            logging.error(f"❌ Exception in upload_and_add_to_mood_board: {e}")
        
        # Test 3: Retrieve mood board items
        logging.info("Test 3: Retrieve mood board items")
        try:
            result = await get_mood_board_items(
                wedding_id=self.wedding_id
            )
            
            if result["status"] == "success":
                logging.info(f"✅ Successfully retrieved mood board items")
                logging.info(f"   Total items: {result.get('item_count', 0)}")
                logging.info(f"   Mood board ID: {result.get('mood_board_id')}")
                
                # Display items
                for item in result.get("items", [])[:3]:  # Show first 3 items
                    logging.info(f"   - {item.get('note', 'No note')} ({item.get('category', 'No category')})")
            else:
                logging.warning(f"⚠️ Failed to retrieve items: {result.get('message')}")
        
        except Exception as e:
            logging.error(f"❌ Exception in get_mood_board_items: {e}")
    
    async def demo_database_queries(self):
        """Demonstrate new database query functionality."""
        logging.info("=== DEMO: Database Query Integration ===")
        
        # Test database connectivity
        try:
            # Simple test query
            test_query = "SELECT NOW() as current_time;"
            result = await execute_supabase_sql(test_query)
            
            if result.get("status") == "success":
                logging.info("✅ Database connection successful")
                current_time = result.get("data", [{}])[0].get("current_time")
                logging.info(f"   Database time: {current_time}")
            else:
                logging.error(f"❌ Database connection failed: {result.get('error')}")
        
        except Exception as e:
            logging.error(f"❌ Database test exception: {e}")
    
    async def demo_error_handling(self):
        """Demonstrate error handling capabilities."""
        logging.info("=== DEMO: Error Handling ===")
        
        # Test 1: Invalid wedding ID
        logging.info("Test 1: Invalid wedding ID")
        try:
            result = await get_mood_board_items(
                wedding_id="invalid_wedding_id"
            )
            logging.info(f"Result for invalid wedding ID: {result['status']}")
        except Exception as e:
            logging.info(f"Expected exception handled: {type(e).__name__}")
        
        # Test 2: Missing required parameters
        logging.info("Test 2: Missing API key simulation")
        original_key = os.environ.get("GOOGLE_API_KEY")
        try:
            # Temporarily remove API key
            if "GOOGLE_API_KEY" in os.environ:
                del os.environ["GOOGLE_API_KEY"]
            
            result = await generate_image_with_gemini(
                prompt="Test prompt",
                tool_context=self.mock_tool_context
            )
            
            if result["status"] == "error":
                logging.info("✅ Proper error handling for missing API key")
            
        except Exception as e:
            logging.info(f"Exception handled: {e}")
        finally:
            # Restore API key
            if original_key:
                os.environ["GOOGLE_API_KEY"] = original_key
    
    async def run_full_demo(self):
        """Run the complete demonstration."""
        logging.info("🎬 Starting Creative Agent Demo")
        logging.info("=" * 50)
        
        # Setup
        env_ready = await self.setup_demo_environment()
        
        # Run demo sections
        try:
            await self.demo_database_queries()
            await asyncio.sleep(1)
            
            if env_ready:
                await self.demo_image_generation()
                await asyncio.sleep(1)
            else:
                logging.info("Skipping image generation demo due to missing environment variables")
            
            await self.demo_mood_board_operations()
            await asyncio.sleep(1)
            
            await self.demo_error_handling()
            
        except Exception as e:
            logging.error(f"Demo failed with exception: {e}")
            import traceback
            logging.error(traceback.format_exc())
        
        logging.info("=" * 50)
        logging.info("🎉 Creative Agent Demo Complete")


async def main():
    """Main demo function."""
    print("🚀 Creative Agent Image Generation Demo")
    print("This demo showcases the enhanced Creative Agent capabilities")
    print("including AI image generation and mood board management.\\n")
    
    demo = CreativeAgentDemo()
    await demo.run_full_demo()


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
