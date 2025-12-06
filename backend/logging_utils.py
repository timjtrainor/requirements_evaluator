"""
Structured logging utilities for the AI Requirements Quality Evaluator.

Provides structured JSON logging capabilities for better observability
in CloudWatch and other log aggregation systems.
"""

import json
import logging
import time
from typing import Any, Dict


class StructuredLogger:
    """Structured JSON logger for better observability."""
    
    def __init__(self, logger: logging.Logger) -> None:
        """
        Initialize structured logger.
        
        Args:
            logger: Standard Python logger instance
        """
        self.logger = logger
    
    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        """
        Log a structured JSON message.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            **kwargs: Additional context fields to include in log
        """
        log_data: Dict[str, Any] = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.logger.log(
            getattr(logging, level),
            json.dumps(log_data)
        )
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log("CRITICAL", message, **kwargs)
