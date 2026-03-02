"""Lambda function to handle incoming calls."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

import boto3

# Import from Lambda layer
from rivaai_common.utils import create_response, hash_phone_number, log_event

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
lambda_client = boto3.client("lambda", region_name=os.environ.get("AWS_REGION", "us-east-1"))

# Environment variables
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "rivaai-sessions")
AUDIO_PROCESSOR_FUNCTION = os.environ.get("AUDIO_PROCESSOR_FUNCTION", "rivaai-audio-processor")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle incoming call webhook.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    log_event(event, context)
    
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        caller_number = body.get("From", "unknown")
        call_sid = body.get("CallSid", f"call-{datetime.now().timestamp()}")
        
        logger.info(f"Incoming call from {caller_number}, SID: {call_sid}")
        
        # Create session in DynamoDB
        session_id = create_session(call_sid, caller_number)
        
        # Return response to telephony provider
        response_body = {
            "message": "Call accepted",
            "session_id": session_id,
            "call_sid": call_sid,
        }
        
        # For Exotel/Twilio, return TwiML
        if "Exotel" in event.get("headers", {}).get("User-Agent", ""):
            twiml_response = generate_twiml_response()
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/xml"},
                "body": twiml_response,
            }
        
        return create_response(200, response_body)
        
    except Exception as e:
        logger.error(f"Error handling call: {str(e)}", exc_info=True)
        return create_response(500, {"error": str(e)})


def create_session(call_sid: str, caller_number: str) -> str:
    """Create session in DynamoDB.
    
    Args:
        call_sid: Call SID
        caller_number: Caller's phone number
        
    Returns:
        Session ID
    """
    table = dynamodb.Table(SESSIONS_TABLE)
    
    session_id = f"session-{call_sid}"
    timestamp = int(datetime.now().timestamp())
    ttl = timestamp + (24 * 60 * 60)  # 24 hours
    
    item = {
        "session_id": session_id,
        "call_sid": call_sid,
        "caller_number_hash": hash_phone_number(caller_number),
        "language_code": "hi-IN",  # Default to Hindi
        "conversation_history": [],
        "created_at": timestamp,
        "ttl": ttl,
        "status": "active",
    }
    
    table.put_item(Item=item)
    logger.info(f"Created session: {session_id}")
    
    return session_id


def generate_twiml_response() -> str:
    """Generate TwiML response for telephony provider.
    
    Returns:
        TwiML XML string
    """
    return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi" language="hi-IN">नमस्ते। मैं आपकी कैसे मदद कर सकता हूं?</Say>
    <Gather input="speech" language="hi-IN" speechTimeout="3" action="/api/process-speech">
        <Say voice="Polly.Aditi" language="hi-IN">कृपया अपना सवाल पूछें।</Say>
    </Gather>
</Response>"""
