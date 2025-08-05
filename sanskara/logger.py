import os
import sys
from loguru import logger
import json
# load environment variables from .env file if it exists
from dotenv import load_dotenv
load_dotenv()
class JsonLogger:
    def __init__(self):
        self.logger = logger
        self._configure_logger()

    def _configure_logger(self):
        self.logger.remove()  # Remove default handler

        # Determine log level from environment variable, default to INFO
        log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()

        # Add a new handler with human-readable format
        # Choose one of the formats below:
        
        # Option 1: Simple format
        # format_string = "{time} {level} {message}"
        
        # Option 2: Detailed format with file/function info
        format_string = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        
        # Option 3: Compact format
        # format_string = "{time:HH:mm:ss} | {level} | {message}"
        
        # Option 4: Colored format (works well in terminals that support colors)
        # format_string = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        
        self.logger.add(
            sys.stdout,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}", # Detailed human-readable format
            serialize=False,  # Disable JSON serialization
            enqueue=True # Use a queue for non-blocking logging
        )
        print(f"Logger initialized with level: {log_level} {os.getenv('LOG_TO_FILE')}")
        # Optionally, add a file handler for local debugging
        if os.getenv("LOG_TO_FILE", "false").lower() == "true":
            logger.debug("Logging to file is enabled.")
            log_file_path = os.getenv("LOG_FILE_PATH", "app.log")
            self.logger.add(
                log_file_path,
                level=log_level,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",  # Detailed human-readable format
                serialize=False,  # Disable JSON serialization
                rotation="10 MB",  # Rotate file after 10 MB
                compression="zip", # Compress old log files
                enqueue=True
            )

    def bind_context(self, **kwargs):
        """Bind context variables to the logger."""
        return self.logger.bind(**kwargs)

# Initialize the logger
json_logger = JsonLogger().logger