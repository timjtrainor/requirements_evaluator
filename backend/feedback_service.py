"""
Feedback service module.

Handles storage of user feedback in DynamoDB.
"""

import logging
import os
import time
import uuid
from typing import Any, Dict, Tuple

import boto3
from botocore.exceptions import ClientError

from config import get_config
from logging_utils import StructuredLogger

# Get configuration
config = get_config()

# Configure structured logging
base_logger = logging.getLogger()
logger = StructuredLogger(base_logger)

# Configuration
TABLE_NAME = config.feedback_table_name or os.environ.get(
    "FEEDBACK_TABLE", "requirements-evaluator-feedback"
)
AWS_REGION = config.bedrock_region

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)


def save_feedback(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Save user feedback to DynamoDB.

    Args:
        data: Dictionary containing feedback details
              Expected keys:
              - helpful (bool): Whether the result was helpful
              - timestamp (int): Client-side timestamp
              - requirementText (str): The text evaluated
              - comments (str, optional): User comments (e.g., why it wasn't helpful)
              - client_ip (str, optional): IP of the submitter

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    feedback_id = str(uuid.uuid4())

    # Prepare item
    item = {
        "feedback_id": feedback_id,
        "helpful": data.get("helpful", False),
        "timestamp": data.get("timestamp"),
        "requirement_text": data.get("requirementText", ""),
        "comments": data.get("comments", ""),
        "client_ip": data.get("client_ip", "unknown"),
        "created_at": int(time.time()),  # Server timestamp in seconds
    }

    try:
        table.put_item(Item=item)
        logger.info("Feedback saved", feedback_id=feedback_id, helpful=item["helpful"])
        return True, ""
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error("DynamoDB error saving feedback", error_code=error_code, error=str(e))
        return False, f"Database error: {error_code}"
    except Exception as e:
        logger.error("Unexpected error saving feedback", error=str(e))
        return False, "Internal server error"
