"""Common utilities for Lambda functions."""

import hashlib
import json
import logging
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def hash_phone_number(phone_number: str) -> str:
    """Hash phone number for privacy.
    
    Args:
        phone_number: Phone number to hash
        
    Returns:
        SHA-256 hash
    """
    return hashlib.sha256(phone_number.encode()).hexdigest()


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create API Gateway response.
    
    Args:
        status_code: HTTP status code
        body: Response body
        
    Returns:
        API Gateway response format
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def log_event(event: Dict[str, Any], context: Any) -> None:
    """Log Lambda event for debugging.
    
    Args:
        event: Lambda event
        context: Lambda context
    """
    logger.info(f"Function: {context.function_name}")
    logger.info(f"Request ID: {context.request_id}")
    logger.info(f"Event: {json.dumps(event)}")
