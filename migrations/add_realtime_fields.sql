-- Migration: Add real-time status tracking fields
-- Story 1.4: Processing Status Tracking and Real-time Updates

-- Add new fields to jobs table for real-time status tracking
ALTER TABLE jobs ADD COLUMN processing_phase VARCHAR(50);
ALTER TABLE jobs ADD COLUMN estimated_completion DATETIME;
ALTER TABLE jobs ADD COLUMN queue_position INTEGER;
ALTER TABLE jobs ADD COLUMN can_cancel BOOLEAN NOT NULL DEFAULT TRUE;

-- Create processing_history table for tracking performance metrics
CREATE TABLE processing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_size BIGINT NOT NULL,
    processing_duration REAL NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries on processing_history
CREATE INDEX idx_processing_history_file_size ON processing_history(file_size);
CREATE INDEX idx_processing_history_created_at ON processing_history(created_at);

-- Update existing jobs to have can_cancel = TRUE by default
UPDATE jobs SET can_cancel = TRUE WHERE can_cancel IS NULL;