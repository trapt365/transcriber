# Database Design

## MVP Schema (SQLite)

```sql
-- Job tracking and processing status
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(36) UNIQUE NOT NULL,           -- UUID for external reference
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    file_format VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded',
    progress INTEGER DEFAULT 0,                   -- Processing progress 0-100
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL               -- For 24-hour cleanup
);

-- Processing results and metadata
CREATE TABLE job_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(36) NOT NULL,
    raw_transcript TEXT,                        -- Original API response
    formatted_transcript TEXT,                  -- Processed transcript
    speaker_count INTEGER,
    confidence_score FLOAT,
    language_detected VARCHAR(50),
    processing_duration INTEGER,                -- Seconds
    api_cost DECIMAL(10,4),                    -- Track Yandex API costs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- Speaker information from diarization
CREATE TABLE speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(36) NOT NULL,
    speaker_id VARCHAR(20) NOT NULL,           -- Speaker 1, Speaker 2, etc.
    speaker_label VARCHAR(100),                -- User-customizable name
    speaking_duration INTEGER,                 -- Total seconds
    segment_count INTEGER,                     -- Number of speaking segments
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- Transcript segments with timestamps
CREATE TABLE transcript_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(36) NOT NULL,
    speaker_id VARCHAR(20) NOT NULL,
    start_time DECIMAL(10,3) NOT NULL,         -- Seconds with millisecond precision
    end_time DECIMAL(10,3) NOT NULL,
    text TEXT NOT NULL,
    confidence DECIMAL(5,4),                   -- 0.0000 to 1.0000
    segment_order INTEGER NOT NULL,            -- Sequence in transcript
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- System usage tracking
CREATE TABLE usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    files_processed INTEGER DEFAULT 0,
    total_duration INTEGER DEFAULT 0,          -- Total audio minutes processed
    api_cost_total DECIMAL(10,4) DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_jobs_expires_at ON jobs(expires_at);
CREATE INDEX idx_job_results_job_id ON job_results(job_id);
CREATE INDEX idx_speakers_job_id ON speakers(job_id);
CREATE INDEX idx_transcript_segments_job_id ON transcript_segments(job_id);
CREATE INDEX idx_transcript_segments_order ON transcript_segments(job_id, segment_order);
```

## Migration Strategy

**Phase 1 (MVP)**: SQLite with file-based storage
- Single file database for simplicity
- Automatic schema creation on first run
- Built-in backup via file copy

**Phase 2 (Production)**: PostgreSQL migration
```python