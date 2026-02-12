"""Unit tests for language detection and DTMF fallback integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

from rivaai.speech.processor import SpeechProcessor
from rivaai.telephony.gateway import TelephonyGateway
from rivaai.telephony.dtmf_handler import DTMFHandler


@pytest.fixture
def mock_twilio_env(monkeypatch):
    """Mock Twilio environment variables for testing."""
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "test_account_sid")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_auth_token")


class TestLanguageDetectionIntegration:
    """Test suite for language detection functionality."""

    @pytest.mark.asyncio
    async def test_detect_language_success(self):
        """Test successful language detection."""
        with patch("rivaai.speech.processor.DeepgramClient") as mock_client:
            # Mock successful language detection
            mock_response = MagicMock()
            mock_response.results.channels = [MagicMock()]
            mock_response.results.channels[0].detected_language = "hi-IN"
            
            # Create proper async mock chain
            mock_transcribe = AsyncMock(return_value=mock_response)
            mock_v = MagicMock()
            mock_v.transcribe_file = mock_transcribe
            mock_asyncrest = MagicMock()
            mock_asyncrest.v = MagicMock(return_value=mock_v)
            mock_listen = MagicMock()
            mock_listen.asyncrest = mock_asyncrest
            mock_client.return_value.listen = mock_listen
            
            processor = SpeechProcessor(api_key="test_key")
            
            # Create sample audio data
            audio_data = b'\x00\x01' * 1000
            
            detected_lang = await processor.detect_language(audio_data, is_mulaw=False)
            
            assert detected_lang == "hi-IN"

    @pytest.mark.asyncio
    async def test_detect_language_unsupported_language(self):
        """Test language detection with unsupported language."""
        with patch("rivaai.speech.processor.DeepgramClient") as mock_client:
            # Mock detection of unsupported language
            mock_response = MagicMock()
            mock_response.results.channels = [MagicMock()]
            mock_response.results.channels[0].detected_language = "en-US"
            
            # Create proper async mock chain
            mock_transcribe = AsyncMock(return_value=mock_response)
            mock_v = MagicMock()
            mock_v.transcribe_file = mock_transcribe
            mock_asyncrest = MagicMock()
            mock_asyncrest.v = MagicMock(return_value=mock_v)
            mock_listen = MagicMock()
            mock_listen.asyncrest = mock_asyncrest
            mock_client.return_value.listen = mock_listen
            
            processor = SpeechProcessor(api_key="test_key")
            audio_data = b'\x00\x01' * 1000
            
            detected_lang = await processor.detect_language(audio_data, is_mulaw=False)
            
            # Should return None for unsupported language
            assert detected_lang is None

    @pytest.mark.asyncio
    async def test_detect_language_failure(self):
        """Test language detection failure."""
        with patch("rivaai.speech.processor.DeepgramClient") as mock_client:
            # Mock detection failure (no language detected)
            mock_response = MagicMock()
            mock_response.results.channels = [MagicMock()]
            mock_response.results.channels[0].detected_language = None
            
            # Create proper async mock chain
            mock_transcribe = AsyncMock(return_value=mock_response)
            mock_v = MagicMock()
            mock_v.transcribe_file = mock_transcribe
            mock_asyncrest = MagicMock()
            mock_asyncrest.v = MagicMock(return_value=mock_v)
            mock_listen = MagicMock()
            mock_listen.asyncrest = mock_asyncrest
            mock_client.return_value.listen = mock_listen
            
            processor = SpeechProcessor(api_key="test_key")
            audio_data = b'\x00\x01' * 1000
            
            detected_lang = await processor.detect_language(audio_data, is_mulaw=False)
            
            assert detected_lang is None

    @pytest.mark.asyncio
    async def test_detect_language_with_mulaw_transcoding(self):
        """Test language detection with μ-law audio transcoding."""
        with patch("rivaai.speech.processor.DeepgramClient") as mock_client:
            mock_response = MagicMock()
            mock_response.results.channels = [MagicMock()]
            mock_response.results.channels[0].detected_language = "mr-IN"
            
            # Create proper async mock chain
            mock_transcribe = AsyncMock(return_value=mock_response)
            mock_v = MagicMock()
            mock_v.transcribe_file = mock_transcribe
            mock_asyncrest = MagicMock()
            mock_asyncrest.v = MagicMock(return_value=mock_v)
            mock_listen = MagicMock()
            mock_listen.asyncrest = mock_asyncrest
            mock_client.return_value.listen = mock_listen
            
            processor = SpeechProcessor(api_key="test_key")
            
            # Create μ-law audio data
            import audioop
            linear_data = b'\x00\x01' * 1000
            mulaw_data = audioop.lin2ulaw(linear_data, 2)
            
            detected_lang = await processor.detect_language(mulaw_data, is_mulaw=True)
            
            assert detected_lang == "mr-IN"

    @pytest.mark.asyncio
    async def test_detect_language_api_error(self):
        """Test language detection with API error."""
        with patch("rivaai.speech.processor.DeepgramClient") as mock_client:
            # Mock API error
            mock_transcribe = AsyncMock(side_effect=Exception("API Error"))
            mock_v = MagicMock()
            mock_v.transcribe_file = mock_transcribe
            mock_asyncrest = MagicMock()
            mock_asyncrest.v = MagicMock(return_value=mock_v)
            mock_listen = MagicMock()
            mock_listen.asyncrest = mock_asyncrest
            mock_client.return_value.listen = mock_listen
            
            processor = SpeechProcessor(api_key="test_key")
            audio_data = b'\x00\x01' * 1000
            
            detected_lang = await processor.detect_language(audio_data, is_mulaw=False)
            
            # Should return None on error
            assert detected_lang is None


class TestDTMFLanguageSelection:
    """Test suite for DTMF language selection fallback."""

    def test_generate_language_selection_twiml_hindi(self, mock_twilio_env):
        """Test TwiML generation for language selection in Hindi."""
        gateway = TelephonyGateway()
        call_sid = "CA1234567890"
        action_url = "https://example.com/language-selected"
        
        twiml = gateway.generate_language_selection_twiml(
            call_sid, action_url, language_code="hi-IN"
        )
        
        assert isinstance(twiml, str)
        assert "<Gather" in twiml
        assert 'numDigits="1"' in twiml  # TwiML uses camelCase
        assert action_url in twiml
        # Check for Hindi prompt text
        assert "कृपया अपनी भाषा चुनें" in twiml

    def test_generate_language_selection_twiml_default(self, mock_twilio_env):
        """Test TwiML generation with default language."""
        gateway = TelephonyGateway()
        call_sid = "CA1234567890"
        action_url = "https://example.com/language-selected"
        
        twiml = gateway.generate_language_selection_twiml(call_sid, action_url)
        
        assert isinstance(twiml, str)
        assert "<Gather" in twiml
        # Should default to Hindi
        assert "कृपया अपनी भाषा चुनें" in twiml

    def test_parse_language_selection_valid(self):
        """Test parsing valid DTMF language selection."""
        handler = DTMFHandler()
        
        # Test all valid language selections
        assert handler.parse_language_selection("1") == "hi-IN"
        assert handler.parse_language_selection("2") == "mr-IN"
        assert handler.parse_language_selection("3") == "te-IN"
        assert handler.parse_language_selection("4") == "ta-IN"
        assert handler.parse_language_selection("5") == "bn-IN"

    def test_parse_language_selection_invalid(self):
        """Test parsing invalid DTMF language selection."""
        handler = DTMFHandler()
        
        # Test invalid selections
        assert handler.parse_language_selection("6") is None
        assert handler.parse_language_selection("0") is None
        assert handler.parse_language_selection("9") is None
        assert handler.parse_language_selection("*") is None

    def test_language_selection_prompts_all_languages(self):
        """Test that language selection prompts exist for all supported languages."""
        handler = DTMFHandler()
        
        supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        
        for lang in supported_languages:
            prompt = handler.get_language_selection_prompt(lang)
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            # Each prompt should mention pressing digits 1-5
            assert "1" in prompt
            assert "5" in prompt


class TestDTMFSTTFallback:
    """Test suite for DTMF fallback when STT fails."""

    def test_generate_stt_fallback_twiml_hindi(self, mock_twilio_env):
        """Test TwiML generation for STT fallback in Hindi."""
        gateway = TelephonyGateway()
        call_sid = "CA1234567890"
        action_url = "https://example.com/domain-selected"
        
        twiml = gateway.generate_stt_fallback_twiml(
            call_sid, action_url, language_code="hi-IN"
        )
        
        assert isinstance(twiml, str)
        assert "<Gather" in twiml
        assert 'numDigits="1"' in twiml  # TwiML uses camelCase
        assert action_url in twiml
        # Check for STT failure message
        assert "मैं आपकी बात सुनने में परेशानी हो रही है" in twiml

    def test_generate_stt_fallback_twiml_all_languages(self, mock_twilio_env):
        """Test STT fallback TwiML for all supported languages."""
        gateway = TelephonyGateway()
        call_sid = "CA1234567890"
        action_url = "https://example.com/domain-selected"
        
        supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        
        for lang in supported_languages:
            twiml = gateway.generate_stt_fallback_twiml(call_sid, action_url, lang)
            assert isinstance(twiml, str)
            assert "<Gather" in twiml
            assert action_url in twiml

    def test_parse_domain_selection_valid(self):
        """Test parsing valid DTMF domain selection."""
        handler = DTMFHandler()
        
        assert handler.parse_domain_selection("1") == "farming"
        assert handler.parse_domain_selection("2") == "education"
        assert handler.parse_domain_selection("3") == "welfare"

    def test_parse_domain_selection_invalid(self):
        """Test parsing invalid DTMF domain selection."""
        handler = DTMFHandler()
        
        assert handler.parse_domain_selection("4") is None
        assert handler.parse_domain_selection("0") is None
        assert handler.parse_domain_selection("*") is None

    def test_stt_failure_prompts_all_languages(self):
        """Test that STT failure prompts exist for all supported languages."""
        handler = DTMFHandler()
        
        supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        
        for lang in supported_languages:
            prompt = handler.get_stt_failure_prompt(lang)
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            # Each prompt should mention pressing digits 1-3 for domains
            assert "1" in prompt
            assert "3" in prompt


class TestDTMFInvalidInput:
    """Test suite for invalid DTMF input handling."""

    def test_generate_invalid_input_twiml(self, mock_twilio_env):
        """Test TwiML generation for invalid input."""
        gateway = TelephonyGateway()
        call_sid = "CA1234567890"
        retry_url = "https://example.com/retry"
        
        twiml = gateway.generate_invalid_input_twiml(
            call_sid, retry_url, language_code="hi-IN"
        )
        
        assert isinstance(twiml, str)
        assert "<Say" in twiml
        assert retry_url in twiml
        assert "गलत विकल्प" in twiml

    def test_invalid_input_prompts_all_languages(self):
        """Test invalid input prompts for all supported languages."""
        handler = DTMFHandler()
        
        supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        
        for lang in supported_languages:
            prompt = handler.get_invalid_input_prompt(lang)
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_timeout_prompts_all_languages(self):
        """Test timeout prompts for all supported languages."""
        handler = DTMFHandler()
        
        supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        
        for lang in supported_languages:
            prompt = handler.get_timeout_prompt(lang)
            assert isinstance(prompt, str)
            assert len(prompt) > 0


class TestLanguageDetectionDTMFWorkflow:
    """Test suite for complete language detection to DTMF fallback workflow."""

    @pytest.mark.asyncio
    async def test_workflow_detection_success_no_fallback(self):
        """Test workflow when language detection succeeds (no DTMF needed)."""
        with patch("rivaai.speech.processor.DeepgramClient") as mock_client:
            # Mock successful detection
            mock_response = MagicMock()
            mock_response.results.channels = [MagicMock()]
            mock_response.results.channels[0].detected_language = "hi-IN"
            
            # Create proper async mock chain
            mock_transcribe = AsyncMock(return_value=mock_response)
            mock_v = MagicMock()
            mock_v.transcribe_file = mock_transcribe
            mock_asyncrest = MagicMock()
            mock_asyncrest.v = MagicMock(return_value=mock_v)
            mock_listen = MagicMock()
            mock_listen.asyncrest = mock_asyncrest
            mock_client.return_value.listen = mock_listen
            
            processor = SpeechProcessor(api_key="test_key")
            audio_data = b'\x00\x01' * 1000
            
            # Step 1: Try language detection
            detected_lang = await processor.detect_language(audio_data, is_mulaw=False)
            
            # Should succeed, no DTMF fallback needed
            assert detected_lang == "hi-IN"
            assert detected_lang in processor.get_supported_languages()

    @pytest.mark.asyncio
    async def test_workflow_detection_fails_use_dtmf(self, mock_twilio_env):
        """Test workflow when language detection fails (use DTMF fallback)."""
        with patch("rivaai.speech.processor.DeepgramClient") as mock_client:
            # Mock detection failure
            mock_response = MagicMock()
            mock_response.results.channels = [MagicMock()]
            mock_response.results.channels[0].detected_language = None
            
            # Create proper async mock chain
            mock_transcribe = AsyncMock(return_value=mock_response)
            mock_v = MagicMock()
            mock_v.transcribe_file = mock_transcribe
            mock_asyncrest = MagicMock()
            mock_asyncrest.v = MagicMock(return_value=mock_v)
            mock_listen = MagicMock()
            mock_listen.asyncrest = mock_asyncrest
            mock_client.return_value.listen = mock_listen
            
            processor = SpeechProcessor(api_key="test_key")
            gateway = TelephonyGateway()
            handler = DTMFHandler()
            
            audio_data = b'\x00\x01' * 1000
            
            # Step 1: Try language detection
            detected_lang = await processor.detect_language(audio_data, is_mulaw=False)
            
            # Detection failed
            assert detected_lang is None
            
            # Step 2: Fall back to DTMF language selection
            call_sid = "CA1234567890"
            action_url = "https://example.com/language-selected"
            twiml = gateway.generate_language_selection_twiml(
                call_sid, action_url, language_code=None
            )
            
            assert "<Gather" in twiml
            
            # Step 3: User presses DTMF digit (simulated)
            user_input = "2"  # Marathi
            selected_lang = handler.parse_language_selection(user_input)
            
            assert selected_lang == "mr-IN"
            assert selected_lang in processor.get_supported_languages()

    def test_workflow_stt_fails_use_dtmf_domain_selection(self, mock_twilio_env):
        """Test workflow when STT fails (use DTMF for domain selection)."""
        gateway = TelephonyGateway()
        handler = DTMFHandler()
        
        # Assume language is already known (hi-IN)
        language_code = "hi-IN"
        
        # Step 1: STT fails, fall back to DTMF domain selection
        call_sid = "CA1234567890"
        action_url = "https://example.com/domain-selected"
        twiml = gateway.generate_stt_fallback_twiml(
            call_sid, action_url, language_code
        )
        
        assert "<Gather" in twiml
        assert "मैं आपकी बात सुनने में परेशानी हो रही है" in twiml
        
        # Step 2: User presses DTMF digit for domain
        user_input = "1"  # Farming
        selected_domain = handler.parse_domain_selection(user_input)
        
        assert selected_domain == "farming"

    def test_workflow_invalid_dtmf_retry(self, mock_twilio_env):
        """Test workflow when user provides invalid DTMF input."""
        gateway = TelephonyGateway()
        handler = DTMFHandler()
        
        language_code = "hi-IN"
        
        # Step 1: User provides invalid input
        user_input = "9"
        selected_lang = handler.parse_language_selection(user_input)
        
        assert selected_lang is None
        
        # Step 2: Generate invalid input TwiML to retry
        call_sid = "CA1234567890"
        retry_url = "https://example.com/language-selection"
        twiml = gateway.generate_invalid_input_twiml(
            call_sid, retry_url, language_code
        )
        
        assert "<Say" in twiml
        assert retry_url in twiml
        assert "गलत विकल्प" in twiml
