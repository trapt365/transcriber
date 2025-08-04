# Requirements

## Functional

FR1: The system must accept audio file uploads in WAV, MP3, and FLAC formats up to 500MB (≈3 hours)
FR2: The system must integrate with Yandex SpeechKit API using "universal mode" for automatic Kazakh-Russian language detection
FR3: The system must perform automatic speaker diarization using built-in Yandex API functionality
FR4: The system must export transcripts in 4 formats: Plain Text, SRT, VTT, and JSON with speaker labels and timestamps
FR5: The system must provide real-time processing status tracking with progress indicators and error handling
FR6: The system must assign automatic speaker labels ("Speaker 1", "Speaker 2", etc.) based on diarization results
FR7: The system must validate uploaded files for format compatibility, size limits, and audio quality
FR8: The system must provide drag-and-drop upload interface with progress visualization
FR9: The system must handle code-switching between Kazakh and Russian within single utterances
FR10: The system must generate timestamped segments for each speaker turn in exported formats

## Non Functional

NFR1: The system must process 3-hour audio files within 15 minutes from upload to download
NFR2: The system must achieve ≥85% transcription accuracy on mixed Kazakh-Russian speech
NFR3: The system must maintain ≥99% uptime and handle API failures gracefully with retry logic
NFR4: The system must support up to 5 concurrent file uploads without performance degradation
NFR5: The system must keep operational costs ≤$2 per 3-hour transcription including all API and hosting fees
NFR6: The system must automatically delete uploaded files after 24 hours for privacy and storage management
NFR7: The system must respond to user interface actions within 2 seconds for optimal user experience
NFR8: The system must implement rate limiting and input validation for security against malicious uploads
NFR9: The system must log all processing activities for debugging and usage analytics while protecting user privacy
NFR10: The system must be deployable on basic cloud infrastructure without GPU requirements
