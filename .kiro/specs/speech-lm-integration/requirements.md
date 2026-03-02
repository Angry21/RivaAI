# Requirements Document

## Introduction

This document specifies requirements for integrating a speech-to-speech language model into RivaAI to replace the current multi-stage STT → LLM → TTS pipeline. The goal is to reduce end-to-end latency while maintaining all existing capabilities including multi-language support, RAG integration, barge-in handling, and safety mechanisms.

The current architecture introduces latency through multiple conversion steps: audio to text (STT), text processing through LLM, and text back to audio (TTS). A direct speech-to-speech model can eliminate intermediate text representations and reduce overall response time, critical for natural phone conversations with rural users on basic PSTN phones.

## Glossary

- **Speech_LM**: Speech-to-speech language model that processes audio input directly and generates audio output directly
- **Audio_Router**: Component that manages bidirectional audio streaming between Twilio WebSocket and processing components
- **RAG_System**: Retrieval-Augmented Generation system that provides domain-specific knowledge context
- **Barge_In_Handler**: Component that detects user interruptions during system speech output
- **Circuit_Breaker**: Safety mechanism that validates and blocks harmful or inappropriate outputs
- **Session_Manager**: Component that maintains conversation state with 24-hour TTL
- **Transcoder**: Component that converts audio between μ-law PCM (8kHz) and Linear16 PCM formats
- **STT_Pipeline**: Current Speech-to-Text processing using Deepgram Nova-2
- **TTS_Pipeline**: Current Text-to-Speech processing using ElevenLabs Turbo
- **PII_Masker**: Component that detects and masks personally identifiable information
- **Twilio_Gateway**: Interface to Twilio WebSocket for PSTN call handling

## Requirements

### Requirement 1: Direct Speech-to-Speech Processing

**User Story:** As a system architect, I want the Speech_LM to process audio input and generate audio output directly, so that we eliminate intermediate text conversion latency.

#### Acceptance Criteria

1. WHEN audio input is received from the Audio_Router, THE Speech_LM SHALL process it directly without text conversion
2. WHEN generating a response, THE Speech_LM SHALL produce audio output directly without intermediate text representation
3. THE Speech_LM SHALL accept Linear16 PCM audio format at 16kHz sample rate as input
4. THE Speech_LM SHALL produce Linear16 PCM audio format at 16kHz or higher sample rate as output
5. THE Speech_LM SHALL support streaming input processing to enable real-time conversation flow

### Requirement 2: Multi-Language Support

**User Story:** As a rural user, I want to converse in my native language, so that I can access decision support without language barriers.

#### Acceptance Criteria

1. THE Speech_LM SHALL support Hindi language input and output
2. THE Speech_LM SHALL support Marathi language input and output
3. THE Speech_LM SHALL support Telugu language input and output
4. THE Speech_LM SHALL support Tamil language input and output
5. THE Speech_LM SHALL support Bengali language input and output
6. WHEN processing audio in a specific language, THE Speech_LM SHALL maintain that language for the response unless explicitly requested to switch
7. THE Speech_LM SHALL detect the input language automatically when language is not specified in session context

### Requirement 3: RAG Integration

**User Story:** As a system architect, I want the Speech_LM to incorporate retrieved knowledge, so that responses are grounded in domain-specific information.

#### Acceptance Criteria

1. WHEN the Speech_LM requires domain knowledge, THE RAG_System SHALL retrieve relevant context from the knowledge base
2. THE Speech_LM SHALL accept retrieved knowledge context as conditioning input
3. WHEN generating responses, THE Speech_LM SHALL incorporate provided knowledge context into the audio output
4. THE Speech_LM SHALL support text-based knowledge injection even when operating in speech-to-speech mode
5. WHEN knowledge retrieval fails, THE Speech_LM SHALL generate a response indicating inability to access specific information

### Requirement 4: Latency Performance

**User Story:** As a rural user, I want quick responses during phone conversations, so that the interaction feels natural and responsive.

#### Acceptance Criteria

1. WHEN processing a simple query without RAG retrieval, THE Speech_LM SHALL produce first audio chunk within 500 milliseconds
2. WHEN processing a complex query with RAG retrieval, THE Speech_LM SHALL produce first audio chunk within 1200 milliseconds
3. THE Speech_LM SHALL stream audio output progressively rather than waiting for complete response generation
4. WHEN measuring end-to-end latency, THE system SHALL achieve lower latency than the current STT_Pipeline → LLM → TTS_Pipeline architecture
5. THE Speech_LM SHALL process audio input with maximum 200 milliseconds of buffering delay

### Requirement 5: Barge-In Support

**User Story:** As a user, I want to interrupt the system when it's speaking, so that I can correct misunderstandings or provide additional information immediately.

#### Acceptance Criteria

1. WHEN the Speech_LM is generating audio output, THE Barge_In_Handler SHALL monitor incoming audio for user speech
2. WHEN user speech is detected during system output, THE Barge_In_Handler SHALL signal an interruption event
3. WHEN an interruption event occurs, THE Speech_LM SHALL stop audio generation within 300 milliseconds
4. WHEN an interruption event occurs, THE Speech_LM SHALL preserve conversation context for the next turn
5. THE Speech_LM SHALL support resuming or restarting response generation after barge-in interruption

### Requirement 6: Audio Format Compatibility

