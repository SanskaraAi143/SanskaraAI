import logging
import os
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter.

    - Merges dict messages into the top-level payload.
    - Includes timestamp, level, logger, module, func, line.
    - Appends exc_info when present.
    - Carries along any extra attributes attached to the LogRecord.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }

        # Include message or merge dict payloads
        msg = record.msg
        if isinstance(msg, dict):
            try:
                payload.update(msg)
            except Exception:
                payload["message"] = str(msg)
        else:
            payload["message"] = record.getMessage()

        # Append exception info
        if record.exc_info:
            try:
                payload["exc"] = self.formatException(record.exc_info)
            except Exception:
                pass

        # Carry extra, non-standard attributes
        std_keys = {
            "name","msg","args","levelname","levelno","pathname","filename","module",
            "exc_info","exc_text","stack_info","lineno","funcName","created","msecs",
            "relativeCreated","thread","threadName","processName","process","stacklevel",
        }
        for k, v in record.__dict__.items():
            if k not in std_keys and not k.startswith("_") and k not in payload:
                try:
                    json.dumps(v)  # ensure serializable
                    payload[k] = v
                except Exception:
                    payload[k] = str(v)

        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str | None = None) -> None:
    """Configure root logging once with a consistent format.

    - Honors LOG_LEVEL env (DEBUG, INFO, WARNING, ERROR) if provided.
    - If handlers already exist, only adjusts levels to avoid duplicates.
    - Optional file logging via LOG_TO_FILE=1 and LOG_FILE (default: sanskara.log).
    - Also aligns common framework loggers (uvicorn) to the same level.
    """
    log_level = (level or os.getenv("LOG_LEVEL", "DEBUG")).upper()
    try:
        numeric_level = getattr(logging, log_level, logging.DEBUG)
    except Exception:
        numeric_level = logging.DEBUG

    root = logging.getLogger()

    json_formatter = JsonFormatter()

    if root.handlers:
        # Respect existing handlers but ensure levels and formatters are consistent
        root.setLevel(numeric_level)
        for h in root.handlers:
            try:
                h.setLevel(numeric_level)
                h.setFormatter(json_formatter)
            except Exception:
                pass
    else:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(numeric_level)
        stream_handler.setFormatter(json_formatter)
        root.addHandler(stream_handler)
        root.setLevel(numeric_level)

    # Optional file handler
    if os.getenv("LOG_TO_FILE", "1").lower() in {"1", "true", "yes"}:
        # Default to repo-root sanskara.log (one directory above this file)
        default_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sanskara.log"))
        log_file = os.getenv("LOG_FILE", default_path)
        try:
            file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(json_formatter)
            # Avoid adding duplicate file handlers for the same filename
            if not any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', None) == getattr(file_handler, 'baseFilename', None) for h in root.handlers):
                root.addHandler(file_handler)
        except Exception:
            # Fail open: continue without file logging
            pass

    # Align common framework loggers to the same level and formatter (useful under uvicorn)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        try:
            lg = logging.getLogger(name)
            lg.setLevel(numeric_level)
            for h in lg.handlers:
                try:
                    h.setLevel(numeric_level)
                    h.setFormatter(json_formatter)
                except Exception:
                    pass
        except Exception:
            pass
