import datetime
import os
import uuid
import base64
from typing import Dict, Any, List, Optional
from logger import json_logger as logger # Import the custom JSON logger

# Import execute_supabase_sql from the shared helpers
from sanskara.helpers import execute_supabase_sql
from sanskara.db_queries import (
    create_mood_board_item_query,
    get_mood_board_items_query,
    create_mood_board_query,
    get_mood_boards_by_wedding_id_query
)

# Import image generation tools
from .image_generation_tools import (
    generate_image_with_gemini,
    edit_image_with_gemini,
    upload_image_to_supabase,
    create_mood_board_collage
)


async def add_item_to_mood_board(wedding_id: str, image_url: str, note: Optional[str] = None, category: str = 'Decorations') -> Dict[str, Any]:
    """
    Adds a new item to the user's mood board.
    """
    with logger.contextualize(wedding_id=wedding_id, image_url=image_url, category=category):
        logger.debug(f"Attempting to add item to mood board for wedding_id: {wedding_id}, category: {category}")
        
        # First, ensure a mood board exists for the wedding.
        # This simplified version assumes one default mood board per wedding.
        # A more complex version might allow multiple mood boards.
        mood_boards_query = get_mood_boards_by_wedding_id_query(wedding_id)
        mood_boards_result = await execute_supabase_sql(mood_boards_query)
        
        mood_board_id = None
        if mood_boards_result.get("status") == "success" and mood_boards_result.get("data"):
            mood_board_id = mood_boards_result["data"][0].get("mood_board_id")
            logger.debug(f"Found existing mood board with ID: {mood_board_id}")
        
        if not mood_board_id:
            logger.info(f"No mood board found for wedding_id: {wedding_id}. Creating a new one.")
            # Create a default mood board if none exists
            create_mb_query = create_mood_board_query(wedding_id, name="Wedding Mood Board")
            create_mb_result = await execute_supabase_sql(create_mb_query)
            
            if create_mb_result.get("status") == "success" and create_mb_result.get("data"):
                mood_board_id = create_mb_result["data"][0].get("mood_board_id")
                logger.info(f"Successfully created new mood board with ID: {mood_board_id}")
            else:
                logger.error(f"Failed to create mood board for wedding_id: {wedding_id}. Error: {create_mb_result.get('error')}", exc_info=True)
                return {"status": "error", "message": f"Failed to create mood board: {create_mb_result.get('error')}"}

        sql = create_mood_board_item_query(mood_board_id, image_url, note, category)
        result = await execute_supabase_sql(sql)
        if result.get("status") == "success":
            item_id = result.get("data", [{}])[0].get("item_id")
            logger.info(f"Successfully added item to mood board. Item ID: {item_id}")
            return {"status": "success", "item_id": item_id}
        else:
            logger.error(f"Failed to add item to mood board. Error: {result.get('error')}", exc_info=True)
            return {"status": "error", "message": f"Failed to add item to mood board: {result.get('error')}"}


async def generate_and_add_to_mood_board(
    wedding_id: str, 
    prompt: str, 
    tool_context,
    category: str = 'Generated',
    note: Optional[str] = None,
    style: Optional[str] = None,
    aspect_ratio: str = "square"
) -> Dict[str, Any]:
    """
    Generates an image using Gemini and automatically adds it to the mood board.
    
    Args:
        wedding_id: The wedding ID
        prompt: Description for image generation
        tool_context: ADK tool context for artifact management
        category: Category for mood board item
        note: Optional note for the mood board item
        style: Optional style for image generation
        aspect_ratio: Aspect ratio for the generated image
        
    Returns:
        Dictionary with generation and mood board addition results
    """
    with logger.contextualize(
        wedding_id=wedding_id,
        prompt=prompt[:50] + "..." if len(prompt) > 50 else prompt,
        category=category
    ):
        logger.info(f"Generating image and adding to mood board for wedding {wedding_id}")
        
        try:
            # Generate the image
            generation_result = await generate_image_with_gemini(
                prompt=prompt,
                tool_context=tool_context,
                style=style,
                aspect_ratio=aspect_ratio
            )
            
            if generation_result.get("status") != "success":
                logger.error(f"Image generation failed: {generation_result.get('error_message')}")
                return {
                    "status": "error",
                    "message": f"Image generation failed: {generation_result.get('error_message')}"
                }
            
            # Use the Supabase URL if available, otherwise use artifact filename
            image_url = generation_result.get("supabase_url") or generation_result.get("artifact_filename")
            
            if not image_url:
                logger.error("No image URL available from generation result")
                return {
                    "status": "error",
                    "message": "Image generation completed but no URL available"
                }
            
            # Add the generated image to mood board
            if not note:
                note = f"AI generated: {prompt[:100]}"
            
            mood_board_result = await add_item_to_mood_board(
                wedding_id=wedding_id,
                image_url=image_url,
                note=note,
                category=category
            )
            
            if mood_board_result.get("status") != "success":
                logger.error(f"Failed to add generated image to mood board: {mood_board_result.get('message')}")
                return {
                    "status": "partial_success",
                    "message": "Image generated successfully but failed to add to mood board",
                    "generation_result": generation_result,
                    "mood_board_error": mood_board_result.get("message")
                }
            
            logger.info(f"Successfully generated image and added to mood board. Item ID: {mood_board_result.get('item_id')}")
            
            return {
                "status": "success",
                "message": "Image generated and added to mood board successfully",
                "item_id": mood_board_result.get("item_id"),
                "image_url": image_url,
                "artifact_filename": generation_result.get("artifact_filename"),
                "prompt_used": generation_result.get("prompt_used")
            }
            
        except Exception as e:
            logger.error(f"Error in generate_and_add_to_mood_board: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to generate and add image: {str(e)}"
            }


