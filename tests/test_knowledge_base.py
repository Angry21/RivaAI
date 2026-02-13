"""Tests for knowledge base setup and embedding generation."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from rivaai.knowledge.data_loader import KnowledgeBaseLoader
from rivaai.knowledge.embeddings import EmbeddingGenerator
from rivaai.knowledge.models import Chemical, Crop, Scheme


class TestEmbeddingGenerator:
    """Test embedding generation functionality."""

    @patch("rivaai.knowledge.embeddings.OpenAI")
    def test_generate_embedding(self, mock_openai):
        """Test single embedding generation."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Create settings mock
        settings = MagicMock()
        settings.openai_api_key = "test_key"
        settings.embedding_model = "text-embedding-3-large"

        # Test embedding generation
        gen = EmbeddingGenerator(settings)
        embedding = gen.generate_embedding("test text")

        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
        mock_client.embeddings.create.assert_called_once()

    @patch("rivaai.knowledge.embeddings.OpenAI")
    def test_generate_embeddings_batch(self, mock_openai):
        """Test batch embedding generation."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
            MagicMock(embedding=[0.3] * 1536),
        ]
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        settings = MagicMock()
        settings.openai_api_key = "test_key"
        settings.embedding_model = "text-embedding-3-large"

        gen = EmbeddingGenerator(settings)
        embeddings = gen.generate_embeddings_batch(["text1", "text2", "text3"])

        assert len(embeddings) == 3
        assert all(len(emb) == 1536 for emb in embeddings)


class TestKnowledgeBaseLoader:
    """Test knowledge base data loading."""

    def test_generate_crop_text(self):
        """Test crop text generation for embedding."""
        db_pool = MagicMock()
        embedding_gen = MagicMock()
        loader = KnowledgeBaseLoader(db_pool, embedding_gen)

        crop = Crop(
            id=None,
            name="Wheat",
            local_names={"hi": "गेहूं", "mr": "गहू"},
            season="Rabi",
            region="North India",
            soil_requirements="Well-drained loamy soil",
            water_requirements="4-5 irrigations",
        )

        text = loader._generate_crop_text(crop)

        assert "Wheat" in text
        assert "गेहूं" in text
        assert "Rabi" in text
        assert "North India" in text
        assert "Well-drained loamy soil" in text

    def test_generate_chemical_text(self):
        """Test chemical text generation for embedding."""
        db_pool = MagicMock()
        embedding_gen = MagicMock()
        loader = KnowledgeBaseLoader(db_pool, embedding_gen)

        chemical = Chemical(
            id=None,
            name="Urea",
            type="fertilizer",
            safe_dosage_min=100.0,
            safe_dosage_max=150.0,
            unit="kg/acre",
            safety_warnings=["Do not exceed 150 kg", "Apply in split doses"],
        )

        text = loader._generate_chemical_text(chemical)

        assert "Urea" in text
        assert "fertilizer" in text
        assert "100.0-150.0 kg/acre" in text
        assert "Do not exceed 150 kg" in text

    def test_generate_scheme_text(self):
        """Test scheme text generation for embedding."""
        db_pool = MagicMock()
        embedding_gen = MagicMock()
        loader = KnowledgeBaseLoader(db_pool, embedding_gen)

        scheme = Scheme(
            id=None,
            name="PM-KISAN",
            domain="welfare",
            local_names={"hi": "प्रधानमंत्री किसान सम्मान निधि"},
            eligibility_criteria=["Must be a farmer", "Land ownership required"],
            required_documents=["Aadhaar card", "Land records"],
            application_process="Apply online at pmkisan.gov.in",
            contact_info={"website": "https://pmkisan.gov.in"},
            last_updated=datetime.now(),
        )

        text = loader._generate_scheme_text(scheme)

        assert "PM-KISAN" in text
        assert "welfare" in text
        assert "Must be a farmer" in text
        assert "Aadhaar card" in text
        assert "Apply online" in text


class TestDataModels:
    """Test knowledge base data models."""

    def test_crop_model(self):
        """Test Crop data model."""
        crop = Crop(
            id=1,
            name="Wheat",
            local_names={"hi": "गेहूं"},
            season="Rabi",
            region="North India",
            soil_requirements="Loamy soil",
            water_requirements="Moderate",
            embedding=[0.1] * 1536,
        )

        assert crop.id == 1
        assert crop.name == "Wheat"
        assert crop.local_names["hi"] == "गेहूं"
        assert len(crop.embedding) == 1536

    def test_chemical_model(self):
        """Test Chemical data model."""
        chemical = Chemical(
            id=1,
            name="Urea",
            type="fertilizer",
            safe_dosage_min=100.0,
            safe_dosage_max=150.0,
            unit="kg/acre",
            safety_warnings=["Warning 1", "Warning 2"],
        )

        assert chemical.id == 1
        assert chemical.name == "Urea"
        assert chemical.safe_dosage_min == 100.0
        assert chemical.safe_dosage_max == 150.0
        assert len(chemical.safety_warnings) == 2

    def test_scheme_model(self):
        """Test Scheme data model."""
        scheme = Scheme(
            id=1,
            name="PM-KISAN",
            domain="welfare",
            local_names={"hi": "किसान योजना"},
            eligibility_criteria=["Criterion 1"],
            required_documents=["Doc 1"],
            application_process="Process description",
            contact_info={"phone": "123456"},
            last_updated=datetime.now(),
        )

        assert scheme.id == 1
        assert scheme.name == "PM-KISAN"
        assert scheme.domain == "welfare"
        assert len(scheme.eligibility_criteria) == 1
        assert len(scheme.required_documents) == 1


@pytest.mark.skipif(
    True, reason="Integration test - requires database and OpenAI API key"
)
class TestKnowledgeBaseIntegration:
    """Integration tests for knowledge base (requires database)."""

    def test_load_crop_integration(self):
        """Test loading crop with real database."""
        # This would require actual database connection
        # Skip in CI/CD, run manually for integration testing
        pass

    def test_vector_search_integration(self):
        """Test vector search with real database."""
        # This would require actual database connection
        # Skip in CI/CD, run manually for integration testing
        pass
