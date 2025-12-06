"""
Lambda handler for AI Requirements Quality Evaluator.

Accepts POST requests with JSON { "requirementText": "..." },
validates input, checks rate limits, calls Amazon Bedrock (Claude 3 Haiku),
and returns structured evaluation results.
"""

import json
import logging
import time
from textwrap import dedent
from typing import Any, Dict, Tuple

import boto3
from botocore.exceptions import ClientError

from config import get_config, validate_response_schema
from logging_utils import StructuredLogger
from rate_limit import check_and_increment_quota

# Get configuration singleton
config = get_config()

# Configure structured JSON logging
base_logger = logging.getLogger()
base_logger.setLevel(config.log_level)
logger = StructuredLogger(base_logger)

# Initialize Bedrock client using configuration
bedrock_client = boto3.client(
    "bedrock-runtime",
    region_name=config.bedrock_region,
    config=boto3.session.Config(
        connect_timeout=config.bedrock_timeout,
        read_timeout=config.bedrock_timeout,
    )
)

# CORS headers for API Gateway responses
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json"
}


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create a properly formatted API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body)
    }


def validate_request(body: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate the incoming request body.
    
    Args:
        body: Parsed JSON body from the request
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not body:
        return False, "Request body is empty"
    
    if "requirementText" not in body:
        return False, "Missing required field: requirementText"
    
    requirement_text = body.get("requirementText", "")
    
    if not isinstance(requirement_text, str):
        return False, "requirementText must be a string"
    
    if len(requirement_text.strip()) == 0:
        return False, "requirementText cannot be empty"
    
    if len(requirement_text.strip()) < config.min_requirement_length:
        return False, f"requirementText must be at least {config.min_requirement_length} characters"
    
    if len(requirement_text) > config.max_requirement_length:
        return False, f"requirementText exceeds maximum length of {config.max_requirement_length} characters"
    
    return True, ""


def build_evaluation_prompt(requirement_text: str) -> str:
    """
    Build the prompt for Bedrock to evaluate the requirement.

    Args:
        requirement_text: The software requirement to evaluate

    Returns:
        Formatted prompt string
    """
    return dedent(
        f"""
        You are an expert software requirements analyst. Analyze the following
        software requirement and provide a structured evaluation.

        Requirement to evaluate:
        "{requirement_text}"

        Evaluate the requirement and respond with ONLY valid JSON in this exact format:
        {{
            "ambiguity_detected": true/false,
            "ambiguity_details": "explanation of any ambiguous terms or phrases, or 'None' if clear",
            "testable": true/false,
            "testability_details": "explanation of whether the requirement can be objectively tested",
            "completeness_score": 1-10,
            "completeness_details": "explanation of what information may be missing",
            "issues": ["list", "of", "specific", "issues"],
            "suggestions": ["list", "of", "improvement", "suggestions"]
        }}

        Important guidelines:
        - ambiguity_detected: true if the requirement contains vague, unclear, or subjective language
        - testable: true if the requirement has measurable, verifiable acceptance criteria
        - completeness_score: 1 (very incomplete) to 10 (fully complete)
        - Be specific and actionable in your feedback

        Respond with ONLY the JSON object, no additional text.
        """
    ).strip()


def call_bedrock(requirement_text: str) -> Dict[str, Any]:
    """
    Call Amazon Bedrock to evaluate the requirement.
    
    Args:
        requirement_text: The software requirement to evaluate
        
    Returns:
        Parsed evaluation results from Bedrock
        
    Raises:
        Exception: If Bedrock call fails or response cannot be parsed
    """
    start_time = time.time()
    prompt = build_evaluation_prompt(requirement_text)

    model_id = config.bedrock_model_id

    # Prepare request body depending on the selected model family
    if model_id.startswith("openai."):
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": config.model_temperature,
            "max_tokens": config.model_max_tokens,
        }
    else:
        # Default to Anthropic format
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": config.model_max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "temperature": config.model_temperature
        }

    logger.info(
        "Calling Bedrock model",
        model_id=model_id,
        temperature=config.model_temperature,
        max_tokens=config.model_max_tokens
    )

    try:
        response = bedrock_client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        duration = time.time() - start_time
        logger.info(
            "Bedrock call completed",
            model_id=model_id,
            duration_seconds=round(duration, 2)
        )

        # Parse response
        response_body = json.loads(response["body"].read())

        if model_id.startswith("openai."):
            # OpenAI models return choices[0].message.content (string or list)
            first_choice = response_body.get("choices", [{}])[0]
            message = first_choice.get("message", {})
            content = message.get("content", "")
            if isinstance(content, list):
                # concatenate text entries if provided as a list of content blocks
                content = "".join(block.get("text", "") for block in content if isinstance(block, dict))
        else:
            content = response_body.get("content", [{}])[0].get("text", "")

        logger.debug("Bedrock response received", content_length=len(content))
        
        # Parse the JSON from the response
        try:
            # Try to extract JSON from the response
            evaluation = json.loads(content)
            
            # Validate the response schema
            is_valid, error_msg = validate_response_schema(evaluation)
            if not is_valid:
                logger.warning(
                    "Schema validation failed",
                    model_id=model_id,
                    error=error_msg
                )
                # Continue with the response even if schema validation fails,
                # but log the issue for monitoring
            
            return evaluation
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse Bedrock response",
                model_id=model_id,
                error=str(e),
                content_preview=content[:200] if content else ""
            )
            # Return a default structure if parsing fails
            return {
                "ambiguity_detected": None,
                "ambiguity_details": "Failed to parse evaluation",
                "testable": None,
                "testability_details": "Failed to parse evaluation",
                "completeness_score": 0,
                "completeness_details": "Failed to parse evaluation",
                "issues": ["Evaluation parsing error"],
                "suggestions": ["Please try again"]
            }
    except ClientError as e:
        duration = time.time() - start_time
        logger.error(
            "Bedrock API error",
            model_id=model_id,
            duration_seconds=round(duration, 2),
            error_code=e.response.get("Error", {}).get("Code", "Unknown"),
            error_message=str(e)
        )
        raise
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "Unexpected error calling Bedrock",
            model_id=model_id,
            duration_seconds=round(duration, 2),
            error=str(e)
        )
        raise


