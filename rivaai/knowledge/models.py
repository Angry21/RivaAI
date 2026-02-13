"""Data models for knowledge base entities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Crop:
    """Agricultural crop information."""

    id: Optional[int]
    name: str
    local_names: Dict[str, str]
    season: str
    region: str
    soil_requirements: str
    water_requirements: str
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Chemical:
    """Chemical (pesticide/fertilizer) information with safety limits."""

    id: Optional[int]
    name: str
    type: str  # pesticide, fertilizer, etc.
    safe_dosage_min: float
    safe_dosage_max: float
    unit: str
    safety_warnings: List[str]
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Scheme:
    """Government welfare or education scheme information."""

    id: Optional[int]
    name: str
    domain: str  # 'welfare', 'education'
    local_names: Dict[str, str]
    eligibility_criteria: List[str]
    required_documents: List[str]
    application_process: str
    contact_info: Dict[str, Any]
    last_updated: datetime
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None


@dataclass
class CropChemicalRelationship:
    """Relationship between crops and chemicals."""

    id: Optional[int]
    crop_id: int
    chemical_id: int
    relationship_type: str  # 'SAFE_FOR', 'REQUIRES', 'AVOID'
    dosage_recommendation: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class CropWeatherRequirement:
    """Weather requirements for crops."""

    id: Optional[int]
    crop_id: int
    weather_condition: str
    requirement_details: Dict[str, Any]
    created_at: Optional[datetime] = None


@dataclass
class Document:
    """Generic document for retrieval results."""

    doc_id: str
    content: str
    metadata: Dict[str, Any]
    embedding: List[float]
    source: str
    domain: str
    last_updated: datetime
    relevance_score: float = 0.0


# Retrieval System Models and Exceptions


class RetrievalError(Exception):
    """Base exception for all retrieval-related errors."""

    pass


class EmbeddingError(RetrievalError):
    """Raised when embedding generation fails."""

    pass


class DatabaseError(RetrievalError):
    """Raised when database operation fails."""

    pass


class ValidationError(RetrievalError):
    """Raised when input validation fails."""

    pass


@dataclass
class RawSearchResult:
    """Intermediate result from vector search before reranking.

    Represents a raw database row from pgvector similarity search.
    """

    doc_id: str
    content: str
    metadata: Dict[str, Any]
    similarity: float
    domain: str
    entity_type: str
    source_table: str


@dataclass
class SearchResult:
    """Final search result returned by retrieval system.

    Contains all metadata, scores, and content for a retrieved document.
    """

    doc_id: str
    content: str
    metadata: Dict[str, Any]
    similarity_score: float  # Original vector similarity (0.0-1.0)
    reranked_score: Optional[float]  # Hybrid reranked score
    domain: str  # 'agriculture', 'welfare', 'education'
    entity_type: str  # 'crop', 'chemical', 'scheme', 'document'
    source_table: str  # Database table name

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of search result
        """
        return {
            "doc_id": self.doc_id,
            "content_preview": self.content[:100] + "..." if len(self.content) > 100 else self.content,
            "similarity_score": round(self.similarity_score, 4),
            "reranked_score": round(self.reranked_score, 4) if self.reranked_score else None,
            "domain": self.domain,
            "entity_type": self.entity_type,
            "source_table": self.source_table,
            "metadata": self.metadata,
        }
