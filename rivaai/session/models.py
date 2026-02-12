"""Data models for session management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List


class Speaker(Enum):
    """Speaker enumeration for conversation turns."""

    USER = "user"
    SYSTEM = "system"


@dataclass
class Entity:
    """Represents an extracted entity from conversation."""

    entity_type: str  # "crop", "chemical", "scheme", "amount"
    value: str
    confidence: float
    requires_semantic_validation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Turn:
    """Represents a single conversation turn."""

    speaker: Speaker
    text: str  # PII masked
    timestamp: datetime
    entities: List[Entity] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionContext:
    """Represents the complete session context."""

    session_id: str
    caller_ani_hash: str  # Hashed, not plaintext
    conversation_history: List[Turn]
    extracted_entities: List[Entity]
    domain: str
    language_code: str
    created_at: datetime
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session context to dictionary for storage.

        Returns:
            Dictionary representation of session context
        """
        return {
            "session_id": self.session_id,
            "caller_ani_hash": self.caller_ani_hash,
            "conversation_history": [
                {
                    "speaker": turn.speaker.value,
                    "text": turn.text,
                    "timestamp": turn.timestamp.isoformat(),
                    "entities": [
                        {
                            "entity_type": e.entity_type,
                            "value": e.value,
                            "confidence": e.confidence,
                            "requires_semantic_validation": e.requires_semantic_validation,
                            "metadata": e.metadata,
                        }
                        for e in turn.entities
                    ],
                    "metadata": turn.metadata,
                }
                for turn in self.conversation_history
            ],
            "extracted_entities": [
                {
                    "entity_type": e.entity_type,
                    "value": e.value,
                    "confidence": e.confidence,
                    "requires_semantic_validation": e.requires_semantic_validation,
                    "metadata": e.metadata,
                }
                for e in self.extracted_entities
            ],
            "domain": self.domain,
            "language_code": self.language_code,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionContext":
        """Create session context from dictionary.

        Args:
            data: Dictionary representation of session context

        Returns:
            SessionContext instance
        """
        return cls(
            session_id=data["session_id"],
            caller_ani_hash=data["caller_ani_hash"],
            conversation_history=[
                Turn(
                    speaker=Speaker(turn["speaker"]),
                    text=turn["text"],
                    timestamp=datetime.fromisoformat(turn["timestamp"]),
                    entities=[
                        Entity(
                            entity_type=e["entity_type"],
                            value=e["value"],
                            confidence=e["confidence"],
                            requires_semantic_validation=e.get(
                                "requires_semantic_validation", False
                            ),
                            metadata=e.get("metadata", {}),
                        )
                        for e in turn.get("entities", [])
                    ],
                    metadata=turn.get("metadata", {}),
                )
                for turn in data["conversation_history"]
            ],
            extracted_entities=[
                Entity(
                    entity_type=e["entity_type"],
                    value=e["value"],
                    confidence=e["confidence"],
                    requires_semantic_validation=e.get(
                        "requires_semantic_validation", False
                    ),
                    metadata=e.get("metadata", {}),
                )
                for e in data["extracted_entities"]
            ],
            domain=data["domain"],
            language_code=data["language_code"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            metadata=data.get("metadata", {}),
        )