def get_client_ip(event: Dict[str, Any]) -> str:
    """Extract client IP from the API Gateway event."""
    # Try requestContext first (API Gateway v1)
    request_context = event.get("requestContext", {})
    identity = request_context.get("identity", {})
    source_ip = identity.get("sourceIp")
    
    if source_ip:
        return source_ip
    
    # Try headers (X-Forwarded-For from CloudFront/ALB)
    headers = event.get("headers", {}) or {}
    forwarded_for = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for")
    
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    return "unknown"


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    request_id = (
        getattr(context, "aws_request_id", None)
        or getattr(context, "request_id", None)
        or "unknown"
    )
    start_time = time.time()
    
    logger.info(
        "Received request",
        request_id=request_id
    )
    
    # Handle both API Gateway v1 (REST API) and v2 (HTTP API) event formats
    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "")
    
    # Handle CORS preflight
    if http_method == "OPTIONS":
        return create_response(200, {"message": "OK"})
    
    # Only accept POST requests
    if http_method != "POST":
        logger.warning("Method not allowed", method=http_method, request_id=request_id)
        return create_response(405, {"error": "Method not allowed"})
    
    try:
        # Parse request body
        body_str = event.get("body", "")
        if not body_str:
            logger.warning("Empty request body", request_id=request_id)
            return create_response(400, {"error": "Request body is required"})
        
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in request", request_id=request_id, error=str(e))
            return create_response(400, {"error": "Invalid JSON in request body"})
        
        # Validate request
        is_valid, error_msg = validate_request(body)
        if not is_valid:
            logger.warning(
                "Request validation failed",
                request_id=request_id,
                error=error_msg
            )
            return create_response(400, {"error": error_msg})
        
        # Check rate limit
        client_ip = get_client_ip(event)
        allowed, rate_error = check_and_increment_quota(client_ip)
        
        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                request_id=request_id,
                client_ip=client_ip
            )
            return create_response(429, {"error": rate_error})
        
        # Call Bedrock for evaluation
        requirement_text = body["requirementText"].strip()
        logger.info(
            "Evaluating requirement",
            request_id=request_id,
            client_ip=client_ip,
            requirement_length=len(requirement_text)
        )
        
        evaluation = call_bedrock(requirement_text)
        
        duration = time.time() - start_time
        logger.info(
            "Request completed successfully",
            request_id=request_id,
            total_duration_seconds=round(duration, 2)
        )
        return create_response(200, evaluation)
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        duration = time.time() - start_time
        logger.error(
            "AWS service error",
            request_id=request_id,
            error_code=error_code,
            error_message=str(e),
            duration_seconds=round(duration, 2)
        )
        return create_response(500, {"error": f"AWS service error: {error_code}"})
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "Unexpected error",
            request_id=request_id,
            error=str(e),
            error_type=type(e).__name__,
            duration_seconds=round(duration, 2),
            exc_info=True
        )
        return create_response(500, {"error": "Internal server error"})
