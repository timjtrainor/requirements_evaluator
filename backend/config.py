"""
Configuration module for AI Requirements Quality Evaluator.

This module provides a single source of truth for all configuration values,
including the Bedrock model selection. The application is designed to be
model-agnostic and can work with different Bedrock models.
"""

import os
from typing import Optional


class Config:
    """
    Centralized configuration for the Requirements Evaluator.
    
    All configuration values should be accessed through this class to ensure
    consistency across the application.
    """
    
    # Bedrock Model Configuration
    # The default model can be overridden via the BEDROCK_MODEL_ID environment variable.
    # Default: openai.gpt-oss-120b-1:0
    # 
    # Other supported models include:
    # - anthropic.claude-3-haiku-20240307-v1:0
    # - anthropic.claude-3-sonnet-20240229-v1:0
    # - anthropic.claude-3-opus-20240229-v1:0
    # - Other OpenAI and foundation models available in Bedrock
    BEDROCK_MODEL_ID: str = os.environ.get(
        "BEDROCK_MODEL_ID", 
        "openai.gpt-oss-120b-1:0"
    )
    
    BEDROCK_REGION: str = os.environ.get("BEDROCK_REGION", "us-east-1")
    
    # Rate Limiting Configuration
    RATE_LIMIT_TABLE: str = os.environ.get("RATE_LIMIT_TABLE", "")
    DAILY_RATE_LIMIT: int = int(os.environ.get("DAILY_RATE_LIMIT", "50"))
    
    # Logging Configuration
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    
    # Model Response Schema - Used for validation
    EXPECTED_RESPONSE_SCHEMA = {
        "type": "object",
        "required": [
            "ambiguity_detected",
            "ambiguity_details",
            "testable",
            "testability_details",
            "completeness_score",
            "completeness_details",
            "issues",
            "suggestions"
        ],
        "properties": {
            "ambiguity_detected": {"type": "boolean"},
            "ambiguity_details": {"type": "string"},
            "testable": {"type": "boolean"},
            "testability_details": {"type": "string"},
            "completeness_score": {"type": "integer", "minimum": 1, "maximum": 10},
            "completeness_details": {"type": "string"},
            "issues": {
                "type": "array",
                "items": {"type": "string"}
            },
            "suggestions": {
                "type": "array",
                "items": {"type": "string"}
            }
        }
    }
    
    @classmethod
    def get_model_id(cls) -> str:
        """Get the configured Bedrock model ID."""
        return cls.BEDROCK_MODEL_ID
    
    @classmethod
    def get_bedrock_region(cls) -> str:
        """Get the configured Bedrock region."""
        return cls.BEDROCK_REGION
    
    @classmethod
    def get_rate_limit_table(cls) -> str:
        """Get the DynamoDB table name for rate limiting."""
        return cls.RATE_LIMIT_TABLE
    
    @classmethod
    def get_daily_rate_limit(cls) -> int:
        """Get the daily rate limit per IP."""
        return cls.DAILY_RATE_LIMIT
    
    @classmethod
    def get_log_level(cls) -> str:
        """Get the logging level."""
        return cls.LOG_LEVEL


def validate_response_schema(response: dict) -> tuple[bool, Optional[str]]:
    """
    Validate that a Bedrock response matches the expected schema.
    
    Args:
        response: The parsed response from Bedrock
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    schema = Config.EXPECTED_RESPONSE_SCHEMA
    
    # Check required fields
    for field in schema["required"]:
        if field not in response:
            return False, f"Missing required field: {field}"
    
    # Check field types
    for field, spec in schema["properties"].items():
        if field not in response:
            continue
            
        value = response[field]
        expected_type = spec["type"]
        
        # Type checking
        if expected_type == "boolean" and not isinstance(value, bool):
            return False, f"Field '{field}' must be boolean, got {type(value).__name__}"
        elif expected_type == "string" and not isinstance(value, str):
            return False, f"Field '{field}' must be string, got {type(value).__name__}"
        elif expected_type == "integer" and not isinstance(value, int):
            return False, f"Field '{field}' must be integer, got {type(value).__name__}"
        elif expected_type == "array" and not isinstance(value, list):
            return False, f"Field '{field}' must be array, got {type(value).__name__}"
        
        # Additional validations
        if expected_type == "integer":
            min_val = spec.get("minimum")
            max_val = spec.get("maximum")
            if min_val is not None and value < min_val:
                return False, f"Field '{field}' must be >= {min_val}, got {value}"
            if max_val is not None and value > max_val:
                return False, f"Field '{field}' must be <= {max_val}, got {value}"
        
        if expected_type == "array":
            items_spec = spec.get("items", {})
            items_type = items_spec.get("type")
            if items_type == "string":
                for i, item in enumerate(value):
                    if not isinstance(item, str):
                        return False, f"Field '{field}[{i}]' must be string, got {type(item).__name__}"
    
    return True, None
