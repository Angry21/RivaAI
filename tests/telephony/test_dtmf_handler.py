"""Unit tests for DTMF Handler."""

import pytest

from rivaai.telephony.dtmf_handler import DTMFHandler, DTMFOption


class TestDTMFHandler:
    """Test suite for DTMFHandler class."""

    def test_initialization(self):
        """Test DTMFHandler initialization."""
        handler = DTMFHandler()
        assert handler is not None

    def test_language_map(self):
        """Test language mapping is correct."""
        assert DTMFHandler.LANGUAGE_MAP["1"] == "hi-IN"
        assert DTMFHandler.LANGUAGE_MAP["2"] == "mr-IN"
        assert DTMFHandler.LANGUAGE_MAP["3"] == "te-IN"
        assert DTMFHandler.LANGUAGE_MAP["4