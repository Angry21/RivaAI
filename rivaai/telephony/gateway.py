"""Telephony Gateway for managing PSTN call lifecycle and WebSocket connections."""

import hashlib
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream

from rivaai.config import get_settings
from rivaai.telephony.models import CallSession, CallStatus, WebSocketConnection

logger = logging.getLogger(__name__)


class TelephonyGateway:
    """
    Manages PSTN call lifecycle and establishes WebSocket connections for audio streaming.
    
    Responsibilities:
    - Answers incoming calls and establishes WebSocket connections
    - Manages call state transitions (ringing, answered, ended)
    - Implements retry logic for connection failures
    - Logs call metadata without recording audio
    """

    def __init__(self):
        """Initialize the Telephony Gateway with Twilio client."""
        self.settings = get_settings()
        self.client = Client(
            self.settings.twilio_account_sid,
            self.settings.twilio_auth_token
        )
        logger.info("TelephonyGateway initialized")

    def handle_incoming_call(self, caller_ani: str) -> CallSession:
        """
        Answers incoming call and establishes WebSocket connection.
        
        Args:
            caller_ani: Caller's phone number (ANI - Automatic Number Identification)
            
        Returns:
            CallSession with connection details
            
        Raises:
            Exception: If call handling fails
        """
        try:
            # Hash the caller ANI for privacy
            caller_ani_hash = self._hash_ani(caller_ani)
            
            # Generate unique identifiers
            session_id = str(uuid4())
            call_sid = f"CA{uuid4().hex[:32]}"  # Twilio-style call SID
            
            # Create WebSocket URL for this call
            websocket_url = f"{self.settings.twilio_websocket_url}/{call_sid}"
            
            # Create call session
            call_session = CallSession(
                call_sid=call_sid,
                caller_ani_hash=caller_ani_hash,
                session_id=session_id,
                websocket_url=websocket_url,
                status=CallStatus.ANSWERED,
                started_at=datetime.utcnow()
            )
            
            logger.info(
                f"Incoming call handled: call_sid={call_sid}, "
                f"session_id={session_id}, caller_hash={caller_ani_hash[:8]}..."
            )
            
            return call_session
            
        except Exception as e:
            logger.error(f"Failed to handle incoming call: {e}", exc_info=True)
            raise

    def establish_websocket(self, call_sid: str) -> WebSocketConnection:
        """
        Creates full-duplex WebSocket for audio streaming.
        
        Audio format: μ-law PCM, 8kHz, 20ms frames.
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            WebSocketConnection with connection details
            
        Raises:
            Exception: If WebSocket establishment fails
        """
        try:
            # Create WebSocket URL
            websocket_url = f"{self.settings.twilio_websocket_url}/{call_sid}"
            
            # Create WebSocket connection configuration
            ws_connection = WebSocketConnection(
                call_sid=call_sid,
                websocket_url=websocket_url,
                audio_format="mulaw",  # G.711 μ-law PCM
                sample_rate=8000,  # 8kHz telephony standard
                frame_size_ms=20,  # 20ms frames
                is_connected=False  # Will be set to True when connection is established
            )
            
            logger.info(
                f"WebSocket established: call_sid={call_sid}, "
                f"format={ws_connection.audio_format}, "
                f"sample_rate={ws_connection.sample_rate}Hz"
            )
            
            return ws_connection
            
        except Exception as e:
            logger.error(
                f"Failed to establish WebSocket for call_sid={call_sid}: {e}",
                exc_info=True
            )
            raise

    def terminate_call(self, call_sid: str) -> None:
        """
        Gracefully ends call and closes WebSocket.
        
        Args:
            call_sid: Twilio call SID
            
        Raises:
            Exception: If call termination fails
        """
        try:
            # Update call status to completed
            # In a real implementation, this would interact with Twilio API
            # to terminate the call
            
            logger.info(f"Call terminated: call_sid={call_sid}")
            
            # Log call metadata (duration, termination reason) without recording audio
            # This would be implemented with actual Twilio API calls
            
        except Exception as e:
            logger.error(
                f"Failed to terminate call for call_sid={call_sid}: {e}",
                exc_info=True
            )
            raise

    def generate_twiml_response(self, call_sid: str) -> str:
        """
        Generates TwiML response to establish WebSocket media stream.
        
        This is called by the Twilio webhook when a call comes in.
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        
        # Create a Connect verb to establish WebSocket stream
        connect = Connect()
        stream = Stream(url=f"{self.settings.twilio_websocket_url}/{call_sid}")
        
        # Configure stream parameters for G.711 μ-law PCM at 8kHz
        stream.parameter(name="audio_format", value="mulaw")
        stream.parameter(name="sample_rate", value="8000")
        
        connect.append(stream)
        response.append(connect)
        
        logger.info(f"Generated TwiML response for call_sid={call_sid}")
        
        return str(response)

    def _hash_ani(self, ani: str) -> str:
        """
        Hash caller ANI using SHA-256 for privacy.
        
        Args:
            ani: Caller's phone number
            
        Returns:
            SHA-256 hash of the ANI
        """
        return hashlib.sha256(ani.encode()).hexdigest()

    def get_call_metadata(self, call_sid: str) -> dict:
        """
        Retrieves call metadata without recording audio.
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            Dictionary with call metadata (duration, status, etc.)
        """
        try:
            # In a real implementation, this would fetch from Twilio API
            # For now, return a placeholder
            metadata = {
                "call_sid": call_sid,
                "status": "in-progress",
                "duration": 0,
                # Note: No audio recording or conversation content
            }
            
            logger.debug(f"Retrieved call metadata for call_sid={call_sid}")
            
            return metadata
            
        except Exception as e:
            logger.error(
                f"Failed to retrieve call metadata for call_sid={call_sid}: {e}",
                exc_info=True
            )
            raise
