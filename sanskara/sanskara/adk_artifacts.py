from google.adk.artifacts import InMemoryArtifactService
import logging

# Global artifact service instance used across REST and WebSocket runners
artifact_service = InMemoryArtifactService()

# In-memory metadata store keyed by artifact version
artifact_metadata = {}
# Session index: (app_name,user_id,session_id) -> {version: {filename,...}}
_session_artifact_index = {}
# Track latest session per (app,user) for fallback resolution
_latest_session_for_user = {}

def record_artifact_metadata(version: str | int, metadata: dict):
    try:
        # Normalize version to string for consistent downstream matching
        v_str = str(version) if version is not None else None
        if v_str:
            artifact_metadata[v_str] = metadata
            app_name = metadata.get("app_name")
            user_id = metadata.get("user_id")
            session_id = metadata.get("session_id")
            filename = metadata.get("filename")
            if app_name and user_id and session_id:
                # update latest session pointer
                _latest_session_for_user[(app_name, user_id)] = session_id
            if app_name and user_id and session_id and filename:
                key = (app_name, user_id, session_id)
                bucket = _session_artifact_index.setdefault(key, {})
                bucket[v_str] = {
                    "version": v_str,
                    "filename": filename,
                    "mime_type": metadata.get("mime_type"),
                    "caption": metadata.get("caption"),
                    "auto_summary": metadata.get("auto_summary"),
                }
    except Exception as e:  # pragma: no cover
        logging.debug(f"record_artifact_metadata failed: {e}")

def get_artifact_metadata(version: str | int):
    return artifact_metadata.get(str(version))

async def list_session_artifacts(app_name: str, user_id: str, session_id: str):
    """Return artifact metadata entries for a session.

    Primary source is the enriched in-memory metadata index populated by record_artifact_metadata.
    Fallback: if that index is empty (e.g. artifacts created by another pathway), attempt to
    synthesize minimal entries from the raw artifact service keys so tools still surface them.
    """
    key = (app_name, user_id, session_id)
    # entries_dict = _session_artifact_index.get(key, {})
    # if entries_dict:
    #     items = list(entries_dict.values())
    #     logging.debug({
    #         "event": "list_session_artifacts:metadata_index_hit",
    #         "key": key,
    #         "count": len(items)
    #     })
    #     return items

    # # Fallback: interrogate artifact service directly
    try:
        raw_keys = await artifact_service.list_artifact_keys(app_name=app_name, user_id=user_id, session_id=session_id)  # type: ignore
        synthesized = []
        for rk in raw_keys or []:
            v_str = str(rk)
            meta = get_artifact_metadata(v_str) or {}
            synthesized.append({
                "version": v_str,
                "filename": meta.get("filename"),  # may be None if we never recorded metadata
                "mime_type": meta.get("mime_type"),
                "caption": meta.get("caption"),
                "auto_summary": meta.get("auto_summary"),
            })
        logging.debug({
            "event": "list_session_artifacts:fallback_raw_keys",
            "key": key,
            "raw_key_count": len(raw_keys or []),
        })
        return synthesized
    except Exception as e:
        logging.debug(f"list_session_artifacts fallback failed for {key}: {e}")
        return []

def find_session_artifacts_by_filenames(app_name: str, user_id: str, session_id: str, filenames: list[str]):
    key = (app_name, user_id, session_id)
    entries = _session_artifact_index.get(key, {})
    want = set(filenames)
    return [v for v in entries.values() if v.get("filename") in want]

def list_all_session_artifacts(app_name: str):
    """Return flattened list of all artifacts for given app across users & sessions.
    Each item: {app_name,user_id,session_id,version,filename,mime_type,caption,auto_summary}
    (Used for fallback resolution / debugging.)
    """
    results = []
    try:
        for (a, user_id, session_id), versions in _session_artifact_index.items():
            if a != app_name:
                continue
            for vinfo in versions.values():
                results.append({
                    "app_name": a,
                    "user_id": user_id,
                    "session_id": session_id,
                    **vinfo,
                })
    except Exception as e:  # pragma: no cover
        logging.debug(f"list_all_session_artifacts failed: {e}")
    return results

def get_latest_session_for_user(app_name: str, user_id: str):
    return _latest_session_for_user.get((app_name, user_id))

logging.info("Global InMemoryArtifactService initialized (artifact_service) with metadata & session index")

__all__ = [
    "artifact_service",
    "record_artifact_metadata",
    "get_artifact_metadata",
    "artifact_metadata",
    "list_session_artifacts",
    "find_session_artifacts_by_filenames",
    "list_all_session_artifacts",
    "get_latest_session_for_user",
]
