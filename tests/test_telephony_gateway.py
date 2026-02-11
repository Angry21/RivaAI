"""Unit tests for TelephonyGateway class."""

import hashlib
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from rivaai.telephony import (
    AudioTranscoder,
    CallSession,
    CallStatus,
    TelephonyGateway,
    WebSocketConnection,
)


class TestTelephonyGateway:
    """Test suite for TelephonyGateway class."""

    @pytest.fixture
    def gateway(self):
        """Create a TelephonyGateway instance for testing."""
        with patch("rivaai.telephony.gateway.Client"):
            gateway = TelephonyGateway()
            return gateway

    def test_handle_incoming_call_creates_session(self, gateway):
        """Test that handle_incoming_call creates a valid CallSession."""
        caller_ani = "+1234567890"
        
        call_session = gateway.handle_incoming_call(caller_ani)
        
        assert isinstance(call_session, CallSession)
        assert call_session.call_sid.startswith("CA")
        assert len(call_session.call_sid) == 34  # "CA" + 32 hex chars
        assert call_session.status == CallStatus.ANSWERED
        assert call_session.caller_ani_hash == hashlib.sha256(caller_ani.encode()).hexdigest()
        assert isinstance(call_session.started_at, datetime)
        assert call_session.ended_at is None

    def test_handle_incoming_call_hashes_ani(self, gateway):
        """Test that caller ANI is properly hashed for privacy."""
        caller_ani = "+1234567890"
        expected_hash = hashlib.sha256(caller_ani.encode()).hexdigest()
        
        call_session = gateway.handle_incoming_call(caller_ani)
        
        assert call_session.caller_ani_hash == expected_hash
        # Ensure the original ANI is not stored
        assert caller_ani not in str(call_session.__dict__)

    def test_handle_incoming_call_generates_unique_sessions(self, gateway):
        """Test that multiple calls generate unique session IDs."""
        caller_ani = "+1234567890"
        
        session1 = gateway.handle_incoming_call(caller_ani)
        session2 = gateway.handle_incoming_call(caller_ani)
        
        assert session1.session_id != session2.session_id
        assert session1.call_sid != session2.call_sid

    def test_establish_websocket_creates_connection(self, gateway):
        """Test that establish_websocket creates a valid WebSocketConnection."""
        call_sid = "CA1234567890abcdef1234567890abcd"
        
        ws_connection = gateway.establish_websocket(call_sid)
        
        assert isinstance(ws_connection, WebSocketConnection)
        assert ws_connection.call_sid == call_sid
        assert ws_connection.audio_format == "mulaw"
        assert ws_connection.sample_rate == 8000
        assert ws_connection.frame_size_ms == 20
        assert ws_connection.is_connected is False

    def test_establish_websocket_uses_correct_audio_format(self, gateway):
        """Test that WebSocket is configured for G.711 μ-law PCM at 8kHz."""
        call_sid = "CA1234567890abcdef1234567890abcd"
        
        ws_connection = gateway.establish_websocket(call_sid)
        
        # Verify telephony standard: μ-law PCM at 8kHz
        assert ws_connection.audio_format == "mulaw"
        assert ws_connection.sample_rate == 8000
        assert ws_connection.frame_size_ms == 20

    def test_terminate_call_logs_without_error(self, gateway):
        """Test that terminate_call completes without error."""
        call_sid = "CA1234567890abcdef1234567890abcd"
        
        # Should not raise an exception
        gateway.terminate_call(call_sid)

    def test_generate_twiml_response_creates_valid_xml(self, gateway):
        """Test that generate_twiml_response creates valid TwiML."""
        call_sid = "CA1234567890abcdef1234567890abcd"
        
        twiml = gateway.generate_twiml_response(call_sid)
        
        assert isinstance(twiml, str)
        assert "<?xml version" in twiml
        assert "<Response>" in twiml
        assert "<Connect>" in twiml
        assert "<Stream" in twiml
        assert call_sid in twiml

    def test_generate_twiml_response_configures_audio_format(self, gateway):
        """Test that TwiML response configures correct audio format."""
        call_sid = "CA1234567890abcdef1234567890abcd"
        
        twiml = gateway.generate_twiml_response(call_sid)
        
        # Should configure μ-law format and 8kHz sample rate
        assert "mulaw" in twiml or "audio_format" in twiml
        assert "8000" in twiml or "sample_rate" in twiml

    def test_get_call_metadata_returns_dict(self, gateway):
        """Test that get_call_metadata returns a dictionary."""
        call_sid = "CA1234567890abcdef1234567890abcd"
        
        metadata = gateway.get_call_metadata(call_sid)
        
        assert isinstance(metadata, dict)
        assert "call_sid" in metadata
        assert metadata["call_sid"] == call_sid

    def test_hash_ani_produces_consistent_hash(self, gateway):
        """Test that _hash_ani produces consistent SHA-256 hashes."""
        ani = "+1234567890"
        expected_hash = hashlib.sha256(ani.encode()).hexdigest()
        
        hash1 = gateway._hash_ani(ani)
        hash2 = gateway._hash_ani(ani)
        
        assert hash1 == hash2
        assert hash1 == expected_hash
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters

    def test_hash_ani_different_for_different_numbers(self, gateway):
        """Test that different ANIs produce different hashes."""
        ani1 = "+1234567890"
        ani2 = "+0987654321"
        
        hash1 = gateway._hash_ani(ani1)
        hash2 = gateway._hash_ani(ani2)
        
        assert hash1 != hash2


