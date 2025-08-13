import time
import threading
from uuid import uuid4
from typing import Dict, List, Optional
from logger import json_logger as logger

_artifacts_lock = threading.Lock()
_artifacts: Dict[str, Dict] = {}
# Index wedding_id -> list of artifact_ids for quick recent lookup
_wedding_index: Dict[str, List[str]] = {}


def add_artifact(*, wedding_id: str, user_id: Optional[str], filename: str, content: bytes, mime_type: str, caption: Optional[str] = None) -> Dict:
    size = len(content)
    artifact_id = str(uuid4())
    record = {
        "artifact_id": artifact_id,
        "wedding_id": wedding_id,
        "user_id": user_id,
        "filename": filename,
        "mime_type": mime_type,
        "size": size,
        "caption": caption,
        "created_at": time.time(),
        # Keep raw bytes only in-memory (NOT persisted) – could be large, optionally cap
        "content": content,
    }
    with _artifacts_lock:
        _artifacts[artifact_id] = record
        _wedding_index.setdefault(wedding_id, []).append(artifact_id)
    logger.info(f"In-memory artifact stored filename={filename} size={size} wedding_id={wedding_id} artifact_id={artifact_id}")
    return {k: v for k, v in record.items() if k != "content"}


def get_recent_artifacts(wedding_id: str, limit: int = 5) -> List[Dict]:
    with _artifacts_lock:
        ids = list(_wedding_index.get(wedding_id, []))
    # Sort by created_at desc
    records = [_artifacts[i] for i in ids]
    records.sort(key=lambda r: r["created_at"], reverse=True)
    trimmed: List[Dict] = []
    for r in records[:limit]:
        trimmed.append({k: v for k, v in r.items() if k != "content"})
    return trimmed


def get_artifact_bytes(artifact_id: str) -> Optional[bytes]:
    with _artifacts_lock:
        rec = _artifacts.get(artifact_id)
        if not rec:
            return None
        return rec.get("content")
