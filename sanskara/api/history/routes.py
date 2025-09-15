from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Literal
from datetime import datetime
import logging
from api.history.models import (
    HistoryEvent, 
    HistoryResponse, 
    ChatMessageContent, 
    ArtifactUploadContent, 
    HistoryEventMetadata
)
from sanskara.db_queries import get_adk_session_ids_for_wedding
from sanskara.artifacts_store import add_artifact, get_recent_artifacts, get_artifact_bytes
from sanskara.models import Wedding
from sanskara.db import astra_client
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from sanskara.helpers import execute_supabase_sql
from dateutil import parser

# Replace the in-memory database setup with Supabase integration
def get_db():
    """
    Placeholder for Supabase database session.
    This function is kept for compatibility but does not create a session.
    """
    pass  # Supabase does not require a persistent session; use execute_supabase_sql directly

async def get_chat_messages_for_sessions(db, session_id):
    """
    Fetch chat messages for a given session ID using Supabase.
    First finds the wedding_id for the session, then gets all messages for that wedding.
    """
    # First get the wedding_id for this session
    get_wedding_sql = """
        SELECT wedding_id 
        FROM chat_sessions 
        WHERE session_id = :session_id;
    """
    wedding_result = await execute_supabase_sql(get_wedding_sql, {"session_id": session_id})
    
    if not wedding_result.get("data"):
        raise HTTPException(status_code=404, detail="Session not found")
        
    wedding_id = wedding_result["data"][0]["wedding_id"]
    
    # Then get all messages for this wedding_id
    sql_query = """
        SELECT cm.message_id, cm.sender_name, cm.content, cm.session_id, cs.wedding_id, cm.timestamp
        FROM chat_messages cm
        JOIN chat_sessions cs ON cm.session_id = cs.session_id
        WHERE cs.wedding_id = :wedding_id
        ORDER BY cm.timestamp ASC;
    """
    params = {"wedding_id": wedding_id}

    result = await execute_supabase_sql(sql_query, params)

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=f"Error fetching chat messages: {result.get('error')}")

    return result.get("data", [])

history_router = APIRouter()

@history_router.get("/sessions/{session_id}/history", response_model=HistoryResponse)
async def get_session_history(
    session_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_types_filter: Optional[List[Literal["message", "artifact_upload", "system_event"]]] = Query(None),
    db: Session = Depends(get_db)
):
    all_events: List[HistoryEvent] = []

    # 1. Fetch chat messages
    if not event_types_filter or "message" in event_types_filter:
        try:
            chat_messages_db = await get_chat_messages_for_sessions(db, session_id)
            for msg in chat_messages_db:
                content_text = msg["content"].get("text") if isinstance(msg["content"], dict) else msg["content"]
                all_events.append(
                    HistoryEvent(
                        metadata=HistoryEventMetadata(
                            timestamp=parser.parse(msg["timestamp"]),
                            event_type="message",
                            wedding_id=msg["wedding_id"]
                        ),
                        content=ChatMessageContent(
                            message_id=str(msg["message_id"]),
                            sender=msg["sender_name"],
                            content=content_text,
                            session_id=msg["session_id"]
                        )
                    )
                )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching chat messages: {str(e)}")

    # 2. Fetch artifact metadata (if applicable)
    if not event_types_filter or "artifact_upload" in event_types_filter:
        # Placeholder for artifact fetching logic
        pass

    # 3. Handle system events (if applicable)
    if not event_types_filter or "system_event" in event_types_filter:
        # Placeholder for system event logic
        pass

    # Filter by date
    if start_date:
        all_events = [event for event in all_events if event.metadata.timestamp >= start_date]
    if end_date:
        all_events = [event for event in all_events if event.metadata.timestamp <= end_date]

    # Sort by timestamp in descending order (newest first)
    all_events.sort(key=lambda x: x.metadata.timestamp, reverse=True)

    # Apply limit and offset
    total_events = len(all_events)
    paginated_events = all_events[offset : offset + limit]
    has_more = (offset + limit) < total_events

    return HistoryResponse(
        events=paginated_events,
        total_events=total_events,
        has_more=has_more
    )
