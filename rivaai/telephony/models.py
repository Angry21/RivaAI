"""Data models for telephony components."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class CallStatus(Enum):
    """Call status enumeration."""

    RINGING = "ringing"
    ANSWERED = "answered"
    IN_PROGRESS = "in_progress"
    ENDED = "ended"
    FAILED = "failed"


class AudioDirection(Enum):
    """Audio direction enumeration."""

    INCOMING = "incoming"  # User to system
    OUTGOING = "outgoing"  # System to user


@dataclass
class CallSession:
    """Represents an active call session."""

    call_sid: str
    caller_ani_hash: str
    session_id: str
    websocket_url: str
    status: CallStatus
    started_at: datetime
    ended_at: Optional[datetime] = None


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection for audio streaming."""

    call_sid: str
    websocket_url: str
    audio_format: str  # e.g., "mulaw"
    sample_rate: int  # e.g., 8000
    frame_size_ms: int  # e.g., 20
    is_connected: bool = False


@dataclass
class AudioChunk:
    """Represents an audio chunk for streaming."""

    call_sid: str
    audio_data: bytes  # μ-law PCM
    timestamp: float
    sequence_number: int
    direction: AudioDirection
