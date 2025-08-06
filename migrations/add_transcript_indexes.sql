-- Add database indexes for optimal transcript retrieval performance
-- Story 1.6: Basic Transcript Generation and Display

-- Index for job lookups by external job_id
CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id);

-- Index for job results lookups
CREATE INDEX IF NOT EXISTS idx_job_results_job_id ON job_results(job_id);

-- Index for speakers by job
CREATE INDEX IF NOT EXISTS idx_speakers_job_id ON speakers(job_id);

-- Composite index for transcript segments ordering
CREATE INDEX IF NOT EXISTS idx_transcript_segments_job_order ON transcript_segments(job_id, segment_order);

-- Index for transcript segments by speaker
CREATE INDEX IF NOT EXISTS idx_transcript_segments_speaker ON transcript_segments(speaker_id);

-- Index for time-based segment queries
CREATE INDEX IF NOT EXISTS idx_transcript_segments_time ON transcript_segments(job_id, start_time, end_time);

-- Index for job status queries
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Composite index for job completion queries
CREATE INDEX IF NOT EXISTS idx_jobs_status_completed ON jobs(status, completed_at) WHERE status = 'completed';

-- ANALYZE tables for query optimization
ANALYZE jobs;
ANALYZE job_results;
ANALYZE speakers;
ANALYZE transcript_segments;