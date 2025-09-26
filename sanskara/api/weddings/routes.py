from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from sanskara.helpers import execute_supabase_sql
import sanskara.db_queries as db_queries
from api.weddings.models import WeddingDetailsResponse, WeddingUpdate
from datetime import date
import logging
import json
from sanskara.cache import get_from_cache, set_to_cache, invalidate_cache

weddings_router = APIRouter()

def _format_wedding_dates(wedding: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to format date objects to ISO strings."""
    if isinstance(wedding.get("wedding_date"), date):
        wedding["wedding_date"] = wedding["wedding_date"].isoformat()
    if isinstance(wedding.get("created_at"), date):
        wedding["created_at"] = wedding["created_at"].isoformat()
    if isinstance(wedding.get("updated_at"), date):
        wedding["updated_at"] = wedding["updated_at"].isoformat()
    return wedding

@weddings_router.get("/{weddingId}", response_model=WeddingDetailsResponse)
async def get_wedding_details(weddingId: str):
    logging.info(f"Received request for wedding details for wedding_id: {weddingId}")
    
    cache_key = f"wedding:{weddingId}"

    # 1. Check cache first
    cached_wedding = get_from_cache(cache_key)
    if cached_wedding:
        return WeddingDetailsResponse(**_format_wedding_dates(cached_wedding))

    # 2. If cache miss, query the database
    wedding_query = await execute_supabase_sql(
        db_queries.get_wedding_details_query(),
        {"wedding_id": weddingId}
    )
    wedding_data = wedding_query.get("data")

    if not wedding_data:
        raise HTTPException(status_code=404, detail="Wedding not found.")
    
    wedding = wedding_data[0]
    
    # 3. Store the result in the cache before returning
    set_to_cache(cache_key, wedding)

    return WeddingDetailsResponse(**_format_wedding_dates(wedding))

@weddings_router.put("/{weddingId}", response_model=WeddingDetailsResponse)
@weddings_router.patch("/{weddingId}", response_model=WeddingDetailsResponse)
async def update_wedding_details(weddingId: str, wedding_update: WeddingUpdate):
    logging.info(f"Received update request for wedding_id: {weddingId} with data: {wedding_update.model_dump_json()}")

    updates = {}
    if wedding_update.wedding_name is not None:
        updates["wedding_name"] = wedding_update.wedding_name
    if wedding_update.wedding_date is not None:
        updates["wedding_date"] = wedding_update.wedding_date.isoformat()
    if wedding_update.wedding_location is not None:
        updates["wedding_location"] = wedding_update.wedding_location
    if wedding_update.wedding_tradition is not None:
        updates["wedding_tradition"] = wedding_update.wedding_tradition
    if wedding_update.wedding_style is not None:
        updates["wedding_style"] = wedding_update.wedding_style
    if wedding_update.status is not None:
        updates["status"] = wedding_update.status
    
    if updates:
        update_fields_sql = db_queries.update_wedding_fields_query(list(updates.keys()))
        params = updates
        params["wedding_id"] = weddingId
        update_result = await execute_supabase_sql(update_fields_sql, params)
        if update_result.get("status") == "error":
            logging.error(f"Failed to update wedding fields: {update_result.get('error')}")
            raise HTTPException(status_code=500, detail="Failed to update wedding details.")

    if wedding_update.details is not None:
        # Fetch existing details to merge
        wedding_query = await execute_supabase_sql(
            db_queries.get_wedding_details_query(),
            {"wedding_id": weddingId}
        )
        existing_wedding_data = wedding_query.get("data")
        if not existing_wedding_data:
            raise HTTPException(status_code=404, detail="Wedding not found for details update.")
        
        existing_details = existing_wedding_data[0].get("details", {})
        merged_details = {**existing_details, **wedding_update.details}
        
        update_details_sql = db_queries.update_wedding_details_jsonb_query()
        params = {
            "wedding_id": weddingId,
            "details": json.dumps(merged_details)
        }
        update_result = await execute_supabase_sql(update_details_sql, params)
        if update_result.get("status") == "error":
            logging.error(f"Failed to update wedding details JSONB: {update_result.get('error')}")
            raise HTTPException(status_code=500, detail="Failed to update wedding details.")
    
    # Invalidate cache after a successful update
    cache_key = f"wedding:{weddingId}"
    invalidate_cache(cache_key)

    # Retrieve and return the updated wedding details
    updated_wedding_query = await execute_supabase_sql(
        db_queries.get_wedding_details_query(),
        {"wedding_id": weddingId}
    )
    updated_wedding_data = updated_wedding_query.get("data")

    if not updated_wedding_data:
        raise HTTPException(status_code=404, detail="Wedding not found after update.")

    updated_wedding = updated_wedding_data[0]
    
    return WeddingDetailsResponse(**_format_wedding_dates(updated_wedding))