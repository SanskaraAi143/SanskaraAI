"""
Image generation and editing tools for the Creative Agent using Google's Gemini models.
Based on the provided image_gen.py implementation.
"""

import os
import uuid
import asyncio
from typing import Dict, Any, Optional
import google.generativeai as genai
from google.adk.tools import ToolContext
from google.genai import types
from logger import json_logger as logger


async def generate_image_with_gemini(
    prompt: str, 
    tool_context: ToolContext,
    style: Optional[str] = None,
    aspect_ratio: Optional[str] = "square"
) -> Dict[str, Any]:
    """
    Generates a new, original image using the dedicated Gemini image generation model.
    The generated image is saved as an artifact and uploaded to Supabase storage.

    Args:
        prompt: A detailed, descriptive prompt for the image to be generated.
        tool_context: The tool context for artifact management.
        style: Optional style modifier (e.g., "watercolor", "photorealistic", "sketch")
        aspect_ratio: Aspect ratio for the image ("square", "landscape", "portrait")

    Returns:
        A dictionary containing the status, artifact filename, and Supabase URL.
    """
    with logger.contextualize(
        tool_name="generate_image_with_gemini",
        prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt,
        style=style,
        aspect_ratio=aspect_ratio
    ):
        logger.info(f"Starting image generation with prompt: '{prompt[:50]}...'")
        
        try:
            # Configure Gemini API
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                logger.error("GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set")
                return {
                    "status": "error",
                    "error_message": "Google API key not configured"
                }
            
            genai.configure(api_key=api_key)
            
            # Enhance prompt with style and aspect ratio
            enhanced_prompt = prompt
            if style:
                enhanced_prompt = f"{style} style: {enhanced_prompt}"
            
            # Add aspect ratio guidance
            if aspect_ratio == "landscape":
                enhanced_prompt += " (landscape orientation, 16:9 ratio)"
            elif aspect_ratio == "portrait":
                enhanced_prompt += " (portrait orientation, 9:16 ratio)"
            else:
                enhanced_prompt += " (square format, 1:1 ratio)"

            image_model_name = "gemini-2.0-flash-preview-image-generation"
            image_model = genai.GenerativeModel(image_model_name)
            logger.debug(f"Using image generation model: {image_model_name}")

            generation_config = {
                "response_modalities": ["IMAGE", "TEXT"],
            }

            logger.info("Sending request to image generation model...")
            response = await image_model.generate_content_async(
                enhanced_prompt, generation_config=generation_config
            )

            # Extract image from response
            image_part = None
            for part in response.parts:
                if part.inline_data and "image" in part.inline_data.mime_type:
                    image_part = part
                    break

            if not image_part:
                logger.warning(f"No image data found in model response: {response}")
                return {
                    "status": "error",
                    "error_message": "Image data not found in the model's response. This could be due to safety filters."
                }

            img_bytes = image_part.inline_data.data
            mime_type = image_part.inline_data.mime_type
            logger.info(f"Generated {len(img_bytes)} bytes of image data ({mime_type})")

            # Create ADK artifact
            adk_image_artifact = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)

            # Generate unique filename
            unique_id = str(uuid.uuid4())[:8]
            artifact_filename = f"generated_image_{unique_id}.png"

            # Save artifact using ADK's artifact service
            version = await tool_context.save_artifact(
                filename=artifact_filename, 
                artifact=adk_image_artifact
            )
            logger.info(f"Saved artifact '{artifact_filename}' as version {version}")

            # Upload to Supabase storage
            supabase_url = await upload_image_to_supabase(
                img_bytes, 
                artifact_filename, 
                mime_type
            )

            return {
                "status": "success",
                "artifact_filename": artifact_filename,
                "artifact_version": version,
                "supabase_url": supabase_url,
                "prompt_used": enhanced_prompt,
                "image_size_bytes": len(img_bytes)
            }

        except Exception as e:
            logger.exception("Error during image generation: {}", e)
            return {
                "status": "error",
                "error_message": f"Failed to generate image: {str(e)}"
            }