async def upload_and_add_to_mood_board(
    wedding_id: str,
    image_data: bytes,
    filename: str,
    mime_type: str = "image/png",
    category: str = 'Uploaded',
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Uploads an image to Supabase storage and adds it to the mood board.
    
    Args:
        wedding_id: The wedding ID
        image_data: The image data as bytes
        filename: The filename for the image
        mime_type: MIME type of the image
        category: Category for mood board item
        note: Optional note for the mood board item
        
    Returns:
        Dictionary with upload and mood board addition results
    """
    with logger.contextualize(
        wedding_id=wedding_id,
        filename=filename,
        category=category,
        image_size=len(image_data)
    ):
        logger.info(f"Uploading image and adding to mood board for wedding {wedding_id}")
        
        try:
            # Upload to Supabase storage
            supabase_url = await upload_image_to_supabase(
                image_bytes=image_data,
                filename=filename,
                mime_type=mime_type
            )
            
            if not supabase_url:
                logger.error("Failed to upload image to Supabase storage")
                return {
                    "status": "error",
                    "message": "Failed to upload image to storage"
                }
            
            # Add to mood board
            if not note:
                note = f"Uploaded image: {filename}"
            
            mood_board_result = await add_item_to_mood_board(
                wedding_id=wedding_id,
                image_url=supabase_url,
                note=note,
                category=category
            )
            
            if mood_board_result.get("status") != "success":
                logger.error(f"Failed to add uploaded image to mood board: {mood_board_result.get('message')}")
                return {
                    "status": "partial_success",
                    "message": "Image uploaded successfully but failed to add to mood board",
                    "supabase_url": supabase_url,
                    "mood_board_error": mood_board_result.get("message")
                }
            
            logger.info(f"Successfully uploaded image and added to mood board. Item ID: {mood_board_result.get('item_id')}")
            
            return {
                "status": "success",
                "message": "Image uploaded and added to mood board successfully",
                "item_id": mood_board_result.get("item_id"),
                "supabase_url": supabase_url,
                "filename": filename
            }
            
        except Exception as e:
            logger.error(f"Error in upload_and_add_to_mood_board: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to upload and add image: {str(e)}"
            }


async def upload_and_add_to_mood_board_b64(
    wedding_id: str,
    image_data_b64: str,
    filename: str,
    mime_type: str = "image/png",
    category: str = 'Uploaded',
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Wrapper for ADK: accepts base64-encoded image data instead of bytes to satisfy
    function-calling JSON schema. Decodes and delegates to upload_and_add_to_mood_board.
    """
    with logger.contextualize(
        tool_name="upload_and_add_to_mood_board_b64",
        wedding_id=wedding_id,
        filename=filename,
        category=category,
        mime_type=mime_type,
    ):
        try:
            image_bytes = base64.b64decode(image_data_b64, validate=False)
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            return {"status": "error", "message": "Invalid base64 image data"}

        # Delegate to the bytes-based helper (not exposed as an ADK tool)
        try:
            return await upload_and_add_to_mood_board(
                wedding_id=wedding_id,
                image_data=image_bytes,
                filename=filename,
                mime_type=mime_type,
                category=category,
                note=note,
            )
        except Exception as e:
            logger.error(f"Error in upload_and_add_to_mood_board_b64: {e}")
            return {"status": "error", "message": f"Failed to upload and add image: {e}"}


async def get_mood_board_items(wedding_id: str, mood_board_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves all items from a mood board.
    
    Args:
        wedding_id: The wedding ID
        mood_board_id: Optional specific mood board ID. If not provided, uses default mood board.
        
    Returns:
        Dictionary with mood board items
    """
    with logger.contextualize(wedding_id=wedding_id, mood_board_id=mood_board_id):
        logger.debug(f"Retrieving mood board items for wedding {wedding_id}")
        
        try:
            # Get mood board ID if not provided
            if not mood_board_id:
                mood_boards_query = get_mood_boards_by_wedding_id_query(wedding_id)
                mood_boards_result = await execute_supabase_sql(mood_boards_query)
                
                if mood_boards_result.get("status") != "success" or not mood_boards_result.get("data"):
                    return {
                        "status": "error",
                        "message": "No mood board found for this wedding"
                    }
                
                mood_board_id = mood_boards_result["data"][0].get("mood_board_id")
            
            # Get mood board items
            items_query = get_mood_board_items_query(mood_board_id)
            items_result = await execute_supabase_sql(items_query)
            
            if items_result.get("status") != "success":
                logger.error(f"Failed to retrieve mood board items: {items_result.get('error')}")
                return {
                    "status": "error",
                    "message": f"Failed to retrieve mood board items: {items_result.get('error')}"
                }
            
            items = items_result.get("data", [])
            logger.info(f"Retrieved {len(items)} mood board items")
            
            return {
                "status": "success",
                "mood_board_id": mood_board_id,
                "items": items,
                "item_count": len(items)
            }
            
        except Exception as e:
            logger.error(f"Error retrieving mood board items: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to retrieve mood board items: {str(e)}"
            }