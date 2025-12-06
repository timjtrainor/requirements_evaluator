"""
Configuration module for AI Requirements Quality Evaluator.

This module provides a single source of truth for all configuration values,
including the Bedrock model selection. The application is designed to be
model-agnostic and can work with different Bedrock models.

Uses Pydantic for configuration validation with fail-fast behavior.
"""

import json
import os
import sys
from typing import List, Optional, Tuple

import boto3
from pydantic import BaseModel, Field, field_validator, ValidationError
from pydantic_settings import BaseSettings


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


class Config(BaseSettings):
    """
    Centralized configuration for the Requirements Evaluator.
    
    All configuration values are validated using Pydantic. Invalid configuration
    will cause the application to fail fast at startup with clear error messages.
    
    All configuration values should be accessed through the singleton instance
    to ensure consistency across the application.
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
    bedrock_model_id: str = Field(
        default="openai.gpt-oss-120b-1:0",
        description="Amazon Bedrock model ID for evaluations"
    )
    
    bedrock_region: str = Field(
        default="us-east-1",
        description="AWS region for Bedrock API calls"
    )
    
    bedrock_timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Bedrock API call timeout in seconds"
    )
    
    # Rate Limiting Configuration
    rate_limit_table: str = Field(
        default="",
        description="DynamoDB table name for rate limiting"
    )
    
    daily_rate_limit: int = Field(
        default=50,
        ge=1,
        le=10000,
        description="Maximum requests per IP per day"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Model Parameters
    model_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Model temperature for consistent evaluations"
    )
    
    model_max_tokens: int = Field(
        default=1024,
        ge=256,
        le=4096,
        description="Maximum tokens in model response"
    )
    
    # Input Validation
    min_requirement_length: int = Field(
        default=10,
        ge=1,
        description="Minimum requirement text length"
    )
    
    max_requirement_length: int = Field(
        default=5000,
        ge=100,
        description="Maximum requirement text length"
    )
    
    # Completeness Score Validation
    completeness_score_min: int = Field(
        default=1,
        ge=1,
        description="Minimum valid completeness score"
    )
    
    completeness_score_max: int = Field(
        default=10,
        le=10,
        description="Maximum valid completeness score"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that log level is one of the accepted values."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}, got '{v}'")
        return v_upper
    
    @field_validator("bedrock_region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Validate AWS region format."""
        if not v or len(v) < 3:
            raise ValueError(f"bedrock_region appears invalid: '{v}'")
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
    
    # Backward compatibility methods
    @classmethod
    def get_model_id(cls) -> str:
        """Get the configured Bedrock model ID."""
        return get_config().bedrock_model_id
    
    @classmethod
    def get_bedrock_region(cls) -> str:
        """Get the configured Bedrock region."""
        return get_config().bedrock_region
    
    @classmethod
    def get_rate_limit_table(cls) -> str:
        """Get the DynamoDB table name for rate limiting."""
        return get_config().rate_limit_table
    
    @classmethod
    def get_daily_rate_limit(cls) -> int:
        """Get the daily rate limit per IP."""
        return get_config().daily_rate_limit
    
    @classmethod
    def get_log_level(cls) -> str:
        """Get the logging level."""
        return get_config().log_level


# Pydantic model for Bedrock response validation
class EvaluationResponse(BaseModel):
    """
    Schema for the expected response from Bedrock evaluation.
    
    This Pydantic model provides strong typing and validation for the
    AI model response, ensuring data integrity throughout the application.
    """
    
    ambiguity_detected: bool = Field(
        description="Whether ambiguous language was detected"
    )
    ambiguity_details: str = Field(
        description="Explanation of ambiguous terms or 'None' if clear"
    )
    testable: bool = Field(
        description="Whether the requirement is objectively testable"
    )
    testability_details: str = Field(
        description="Explanation of testability assessment"
    )
    completeness_score: int = Field(
        ge=1,
        le=10,
        description="Completeness score from 1 (incomplete) to 10 (complete)"
    )
    completeness_details: str = Field(
        description="Explanation of what information may be missing"
    )
    issues: List[str] = Field(
        default_factory=list,
        description="List of specific issues found"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="List of improvement suggestions"
    )
    
    model_config = {
        "extra": "forbid",  # Reject any extra fields
    }


# Singleton instance of configuration
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get the singleton configuration instance.
    
    The configuration is loaded and validated once at first access.
    Invalid configuration will cause the application to fail fast.
    
    Returns:
        Config: The validated configuration instance
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    global _config_instance
    if _config_instance is None:
        try:
            _config_instance = Config()
        except ValidationError as e:
            error_msg = f"Configuration validation failed: {e}"
            # For Lambda environment, print to stderr and exit
            # In other contexts, raise exception for proper handling
            if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
                print(error_msg, file=sys.stderr)
                sys.exit(1)
            else:
                raise ConfigurationError(error_msg) from e
    return _config_instance


def validate_response_schema(response: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate that a Bedrock response matches the expected schema using Pydantic.

    Args:
        response: The parsed response from Bedrock

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Use Pydantic model for validation
        EvaluationResponse(**response)
        return True, None
    except Exception as e:
        return False, str(e)


def get_secret(secret_name: str, region_name: str = "us-east-1") -> Optional[dict]:
    """
    Retrieve a secret from AWS Secrets Manager.

    Args:
        secret_name: Name or ARN of the secret
        region_name: AWS region where the secret is stored

    Returns:
        Dictionary containing the secret values, or None if retrieval fails

    Example:
        secrets = get_secret("prod/api-keys")
        api_key = secrets.get("api_key") if secrets else None
    """
    try:
        client = boto3.client("secretsmanager", region_name=region_name)
        response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in response:
            return json.loads(response["SecretString"])
        else:
            # Binary secrets are not supported in this implementation
            return None
    except Exception as e:
        # Log error but don't fail - allow fallback to environment variables
        print(f"Warning: Failed to retrieve secret '{secret_name}': {e}", file=sys.stderr)
        return None


def get_parameter(parameter_name: str, region_name: str = "us-east-1", with_decryption: bool = True) -> Optional[str]:
    """
    Retrieve a parameter from AWS Systems Manager Parameter Store.

    Args:
        parameter_name: Name of the parameter
        region_name: AWS region where the parameter is stored
        with_decryption: Whether to decrypt the parameter value

    Returns:
        Parameter value as string, or None if retrieval fails

    Example:
        value = get_parameter("/prod/config/rate-limit")
    """
    try:
        client = boto3.client("ssm", region_name=region_name)
        response = client.get_parameter(
            Name=parameter_name,
            WithDecryption=with_decryption
        )
        return response["Parameter"]["Value"]
    except Exception as e:
        # Log error but don't fail - allow fallback to environment variables
        print(f"Warning: Failed to retrieve parameter '{parameter_name}': {e}", file=sys.stderr)
        return None
