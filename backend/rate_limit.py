"""
Rate limiting helper using DynamoDB.

Implements daily rate limiting based on caller IP address.
Stores date + count in DynamoDB and provides quota checking.
"""

import os
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()

# Configuration from environment variables
TABLE_NAME = os.environ.get("RATE_LIMIT_TABLE", "requirements-evaluator-rate-limit")
DAILY_LIMIT = int(os.environ.get("DAILY_RATE_LIMIT", "50"))
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)


def get_today_date() -> str:
    """Get today's date in YYYY-MM-DD format (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def check_and_increment_quota(client_ip: str) -> tuple[bool, str]:
    """
    Check if the client has remaining quota and increment the counter.
    
    This function atomically checks and increments the request count for
    a given IP address. Uses DynamoDB conditional expressions to ensure
    thread-safe operation.
    
    Args:
        client_ip: The IP address of the client making the request
        
    Returns:
        Tuple of (allowed: bool, error_message: str)
        - If allowed is True, error_message is empty
        - If allowed is False, error_message contains the reason
    """
    # Skip rate limiting for unknown IPs or if disabled
    if client_ip == "unknown" or os.environ.get("SKIP_RATE_LIMIT") == "true":
        logger.debug(f"Rate limiting skipped for IP: {client_ip}")
        return True, ""
    
    today = get_today_date()
    pk = f"IP#{client_ip}"
    
    try:
        # Try to increment the counter atomically
        response = table.update_item(
            Key={"pk": pk},
            UpdateExpression="SET request_count = if_not_exists(request_count, :zero) + :inc, #date = :today",
            ConditionExpression="attribute_not_exists(#date) OR #date = :today",
            ExpressionAttributeNames={
                "#date": "date"
            },
            ExpressionAttributeValues={
                ":zero": 0,
                ":inc": 1,
                ":today": today
            },
            ReturnValues="UPDATED_NEW"
        )
        
        new_count = int(response["Attributes"]["request_count"])
        logger.info(f"Rate limit check for {client_ip}: {new_count}/{DAILY_LIMIT}")
        
        if new_count > DAILY_LIMIT:
            return False, f"Daily rate limit of {DAILY_LIMIT} requests exceeded. Please try again tomorrow."
        
        return True, ""
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        
        if error_code == "ConditionalCheckFailedException":
            # Date changed - reset the counter for the new day
            logger.info(f"New day detected for {client_ip}, resetting counter")
            return reset_counter_for_new_day(client_ip, today)
        
        # Log error but allow the request (fail open)
        logger.error(f"DynamoDB error during rate limit check: {str(e)}")
        return True, ""
        
    except Exception as e:
        # Log error but allow the request (fail open)
        logger.error(f"Unexpected error during rate limit check: {str(e)}")
        return True, ""


def reset_counter_for_new_day(client_ip: str, today: str) -> tuple[bool, str]:
    """
    Reset the counter for a new day.
    
    Args:
        client_ip: The IP address of the client
        today: Today's date string
        
    Returns:
        Tuple of (allowed: bool, error_message: str)
    """
    pk = f"IP#{client_ip}"
    
    try:
        table.put_item(
            Item={
                "pk": pk,
                "date": today,
                "request_count": 1
            }
        )
        logger.info(f"Counter reset for {client_ip} on {today}")
        return True, ""
        
    except Exception as e:
        logger.error(f"Error resetting counter: {str(e)}")
        # Fail open
        return True, ""


def get_current_usage(client_ip: str) -> dict:
    """
    Get the current usage statistics for a client IP.
    
    Args:
        client_ip: The IP address of the client
        
    Returns:
        Dictionary with usage information
    """
    pk = f"IP#{client_ip}"
    today = get_today_date()
    
    try:
        response = table.get_item(Key={"pk": pk})
        item = response.get("Item", {})
        
        # Check if the record is for today
        if item.get("date") == today:
            return {
                "ip": client_ip,
                "date": today,
                "requests_used": int(item.get("request_count", 0)),
                "requests_remaining": max(0, DAILY_LIMIT - int(item.get("request_count", 0))),
                "daily_limit": DAILY_LIMIT
            }
        else:
            # Record is from a previous day
            return {
                "ip": client_ip,
                "date": today,
                "requests_used": 0,
                "requests_remaining": DAILY_LIMIT,
                "daily_limit": DAILY_LIMIT
            }
            
    except Exception as e:
        logger.error(f"Error getting usage: {str(e)}")
        return {
            "ip": client_ip,
            "date": today,
            "requests_used": 0,
            "requests_remaining": DAILY_LIMIT,
            "daily_limit": DAILY_LIMIT,
            "error": "Could not retrieve usage data"
        }
