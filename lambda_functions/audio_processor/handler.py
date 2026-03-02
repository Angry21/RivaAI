"""Lambda function to process audio and orchestrate flow."""

import json
import logging
import os
from typing import Any, Dict

import boto3

from rivaai_common.utils import create_response, log_event

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
lambda_client = boto3.client("lambda", region_name=os.environ.get("AWS_REGION", "us-east-1"))
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))

# Environment variables
KNOWLEDGE_RETRIEVER_FUNCTION = os.environ.get("KNOWLEDGE_RETRIEVER_FUNCTION", "rivaai-knowledge-retriever")
RESPONSE_GENERATOR_FUNCTION = os.environ.get("RESPONSE_GENERATOR_FUNCTION", "rivaai-response-generator")
SPEECH_SYNTHESIZER_FUNCTION = os.environ.get("SPEECH_SYNTHESIZER_FUNCTION", "rivaai-speech-synthesizer")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "rivaai-sessions")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Process audio and orchestrate the flow.
    
    Args:
        event: Contains transcribed text from Transcribe
        context: Lambda context
        
    Returns:
        Response with audio or text
    """
    log_event(event, context)
    
    try:
        # Extract data
        body = json.loads(event.get("body", "{}"))
        session_id = body.get("session_id")
        transcribed_text = body.get("text", "")
        language_code = body.get("language_code", "hi-IN")
        
        logger.info(f"Processing: '{transcribed_text}' for session {session_id}")
        
        # Simple intent detection (keyword matching)
        needs_knowledge = check_needs_knowledge(transcribed_text)
        
        if needs_knowledge:
            # Path 1: Knowledge retrieval + RAG
            logger.info("Query needs knowledge retrieval")
            
            # Step 1: Retrieve knowledge
            knowledge_response = invoke_lambda(
                KNOWLEDGE_RETRIEVER_FUNCTION,
                {"query": transcribed_text, "language_code": language_code}
            )
            rag_context = knowledge_response.get("context", "")
            
            # Step 2: Generate response with RAG
            response_data = invoke_lambda(
                RESPONSE_GENERATOR_FUNCTION,
                {
                    "query": transcribed_text,
                    "rag_context": rag_context,
                    "language_code": language_code
                }
            )
        else:
            # Path 2: Direct response (no knowledge needed)
            logger.info("Direct response without knowledge retrieval")
            response_data = invoke_lambda(
                RESPONSE_GENERATOR_FUNCTION,
                {
                    "query": transcribed_text,
                    "rag_context": "",
                    "language_code": language_code
                }
            )
        
        response_text = response_data.get("response", "")
        
        # Step 3: Synthesize speech
        audio_response = invoke_lambda(
            SPEECH_SYNTHESIZER_FUNCTION,
            {"text": response_text, "language_code": language_code}
        )
        
        # Update session
        update_session(session_id, transcribed_text, response_text)
        
        return create_response(200, {
            "text": response_text,
            "audio": audio_response.get("audio"),
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}", exc_info=True)
        return create_response(500, {"error": str(e)})


def check_needs_knowledge(text: str) -> bool:
    """Check if query needs knowledge retrieval.
    
    Args:
        text: User query
        
    Returns:
        True if needs knowledge retrieval
    """
    # Simple keyword matching for MVP
    knowledge_keywords = [
        "wheat", "गेहूं", "खेती", "farming", "crop",
        "chemical", "fertilizer", "scheme", "योजना"
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in knowledge_keywords)


def invoke_lambda(function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke another Lambda function.
    
    Args:
        function_name: Lambda function name
        payload: Payload to send
        
    Returns:
        Response from Lambda
    """
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response["Payload"].read())
    return json.loads(result.get("body", "{}"))


def update_session(session_id: str, user_text: str, system_text: str) -> None:
    """Update session with conversation turn.
    
    Args:
        session_id: Session ID
        user_text: User's text
        system_text: System's response
    """
    table = dynamodb.Table(SESSIONS_TABLE)
    
    table.update_item(
        Key={"session_id": session_id},
        UpdateExpression="SET conversation_history = list_append(conversation_history, :turn)",
        ExpressionAttributeValues={
            ":turn": [
                {"role": "user", "text": user_text},
                {"role": "assistant", "text": system_text}
            ]
        }
    )
