"""Property-based tests for call establishment latency.

Feature: sochq
Property 1: Call Establishment Latency
Validates: Requirements 1.1

For any incoming call, the Telephony_Layer should answer within 3 rings 
and establish a full-duplex WebSocket connection with valid audio streaming capabilities.
"""

import time
from unittest.mock import patch

import pytest
from hypothesis import given, strategies as st

from rivaai.telephony import CallStatus, TelephonyGateway, WebSocketConnection


# Strategy for generating valid phone numbers (ANI)
phone_number_strategy = st.one_of(
    # US/Canada format
    st.from_regex(r"\+1[2-9]\d{9}", fullmatch=True),
    # International format (India)
    st.from_regex(r"\+91[6-9]\d{9}", fullmatch=True),
    # Generic international format
    st.builds(
        lambda country, number: f"+{country}{number}",
        country=st.integers(min_value=1, max_value=999),
        number=st.integers(min_value=1000000000, max_value=9999999999)
    )
)


@pytest.mark.property
class TestCallEstablishmentLatency:
    """Property-based tests for call establishment latency requirements."""

    @given(caller_ani=phone_number_strategy)
    def test_call_answered_within_3_rings(self, caller_ani: str):
        """
        Property 1: Call Establishment Latency
        
        For any incoming call, the Telephony_Layer should answer within 3 rings
        (approximately 3000ms) and establish a full-duplex WebSocket connection.
        
        Validates: Requirements 1.1
        """
        with patch("rivaai.telephony.gateway.Client"):
            gateway = TelephonyGateway()
            
            # Measure call establishment time
            start_time = time.perf_counter()
            call_session = gateway.handle_incoming_call(caller_ani)
            end_time = time.perf_counter()
            
            elapsed_ms = (end_time - start_time) * 1000
            
            # Verify call is answered within 3 rings (3000ms)
            assert elapsed_ms < 3000, (
                f"Call establishment took {elapsed_ms:.2f}ms, "
                f"exceeds 3-ring limit (3000ms)"
            )
            
            # Verify call session is created with ANSWERED status
            assert call_session.status == CallStatus.ANSWERED, (
                "Call should be in ANSWERED status after establishment"
            )
            
            # Verify session has valid identifiers
            assert call_session.call_sid is not None
            assert call_session.session_id is not None
            assert call_session.caller_ani_hash is not None
            
            # Verify WebSocket URL is provided
            assert call_session.websocket_url is not None
            assert len(call_session.websocket_url) > 0

    @given(caller_ani=phone_number_strategy)
    def test_websocket_established_with_valid_audio_config(self, caller_ani: str):
        """
        Property 1: Call Establishment Latency (WebSocket Configuration)
        
        For any incoming call, the established WebSocket connection should have
        valid audio streaming capabilities configured for telephony standard.
        
        Validates: Requirements 1.1, 1.4
        """
        with patch("rivaai.telephony.gateway.Client"):
            gateway = TelephonyGateway()
            
            # Establish call and get call_sid
            call_session = gateway.handle_incoming_call(caller_ani)
            
            # Measure WebSocket establishment time
            start_time = time.perf_counter()
            ws_connection = gateway.establish_websocket(call_session.call_sid)
            end_time = time.perf_counter()
            
            elapsed_ms = (end_time - start_time) * 1000
            
            # WebSocket establishment should be fast (part of 3-ring budget)
            assert elapsed_ms < 1000, (
                f"WebSocket establishment took {elapsed_ms:.2f}ms, "
                f"should be under 1000ms"
            )
            
            # Verify WebSocket connection is properly configured
            assert isinstance(ws_connection, WebSocketConnection)
            assert ws_connection.call_sid == call_session.call_sid
            
            # Verify telephony standard audio configuration
            assert ws_connection.audio_format == "mulaw", (
                "Audio format must be μ-law PCM for telephony"
            )
            assert ws_connection.sample_rate == 8000, (
                "Sample rate must be 8kHz for telephony standard"
            )
            assert ws_connection.frame_size_ms == 20, (
                "Frame size must be 20ms for telephony"
            )
            
            # Verify WebSocket URL is valid
            assert ws_connection.websocket_url is not None
            assert call_session.call_sid in ws_connection.websocket_url

    @given(
        caller_ani=phone_number_strategy,
        num_calls=st.integers(min_value=1, max_value=10)
    )
    def test_multiple_calls_all_answered_within_latency(
        self, 
        caller_ani: str, 
        num_calls: int
    ):
        """
        Property 1: Call Establishment Latency (Multiple Calls)
        
        For any sequence of incoming calls, each call should be answered
        within 3 rings independently.
        
        Validates: Requirements 1.1
        """
        with patch("rivaai.telephony.gateway.Client"):
            gateway = TelephonyGateway()
            
            for i in range(num_calls):
                start_time = time.perf_counter()
                call_session = gateway.handle_incoming_call(caller_ani)
                end_time = time.perf_counter()
                
                elapsed_ms = (end_time - start_time) * 1000
                
                assert elapsed_ms < 3000, (
                    f"Call {i+1}/{num_calls} took {elapsed_ms:.2f}ms, "
                    f"exceeds 3-ring limit (3000ms)"
                )
                
                assert call_session.status == CallStatus.ANSWERED
                assert call_session.call_sid is not None

    @given(caller_ani=phone_number_strategy)
    def test_full_duplex_capability_indicated(self, caller_ani: str):
        """
        Property 1: Call Establishment Latency (Full-Duplex)
        
        For any incoming call, the established WebSocket connection should
        support full-duplex audio streaming (bidirectional).
        
        Validates: Requirements 1.1
        """
        with patch("rivaai.telephony.gateway.Client"):
            gateway = TelephonyGateway()
            
            # Establish call and WebSocket
            call_session = gateway.handle_incoming_call(caller_ani)
            ws_connection = gateway.establish_websocket(call_session.call_sid)
            
            # Verify full-duplex capability
            # Full-duplex means the connection can handle both incoming and outgoing
            # audio simultaneously. This is indicated by the WebSocket configuration.
            assert ws_connection.audio_format == "mulaw"
            assert ws_connection.sample_rate == 8000
            
            # The WebSocket URL should be unique per call for bidirectional streaming
            assert call_session.call_sid in ws_connection.websocket_url
            
            # Verify the connection is ready to be established
            # (is_connected will be False until actual connection, but config is ready)
            assert ws_connection.is_connected is False  # Not yet connected
            assert ws_connection.websocket_url is not None  # But ready to connect

    @given(caller_ani=phone_number_strategy)
    def test_call_establishment_creates_unique_sessions(self, caller_ani: str):
        """
        Property 1: Call Establishment Latency (Session Uniqueness)
        
        For any incoming call, a unique session should be created even if
        from the same caller ANI, ensuring proper call isolation.
        
        Validates: Requirements 1.1, 3.1
        """
        with patch("rivaai.telephony.gateway.Client"):
            gateway = TelephonyGateway()
            
            # Establish multiple calls from same ANI
            call_session_1 = gateway.handle_incoming_call(caller_ani)
            call_session_2 = gateway.handle_incoming_call(caller_ani)
            
            # Each call should have unique identifiers
            assert call_session_1.call_sid != call_session_2.call_sid, (
                "Each call must have a unique call_sid"
            )
            assert call_session_1.session_id != call_session_2.session_id, (
                "Each call must have a unique session_id"
            )
            
            # But same caller should have same ANI hash (for session resumption)
            assert call_session_1.caller_ani_hash == call_session_2.caller_ani_hash, (
                "Same caller ANI should produce same hash"
            )
            
            # Both calls should be answered
            assert call_session_1.status == CallStatus.ANSWERED
            assert call_session_2.status == CallStatus.ANSWERED
