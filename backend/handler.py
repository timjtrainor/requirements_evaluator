"""
Lambda handler for AI Requirements Quality Evaluator.

Accepts POST requests with JSON { "requirementText": "..." },
validates input, checks rate limits, calls Amazon Bedrock (Claude 3 Haiku),
and returns structured evaluation results.
"""

import json
import logging
from textwrap import dedent
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import Config, validate_response_schema
from rate_limit import check_and_increment_quota

# Configure logging
logger = logging.getLogger()
logger.setLevel(Config.get_log_level())

# Initialize Bedrock client using configuration
bedrock_client = boto3.client("bedrock-runtime", region_name=Config.get_bedrock_region())

# CORS headers for API Gateway responses
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json"
}


def create_response(status_code: int, body: dict) -> dict:
    """Create a properly formatted API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body)
    }


def validate_request(body: dict) -> tuple[bool, str]:
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
    
    if len(requirement_text.strip()) < 10:
        return False, "requirementText must be at least 10 characters"
    
    if len(requirement_text) > 5000:
        return False, "requirementText exceeds maximum length of 5000 characters"
    
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


def call_bedrock(requirement_text: str) -> dict:
    """
    Call Amazon Bedrock to evaluate the requirement.
    
    Args:
        requirement_text: The software requirement to evaluate
        
    Returns:
        Parsed evaluation results from Bedrock
        
    Raises:
        Exception: If Bedrock call fails or response cannot be parsed
    """
    prompt = build_evaluation_prompt(requirement_text)

    model_id = Config.get_model_id()

    # Prepare request body depending on the selected model family
    if model_id.startswith("openai."):
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,
            "max_tokens": 1024,
        }
    else:
        # Default to Anthropic format
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
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
            "temperature": 0.2  # Low temperature for consistent evaluations
        }

    logger.info(f"Calling Bedrock model: {model_id}")

    response = bedrock_client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body)
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

    logger.debug(f"Bedrock response content: {content}")
    
    # Parse the JSON from the response
    try:
        # Try to extract JSON from the response
        evaluation = json.loads(content)
        
        # Validate the response schema
        is_valid, error_msg = validate_response_schema(evaluation)
        if not is_valid:
            logger.warning(f"Schema validation failed: {error_msg}")
            # Continue with the response even if schema validation fails,
            # but log the issue for monitoring
        
        return evaluation
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Bedrock response as JSON: {e}")
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


def get_client_ip(event: dict) -> str:
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


def handler(event: dict, context: Any) -> dict:
    """
    Main Lambda handler function.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Handle both API Gateway v1 (REST API) and v2 (HTTP API) event formats
    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "")
    
    # Handle CORS preflight
    if http_method == "OPTIONS":
        return create_response(200, {"message": "OK"})
    
    # Only accept POST requests
    if http_method != "POST":
        return create_response(405, {"error": "Method not allowed"})
    
    try:
        # Parse request body
        body_str = event.get("body", "")
        if not body_str:
            return create_response(400, {"error": "Request body is required"})
        
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError:
            return create_response(400, {"error": "Invalid JSON in request body"})
        
        # Validate request
        is_valid, error_msg = validate_request(body)
        if not is_valid:
            logger.warning(f"Validation failed: {error_msg}")
            return create_response(400, {"error": error_msg})
        
        # Check rate limit
        client_ip = get_client_ip(event)
        allowed, rate_error = check_and_increment_quota(client_ip)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return create_response(429, {"error": rate_error})
        
        # Call Bedrock for evaluation
        requirement_text = body["requirementText"].strip()
        logger.info(f"Evaluating requirement: {requirement_text[:100]}...")
        
        evaluation = call_bedrock(requirement_text)
        
        logger.info("Evaluation completed successfully")
        return create_response(200, evaluation)
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(f"AWS ClientError: {error_code} - {str(e)}")
        return create_response(500, {"error": f"AWS service error: {error_code}"})
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error"})