**User Story:** As a system architect, I want seamless audio format handling, so that the Speech_LM integrates with existing Twilio WebSocket infrastructure.

#### Acceptance Criteria

1. WHEN receiving audio from Twilio_Gateway, THE Transcoder SHALL convert μ-law PCM at 8kHz to Linear16 PCM at 16kHz
2. WHEN sending audio to Twilio_Gateway, THE Transcoder SHALL convert Linear16 PCM to μ-law PCM at 8kHz
3. THE Audio_Router SHALL buffer audio chunks appropriately for Speech_LM processing requirements
4. THE Speech_LM SHALL handle variable-length audio chunks without requiring fixed-size buffers
5. WHEN audio format conversion introduces artifacts, THE system SHALL log quality degradation warnings

### Requirement 7: Safety Mechanisms

**User Story:** As a system operator, I want safety validation on Speech_LM outputs, so that harmful or inappropriate content is blocked before reaching users.

#### Acceptance Criteria

1. WHEN the Speech_LM generates audio output, THE Circuit_Breaker SHALL validate the content for safety violations
2. IF harmful content is detected, THEN THE Circuit_Breaker SHALL block the audio output and generate a safe fallback response
3. THE Circuit_Breaker SHALL perform semantic validation even when operating on audio outputs
4. THE Circuit_Breaker SHALL complete safety validation within 100 milliseconds to minimize latency impact
5. WHEN safety validation fails repeatedly, THE Circuit_Breaker SHALL escalate to human review and pause the session

### Requirement 8: Session State Management

**User Story:** As a system architect, I want conversation context preserved across turns, so that multi-turn dialogues remain coherent.

#### Acceptance Criteria

1. WHEN a new call begins, THE Session_Manager SHALL create a session with 24-hour TTL
2. WHEN the Speech_LM processes audio, THE Session_Manager SHALL provide conversation history as context
3. WHEN the Speech_LM generates a response, THE Session_Manager SHALL store the turn in conversation history
4. THE Session_Manager SHALL maintain session state in Redis with automatic expiration after 24 hours
5. WHEN a session expires, THE Session_Manager SHALL delete all associated conversation data to preserve privacy

### Requirement 9: Privacy Preservation

**User Story:** As a user, I want my personal information protected, so that sensitive data is not stored or leaked.

#### Acceptance Criteria

1. WHEN audio contains personally identifiable information, THE PII_Masker SHALL detect and mask it before storage
2. THE PII_Masker SHALL operate on audio representations or transcriptions as appropriate for the Speech_LM architecture
3. WHEN storing conversation history, THE Session_Manager SHALL ensure PII has been masked
4. THE system SHALL automatically delete all session data after 24 hours
5. WHEN logging for debugging, THE system SHALL exclude PII from log entries

### Requirement 10: Fallback and Error Handling

**User Story:** As a system operator, I want graceful degradation when the Speech_LM fails, so that users receive helpful error messages rather than silence.

#### Acceptance Criteria

1. IF the Speech_LM fails to process audio input, THEN THE system SHALL generate an error response using TTS_Pipeline as fallback
2. WHEN the Speech_LM is unavailable, THE system SHALL fall back to the STT_Pipeline → LLM → TTS_Pipeline architecture
3. IF audio quality is too poor for Speech_LM processing, THEN THE system SHALL request the user to repeat their input
4. WHEN the Speech_LM encounters an internal error, THE system SHALL log detailed diagnostics for debugging
5. THE system SHALL monitor Speech_LM health and automatically switch to fallback mode when error rate exceeds 10 percent

### Requirement 11: Speech LM Model Selection and Configuration

**User Story:** As a system architect, I want flexible Speech_LM model selection, so that we can optimize for latency, quality, and cost based on deployment requirements.

#### Acceptance Criteria

1. THE system SHALL support configurable Speech_LM model selection via environment variables
2. THE system SHALL validate Speech_LM model compatibility with multi-language requirements during initialization
3. WHEN a Speech_LM model is configured, THE system SHALL verify it supports all required languages before accepting calls
4. THE system SHALL support hot-swapping Speech_LM models without requiring application restart
5. THE system SHALL log Speech_LM model name, version, and configuration parameters at startup

### Requirement 12: Monitoring and Observability

**User Story:** As a system operator, I want detailed metrics on Speech_LM performance, so that I can identify bottlenecks and optimize the system.

#### Acceptance Criteria

1. THE system SHALL measure and log Speech_LM time-to-first-audio-chunk for each response
2. THE system SHALL measure and log end-to-end latency from user speech end to system speech start
3. THE system SHALL track Speech_LM error rates and categorize errors by type
4. THE system SHALL monitor Speech_LM audio quality metrics including signal-to-noise ratio
5. THE system SHALL expose Speech_LM performance metrics via monitoring endpoints for observability tools

### Requirement 13: Testing and Validation

**User Story:** As a developer, I want comprehensive testing for Speech_LM integration, so that I can verify correctness and catch regressions.

#### Acceptance Criteria

1. THE system SHALL include property-based tests for audio format conversions with minimum 100 examples
2. THE system SHALL include round-trip property tests for audio transcoding (Linear16 → μ-law → Linear16)
3. THE system SHALL include integration tests for Speech_LM with RAG_System interaction
4. THE system SHALL include latency benchmark tests comparing Speech_LM to current pipeline
5. THE system SHALL include multi-language tests for all five supported languages