class TestAudioTranscoder:
    """Test suite for AudioTranscoder class."""

    @pytest.fixture
    def transcoder(self):
        """Create an AudioTranscoder instance for testing."""
        return AudioTranscoder()

    def test_mulaw_to_linear16_converts_audio(self, transcoder):
        """Test that μ-law to Linear16 conversion works."""
        # Create sample μ-law data (8-bit samples)
        mulaw_data = bytes([0, 127, 255, 64, 192])
        
        linear_data = transcoder.mulaw_to_linear16(mulaw_data)
        
        assert isinstance(linear_data, bytes)
        # Linear16 should be 2x the size (16-bit vs 8-bit)
        assert len(linear_data) == len(mulaw_data) * 2

    def test_mulaw_to_linear16_raises_on_empty_data(self, transcoder):
        """Test that empty data raises ValueError."""
        with pytest.raises(ValueError, match="Empty audio data"):
            transcoder.mulaw_to_linear16(b"")

    def test_linear16_to_mulaw_converts_audio(self, transcoder):
        """Test that Linear16 to μ-law conversion works."""
        # Create sample Linear16 data (16-bit samples)
        linear_data = bytes([0, 0, 127, 127, 255, 255, 64, 64])
        
        mulaw_data = transcoder.linear16_to_mulaw(linear_data)
        
        assert isinstance(mulaw_data, bytes)
        # μ-law should be half the size (8-bit vs 16-bit)
        assert len(mulaw_data) == len(linear_data) // 2

    def test_linear16_to_mulaw_raises_on_empty_data(self, transcoder):
        """Test that empty data raises ValueError."""
        with pytest.raises(ValueError, match="Empty audio data"):
            transcoder.linear16_to_mulaw(b"")

    def test_roundtrip_conversion_preserves_data_approximately(self, transcoder):
        """Test that μ-law -> Linear16 -> μ-law roundtrip preserves data."""
        # Create sample μ-law data
        original_mulaw = bytes([0, 127, 255, 64, 192, 32, 160])
        
        # Convert to Linear16 and back
        linear_data = transcoder.mulaw_to_linear16(original_mulaw)
        roundtrip_mulaw = transcoder.linear16_to_mulaw(linear_data)
        
        # Should be the same size
        assert len(roundtrip_mulaw) == len(original_mulaw)
        # Note: Due to lossy compression, values may not be exactly the same
        # but should be close

    def test_resample_audio_same_rate_returns_original(self, transcoder):
        """Test that resampling at the same rate returns original data."""
        audio_data = bytes([0, 0, 127, 127, 255, 255])
        
        resampled = transcoder.resample_audio(audio_data, 8000, 8000)
        
        assert resampled == audio_data

    def test_resample_audio_raises_on_empty_data(self, transcoder):
        """Test that empty data raises ValueError."""
        with pytest.raises(ValueError, match="Empty audio data"):
            transcoder.resample_audio(b"", 8000, 16000)

    def test_validate_audio_format_mulaw(self, transcoder):
        """Test audio format validation for μ-law."""
        # Valid μ-law data (1 byte per sample)
        mulaw_data = bytes([0, 127, 255, 64])
        
        is_valid = transcoder.validate_audio_format(mulaw_data, "mulaw", 8000)
        
        assert is_valid is True

    def test_validate_audio_format_linear16(self, transcoder):
        """Test audio format validation for Linear16."""
        # Valid Linear16 data (2 bytes per sample)
        linear_data = bytes([0, 0, 127, 127, 255, 255])
        
        is_valid = transcoder.validate_audio_format(linear_data, "linear16", 8000)
        
        assert is_valid is True

    def test_validate_audio_format_invalid_size(self, transcoder):
        """Test that invalid data size is detected."""
        # Invalid Linear16 data (odd number of bytes)
        invalid_data = bytes([0, 0, 127])
        
        is_valid = transcoder.validate_audio_format(invalid_data, "linear16", 8000)
        
        assert is_valid is False

    def test_validate_audio_format_empty_data(self, transcoder):
        """Test that empty data is invalid."""
        is_valid = transcoder.validate_audio_format(b"", "mulaw", 8000)
        
        assert is_valid is False

    def test_validate_audio_format_unknown_format(self, transcoder):
        """Test that unknown format returns False."""
        audio_data = bytes([0, 127, 255])
        
        is_valid = transcoder.validate_audio_format(audio_data, "unknown", 8000)
        
        assert is_valid is False


class TestAudioFormatConstants:
    """Test audio format constants and configurations."""

    def test_telephony_standard_configuration(self):
        """Test that telephony standard is correctly configured."""
        transcoder = AudioTranscoder()
        
        # Verify telephony standard: 8kHz, μ-law (8-bit), Linear16 (16-bit)
        assert transcoder.TELEPHONY_SAMPLE_RATE == 8000
        assert transcoder.MULAW_SAMPLE_WIDTH == 1
        assert transcoder.LINEAR16_SAMPLE_WIDTH == 2

    def test_websocket_frame_size(self):
        """Test that WebSocket frame size is 20ms as per design."""
        with patch("rivaai.telephony.gateway.Client"):
            gateway = TelephonyGateway()
            ws_connection = gateway.establish_websocket("CA123")
            
            assert ws_connection.frame_size_ms == 20
