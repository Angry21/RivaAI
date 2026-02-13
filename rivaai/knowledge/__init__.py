"""Knowledge base and retrieval layer."""

from rivaai.knowledge.data_loader import KnowledgeBaseLoader
from rivaai.knowledge.embeddings import EmbeddingGenerator, get_embedding_generator
from rivaai.knowledge.models import (
    Chemical,
    Crop,
    CropChemicalRelationship,
    CropWeatherRequirement,
    DatabaseError,
    Document,
    EmbeddingError,
    RawSearchResult,
    RetrievalError,
    Scheme,
    SearchResult,
    ValidationError,
)
from rivaai.knowledge.rag_formatter import RAGFormatter
from rivaai.knowledge.reranker import HybridReranker
from rivaai.knowledge.retrieval import RetrievalSystem
from rivaai.knowledge.vector_search import VectorSearchEngine

__all__ = [
    "KnowledgeBaseLoader",
    "EmbeddingGenerator",
    "get_embedding_generator",
    "Crop",
    "Chemical",
    "Scheme",
    "CropChemicalRelationship",
    "CropWeatherRequirement",
    "Document",
    "SearchResult",
    "RawSearchResult",
    "RetrievalError",
    "EmbeddingError",
    "DatabaseError",
    "ValidationError",
    "HybridReranker",
    "VectorSearchEngine",
    "RAGFormatter",
    "RetrievalSystem",
]
