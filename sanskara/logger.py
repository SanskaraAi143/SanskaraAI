import os
import sys
from loguru import logger
import json

class JsonLogger:
    def __init__(self):
        self.logger = logger
        self._configure_logger()

    def _configure_logger(self):
        self.logger.remove()  # Remove default handler

        # Determine log level from environment variable, default to INFO
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        # Add a new handler with JSON format
        self.logger.add(
            sys.stdout,
            level=log_level,
            format="{message}",
            serialize=True,
            enqueue=True # Use a queue for non-blocking logging
        )

        # Optionally, add a file handler for local debugging
        if os.getenv("LOG_TO_FILE", "false").lower() == "true":
            log_file_path = os.getenv("LOG_FILE_PATH", "app.log")
            self.logger.add(
                log_file_path,
                level=log_level,
                format="{message}",
                serialize=True,
                rotation="10 MB",  # Rotate file after 10 MB
                compression="zip", # Compress old log files
                enqueue=True
            )

    def bind_context(self, **kwargs):
        """Bind context variables to the logger."""
        return self.logger.bind(**kwargs)

# Initialize the logger
json_logger = JsonLogger().logger