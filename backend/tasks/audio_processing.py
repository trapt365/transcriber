"""Audio processing tasks for transcription pipeline."""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from backend.celery_app import celery_app
from backend.tasks.base import BaseProcessingTask, ProcessingStageEnum
from backend.app.models.job import Job
from backend.app.models.enums import JobStatus
from backend.app.services.processing_service import create_processing_service
from backend.app.services.audio_service import audio_service
from backend.extensions import db
from backend.config import get_config

logger = logging.getLogger(__name__)
config = get_config()


@celery_app.task(bind=True, base=BaseProcessingTask)
def process_audio_task(self, job_id: str) -> Dict[str, Any]:
    """
    Main audio processing task with progress tracking.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Processing result dictionary
        
    Raises:
        ProcessingError: If processing fails
    """
    try:
        # Get job from database
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Update job status to processing
        job.status = JobStatus.PROCESSING
        db.session.commit()
        
        logger.info(f"Starting audio processing for job {job_id}")
        
        # Stage 1: Audio Preprocessing (10% progress)
        self.update_progress(
            job_id=job_id,
            stage=ProcessingStageEnum.PREPROCESSING,
            progress=10,
            message="Preprocessing audio file..."
        )
        
        # Analyze audio file first
        audio_metadata = audio_service.analyze_audio_file(job.file_path)
        logger.info(f"Audio analysis for job {job_id}: {audio_metadata}")
        
        # Preprocess audio file
        processed_audio_path = audio_service.preprocess_for_speechkit(job.file_path)
        
        # Stage 2: Upload to API (20% progress)
        self.update_progress(
            job_id=job_id,
            stage=ProcessingStageEnum.UPLOADING_TO_API,
            progress=20,
            message="Initializing transcription..."
        )
        
        # Create processing service
        processing_service = create_processing_service(
            provider="yandex",
            api_key=config.YANDEX_API_KEY,
            folder_id=config.YANDEX_FOLDER_ID
        )
        
        # Stage 3: Process with API (30-80% progress)
        self.update_progress(
            job_id=job_id,
            stage=ProcessingStageEnum.PROCESSING_API,
            progress=30,
            message="Processing with Yandex SpeechKit..."
        )
        
        # Process audio with Yandex SpeechKit
        job_result = processing_service.process_audio(job)
        
        # Stage 4: Download and Process Results (90% progress)
        self.update_progress(
            job_id=job_id,
            stage=ProcessingStageEnum.DOWNLOADING_RESULTS,
            progress=90,
            message="Processing transcription results..."
        )
        
        # Save result to database
        db.session.add(job_result)
        
        # Stage 5: Postprocessing and Completion (100% progress)
        self.update_progress(
            job_id=job_id,
            stage=ProcessingStageEnum.POSTPROCESSING,
            progress=95,
            message="Finalizing processing..."
        )
        
        # Update job status
        job.status = JobStatus.COMPLETED
        job.progress = 100
        db.session.commit()
        
        # Cleanup temporary files
        cleanup_temp_files(processed_audio_path)
        
        # Final update
        self.update_progress(
            job_id=job_id,
            stage=ProcessingStageEnum.COMPLETED,
            progress=100,
            message="Processing completed successfully"
        )
        
        logger.info(f"Audio processing completed for job {job_id}")
        
        return {
            'job_id': job_id,
            'status': 'completed',
            'result_id': job_result.id if job_result else None,
            'confidence_score': job_result.confidence_score if job_result else None,
            'word_count': job_result.word_count if job_result else None
        }
        
    except Exception as exc:
        logger.error(f"Audio processing failed for job {job_id}: {exc}")
        
        # Update job status to failed
        try:
            job = Job.query.get(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                db.session.commit()
        except Exception as db_exc:
            logger.error(f"Failed to update job status: {db_exc}")
        
        raise exc


def preprocess_audio_file(input_path: Path) -> Path:
    """
    Preprocess audio file for Yandex SpeechKit.
    
    Args:
        input_path: Path to input audio file
        
    Returns:
        Path to processed audio file
        
    Raises:
        subprocess.CalledProcessError: If FFmpeg processing fails
        FileNotFoundError: If input file doesn't exist
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input audio file not found: {input_path}")
    
    logger.info(f"Preprocessing audio file: {input_path}")
    
    # Create temporary file for processed audio
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        output_path = Path(temp_file.name)
    
    try:
        # FFmpeg command for optimal Yandex SpeechKit processing
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '16000',          # 16kHz sample rate
            '-ac', '1',              # Mono channel
            '-af', 'volume=0.8',     # Normalize volume
            '-y',                    # Overwrite output file
            str(output_path)
        ]
        
        logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
        
        # Run FFmpeg with timeout
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        logger.info(f"Audio preprocessing completed: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as exc:
        logger.error(f"FFmpeg processing failed: {exc.stderr}")
        # Clean up output file if it was created
        if output_path.exists():
            output_path.unlink()
        raise
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg processing timed out")
        # Clean up output file if it was created
        if output_path.exists():
            output_path.unlink()
        raise


def cleanup_temp_files(*file_paths: Path) -> None:
    """
    Clean up temporary files created during processing.
    
    Args:
        *file_paths: Paths to temporary files to delete
    """
    for file_path in file_paths:
        if file_path and file_path.exists():
            try:
                file_path.unlink()
                logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as exc:
                logger.warning(f"Failed to clean up file {file_path}: {exc}")


@celery_app.task(bind=True, base=BaseProcessingTask)
def cancel_processing_task(self, job_id: str) -> Dict[str, Any]:
    """
    Cancel ongoing processing task.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Cancellation result dictionary
    """
    try:
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        logger.info(f"Cancelling processing for job {job_id}")
        
        # Update job status
        job.status = JobStatus.CANCELLED
        job.error_message = "Processing cancelled by user"
        db.session.commit()
        
        # Send cancellation update
        self.update_progress(
            job_id=job_id,
            stage=ProcessingStageEnum.CANCELLED,
            progress=0,
            message="Processing cancelled"
        )
        
        return {
            'job_id': job_id,
            'status': 'cancelled'
        }
        
    except Exception as exc:
        logger.error(f"Failed to cancel job {job_id}: {exc}")
        raise


__all__ = [
    'process_audio_task',
    'cancel_processing_task',
    'preprocess_audio_file',
    'cleanup_temp_files'
]