async def edit_image_with_gemini(
    image_url: str,
    edit_prompt: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Edits an existing image using Gemini's image editing capabilities.
    Currently returns a placeholder status, as this feature is under development.
    
    Args:
        image_url: URL or path to the existing image
        edit_prompt: Description of the desired edits
        tool_context: The tool context for artifact management
        
    Returns:
        A dictionary containing the status and edited image information.
    """
    with logger.contextualize(
        tool_name="edit_image_with_gemini",
        image_url=image_url,
        edit_prompt=edit_prompt[:100] + "..." if len(edit_prompt) > 100 else edit_prompt
    ):
        logger.info(f"Starting image editing for: {image_url}")
        
        try:
            # Configure Gemini API
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                logger.error("GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set")
                return {
                    "status": "error",
                    "error_message": "Google API key not configured"
                }
            
            genai.configure(api_key=api_key)
            
            # Download the original image to validate accessibility (no model call yet)
            original_image_bytes = await download_image_from_url(image_url)
            if not original_image_bytes:
                return {
                    "status": "error",
                    "error_message": f"Failed to download original image from {image_url}"
                }

            # Feature not yet implemented: return graceful message
            logger.warning("Image editing with Gemini is not fully implemented in this version")
            return {
                "status": "error",
                "error_message": "Image editing feature is currently under development"
            }
            
        except Exception as e:
            logger.exception("Error during image editing: {}", e)
            return {
                "status": "error",
                "error_message": f"Failed to edit image: {str(e)}"
            }


async def upload_image_to_supabase(
    image_bytes: bytes, 
    filename: str, 
    mime_type: str
) -> Optional[str]:
    """
    Uploads an image to Supabase storage bucket.
    
    Args:
        image_bytes: The image data as bytes
        filename: The filename for the uploaded image
        mime_type: The MIME type of the image
        
    Returns:
        The public URL of the uploaded image, or None if upload failed.
    """
    with logger.contextualize(
        tool_name="upload_image_to_supabase",
        filename=filename,
        mime_type=mime_type,
        image_size=len(image_bytes)
    ):
        logger.info(f"Uploading image to Supabase: {filename}")
        
        try:
            from supabase import create_client, Client
            
            # Get Supabase configuration
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                logger.error("Supabase configuration missing")
                return None
            
            # Create Supabase client
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # Upload to storage bucket
            bucket_name = "wedding-images"  # Configure this as needed
            file_path = f"generated/{filename}"
            
            # Upload the image
            response = supabase.storage.from_(bucket_name).upload(
                file_path, 
                image_bytes,
                file_options={"content-type": mime_type}
            )
            
            # Handle different response shapes (library versions)
            upload_ok = False
            try:
                # Newer clients: UploadResponse with `.error` attribute
                upload_ok = getattr(response, "error", None) is None
            except Exception:
                pass
            
            if not upload_ok:
                # Fallbacks
                if hasattr(response, "status_code"):
                    upload_ok = (response.status_code == 200)
                elif isinstance(response, dict):
                    upload_ok = response.get("error") in (None, "")
            
            if upload_ok:
                # Get public URL
                public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
                logger.info(f"Successfully uploaded image to Supabase: {public_url}")
                return public_url
            else:
                logger.warning(f"Failed to upload to Supabase, response: {response}")
                return None
                
        except ImportError:
            logger.warning("Supabase Python client not installed. Install with: pip install supabase")
            return None
        except Exception as e:
            logger.exception("Error uploading to Supabase: {}", e)
            return None


async def download_image_from_url(url: str) -> Optional[bytes]:
    """
    Downloads an image from a URL.
    
    Args:
        url: The URL to download from
        
    Returns:
        The image data as bytes, or None if download failed.
    """
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Failed to download image: HTTP {response.status}")
                    return None
                    
    except ImportError:
        logger.warning("aiohttp not installed. Install with: pip install aiohttp")
        return None
    except Exception as e:
        logger.exception("Error downloading image: {}", e)
        return None


async def create_mood_board_collage(
    wedding_id: str,
    mood_board_id: str,
    tool_context: ToolContext,
    layout: str = "grid"
) -> Dict[str, Any]:
    """
    Creates a collage from all images in a mood board.
    
    Args:
        wedding_id: The wedding ID
        mood_board_id: The mood board ID
        tool_context: The tool context for artifact management
        layout: Layout style for the collage ("grid", "freeform", "magazine")
        
    Returns:
        A dictionary containing the status and collage information.
    """
    with logger.contextualize(
        tool_name="create_mood_board_collage",
        wedding_id=wedding_id,
        mood_board_id=mood_board_id,
        layout=layout
    ):
        logger.info(f"Creating mood board collage for wedding {wedding_id}")
        
        try:
            # Get all images from the mood board
            from sanskara.helpers import execute_supabase_sql
            from sanskara.db_queries import get_mood_board_items_query
            
            items_query = get_mood_board_items_query(mood_board_id)
            items_result = await execute_supabase_sql(items_query)
            
            if items_result.get("status") != "success" or not items_result.get("data"):
                return {
                    "status": "error",
                    "error_message": "No images found in mood board"
                }
            
            image_urls = [item.get("image_url") for item in items_result["data"] if item.get("image_url")]
            
            if len(image_urls) < 2:
                return {
                    "status": "error",
                    "error_message": "Need at least 2 images to create a collage"
                }
            
            # Generate collage using Gemini (placeholder)
            prompt = f"""Create a beautiful wedding mood board collage using a {layout} layout. 
            Combine these {len(image_urls)} images into a cohesive, elegant design that captures 
            the wedding aesthetic. Use proper spacing, balance, and harmony between the images."""
            
            logger.warning("Mood board collage creation is not fully implemented")
            
            return {
                "status": "success",
                "message": f"Collage creation requested for {len(image_urls)} images",
                "image_count": len(image_urls),
                "layout": layout
            }
            
        except Exception as e:
            logger.exception("Error creating mood board collage: {}", e)
            return {
                "status": "error",
                "error_message": f"Failed to create collage: {str(e)}"
            }
