# System Architecture Overview

## High-Level Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Frontend Web UI   │    │   Backend API        │    │   External Services │
│                     │    │                      │    │                     │
│ - Upload Interface  │◄──►│ - Flask Application  │◄──►│ - Yandex SpeechKit │
│ - Status Tracking   │    │ - File Management    │    │ - File Storage      │
│ - Results Display   │    │ - Processing Queue   │    │ - Monitoring        │
│ - Export Downloads  │    │ - Export Generation  │    │                     │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
           │                           │                           │
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       │
                           ┌───────────▼────────────┐
                           │     Data Layer         │
                           │                        │
                           │ - SQLite (MVP)         │
                           │ - File System Storage  │
                           │ - Redis (Queuing)      │
                           │ - Session Storage      │
                           └────────────────────────┘
```

## Core Components

1. **Web Frontend**: Responsive HTML5/CSS3/JavaScript interface with drag-and-drop file upload
2. **Flask API Backend**: RESTful API handling file processing, status tracking, and export generation
3. **Processing Engine**: Yandex SpeechKit integration with retry logic and error handling
4. **File Manager**: Secure file upload, storage, validation, and automated cleanup
5. **Export System**: Multi-format transcript generation (Plain Text, SRT, VTT, JSON)
6. **Queue System**: Redis-backed Celery for concurrent processing management
7. **Monitoring Layer**: Health checks, logging, metrics collection, and alerting

## Data Flow

```
Upload → Validation → Queue → Processing → Export → Cleanup
   │         │          │         │          │        │
   ▼         ▼          ▼         ▼          ▼        ▼
Web UI → File Check → Redis → Yandex API → Generate → Delete
```

1. **Upload**: User uploads audio file via web interface
2. **Validation**: File format, size, and content validation
3. **Queue**: Job queued in Redis for processing
4. **Processing**: Yandex SpeechKit transcription with diarization
5. **Export**: Multi-format transcript generation
6. **Cleanup**: Automated file deletion after 24 hours
