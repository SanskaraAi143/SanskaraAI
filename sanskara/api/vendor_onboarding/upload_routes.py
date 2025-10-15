from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import List, Dict, Any, Optional
from google import genai
import os
import json
import asyncio
from pydantic import BaseModel, ConfigDict # ConfigDict for Pydantic v2

# Import the newly defined Pydantic models
# You MUST ensure that these schemas do NOT contain generic Dicts.
from .vendor_onboarding_schemas import VendorOnboardingForm
from .staff_onboarding_schemas import StaffOnboardingForm

# Configure Google GenAI
client = genai.Client()

upload_router = APIRouter()

@upload_router.post("/upload-and-extract")
async def upload_and_extract_data(
    files: List[UploadFile] = File(...),
    is_vendor: bool = True # Placeholder: This should come from frontend or context
):
    extracted_data_list = []
    print("Received file upload request.")
    
    # Determine which schema to use based on is_vendor flag
    response_schema_model = VendorOnboardingForm  if is_vendor else StaffOnboardingForm

    for file in files:
        temp_file_path = None
        genai_file = None # Initialize outside try block for cleanup
        try:
            # Read and save the uploaded file temporarily
            contents = await file.read()
            temp_file_path = f"/tmp/{file.filename}"
            with open(temp_file_path, "wb") as f:
                f.write(contents)
            
            # Upload the file to the Gemini API
            genai_file = client.files.upload(file=temp_file_path)
            
            prompt = f"""
            Extract all relevant information from this document.
            
            """
            prompt2 ="use this schema VendorOnboardingForm"
            response = client.models.generate_content(
                model="gemini-2.0-flash", # Use a stable model, like gemini-1.5-flash
                contents=[prompt, genai_file,prompt2],
                config=genai.types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=response_schema_model,
                ),
            )
            
            extracted_json = json.loads(response.text)
            extracted_data_list.append(extracted_json)
            
        except Exception as e:
            print(f"Error processing file {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing file {file.filename}: {str(e)}"
            )
        finally:
            # Ensure cleanup happens regardless of success or failure
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if genai_file:
                client.files.delete(name=genai_file.name)
            
    return {"status": "success", "extracted_data": extracted_data_list}

