from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Literal, Union

class HistoryEventMetadata(BaseModel):
    timestamp: datetime
    event_type: Literal["message", "artifact_upload", "system_event"]
    wedding_id: str

class ChatMessageContent(BaseModel):
    message_id: str
    sender: str
    content: str
    session_id: Optional[str] = None

class ArtifactUploadContent(BaseModel):
    artifact_id: str
    file_name: str
    file_type: str
    url: Optional[str] = None
    description: Optional[str] = None

class SystemEventContent(BaseModel):
    event_type: str
    details: str

class HistoryEvent(BaseModel):
    metadata: HistoryEventMetadata
    content: Union[ChatMessageContent, ArtifactUploadContent, SystemEventContent]

class HistoryResponse(BaseModel):
    events: List[HistoryEvent]
    total_events: int
    has_more: bool