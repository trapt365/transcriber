"""Job management routes for status tracking and results retrieval."""

from datetime import datetime
from flask import Blueprint, jsonify, render_template, current_app, abort, request
from sqlalchemy.exc import SQLAlchemyError

from backend.app.models.job import Job
from backend.app.models.result import JobResult
from backend.app.models.enums import JobStatus, ExportFormat
from backend.app.services.progress_service import ProgressService
from backend.app.services.transcript_formatter import TranscriptFormatter
from backend.app.services.export_service import TranscriptExportService
from backend.app.utils.exceptions import ExportError
from backend.extensions import db

# Create blueprint
jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('/status/<job_id>')
def job_status_page(job_id):
    """Render job status page."""
    try:
        job = Job.query.filter_by(job_id=job_id).first()
        if not job:
            abort(404)
        
        return render_template('status.html', job=job)
        
    except Exception as e:
        current_app.logger.error(f"Error rendering status page for job {job_id}: {str(e)}")
        abort(500)


@jobs_bp.route('/transcript/<job_id>')
def job_transcript_page(job_id):
    """Render job transcript page."""
    try:
        job = Job.query.filter_by(job_id=job_id).first()
        if not job:
            abort(404)
        
        # Check if job is completed
        if job.status != JobStatus.COMPLETED.value:
            return render_template('status.html', job=job)
        
        return render_template('transcript.html', job=job)
        
    except Exception as e:
        current_app.logger.error(f"Error rendering transcript page for job {job_id}: {str(e)}")
        abort(500)


@jobs_bp.route('/api/v1/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get detailed job status and information.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        JSON response with job details and status
    """
    try:
        job = Job.query.filter_by(job_id=job_id).first()
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found',
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        # Get job result if available
        result = None
        if job.status == JobStatus.COMPLETED:
            job_result = JobResult.query.filter_by(job_id=job.id).first()
            if job_result:
                result = {
                    'transcript': job_result.transcript_text,
                    'confidence_score': job_result.confidence_score,
                    'language_detected': job_result.language_detected,
                    'processing_duration': job_result.processing_duration,
                    'word_count': job_result.word_count,
                    'speakers': [
                        {
                            'speaker_id': speaker.speaker_id,
                            'name': speaker.name,
                            'confidence': speaker.confidence
                        }
                        for speaker in job_result.speakers
                    ],
                    'segments': [
                        {
                            'start_time': segment.start_time,
                            'end_time': segment.end_time,
                            'text': segment.text,
                            'confidence': segment.confidence,
                            'speaker_id': segment.speaker_id
                        }
                        for segment in job_result.segments
                    ]
                }
        
        # Use actual progress from job model
        progress = job.progress
        
        # Update estimated completion if not set
        if not job.estimated_completion and job.status in [JobStatus.UPLOADED.value, JobStatus.PROCESSING.value]:
            estimated_completion = ProgressService.calculate_estimated_completion(job)
            if estimated_completion:
                job.estimated_completion = estimated_completion
                db.session.commit()
        
        # Prepare response
        response_data = {
            'success': True,
            'job': {
                'job_id': job.job_id,
                'filename': job.original_filename,
                'status': job.status,
                'progress': progress,
                'processing_phase': job.processing_phase,
                'estimated_completion': job.estimated_completion.isoformat() if job.estimated_completion else None,
                'queue_position': job.queue_position,
                'can_cancel': job.can_cancel,
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'file_info': {
                    'size': job.file_size,
                    'format': job.file_format
                },
                'error_message': job.error_message
            }
        }
        
        # Add result data if available
        if result:
            response_data['result'] = result
        
        return jsonify(response_data), 200
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error getting job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': 'Failed to retrieve job information'
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error getting job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500


@jobs_bp.route('/api/v1/jobs/<job_id>/result', methods=['GET'])
def get_job_result(job_id):
    """Get job result details.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        JSON response with detailed transcription results
    """
    try:
        job = Job.query.filter_by(job_id=job_id).first()
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found',
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        if job.status != JobStatus.COMPLETED:
            return jsonify({
                'success': False,
                'error': 'Job not completed',
                'message': f'Job is currently {job.status.value}. Results are only available for completed jobs.'
            }), 400
        
        # Get job result
        job_result = JobResult.query.filter_by(job_id=job.id).first()
        
        if not job_result:
            return jsonify({
                'success': False,
                'error': 'Result not found',
                'message': 'Job completed but result data is not available'
            }), 404
        
        # Prepare detailed result response
        result_data = {
            'success': True,
            'job_id': job.job_id,
            'filename': job.original_filename,
            'result': {
                'transcript': job_result.transcript_text,
                'confidence_score': job_result.confidence_score,
                'language_detected': job_result.language_detected,
                'processing_duration': job_result.processing_duration,
                'word_count': job_result.word_count,
                'created_at': job_result.created_at.isoformat(),
                'speakers': [
                    {
                        'speaker_id': speaker.speaker_id,
                        'name': speaker.name,
                        'confidence': speaker.confidence,
                        'total_speaking_time': speaker.total_speaking_time
                    }
                    for speaker in job_result.speakers
                ],
                'segments': [
                    {
                        'id': segment.id,
                        'start_time': segment.start_time,
                        'end_time': segment.end_time,
                        'text': segment.text,
                        'confidence': segment.confidence,
                        'speaker_id': segment.speaker_id,
                        'word_count': len(segment.text.split()) if segment.text else 0
                    }
                    for segment in job_result.segments
                ],
                'statistics': {
                    'total_speakers': len(job_result.speakers),
                    'total_segments': len(job_result.segments),
                    'average_confidence': job_result.confidence_score,
                    'total_duration': max([s.end_time for s in job_result.segments], default=0),
                    'words_per_minute': (
                        job_result.word_count / (job_result.processing_duration / 60)
                        if job_result.processing_duration and job_result.processing_duration > 0
                        else 0
                    )
                }
            }
        }
        
        return jsonify(result_data), 200
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error getting result for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': 'Failed to retrieve job result'
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error getting result for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500


@jobs_bp.route('/api/v1/jobs/<job_id>/transcript', methods=['GET'])
def get_job_transcript(job_id):
    """Get formatted transcript for a completed job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        JSON response with formatted transcript data
    """
    try:
        job = Job.query.filter_by(job_id=job_id).first()
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found',
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        # Check if job is completed
        if job.status != JobStatus.COMPLETED.value:
            return jsonify({
                'success': False,
                'error': 'Job not completed',
                'message': f'Job is currently {job.status}. Transcript is only available for completed jobs.'
            }), 400
        
        # Initialize formatter and get transcript data
        formatter = TranscriptFormatter(db.session)
        
        # Validate transcript data first
        validation_result = formatter.validate_transcript_data(job_id)
        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'error': 'Invalid transcript data',
                'message': 'Transcript data validation failed',
                'validation_errors': validation_result['errors']
            }), 400
        
        # Format transcript
        transcript_data = formatter.format_transcript(job_id)
        
        # Prepare response with all required data
        response_data = {
            'success': True,
            'job_id': job_id,
            'filename': job.original_filename,
            'transcript': {
                'formatted_text': transcript_data['formatted_text'],
                'preview': transcript_data['preview'],
                'segments': transcript_data['segments'],
                'speaker_count': transcript_data['speaker_count'],
                'total_segments': transcript_data['total_segments'],
                'total_duration': transcript_data['total_duration'],
                'confidence_score': transcript_data['confidence_score']
            },
            'metadata': transcript_data['metadata'],
            'validation': {
                'warnings': validation_result.get('warnings', []),
                'segment_count': validation_result['segment_count'],
                'speaker_count': validation_result['speaker_count']
            }
        }
        
        current_app.logger.info(f"Successfully retrieved transcript for job {job_id}")
        return jsonify(response_data), 200
        
    except ValueError as e:
        # Handle formatter validation errors
        current_app.logger.warning(f"Transcript validation error for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Transcript validation error',
            'message': str(e)
        }), 400
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error getting transcript for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': 'Failed to retrieve transcript data'
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error getting transcript for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred while processing transcript'
        }), 500


@jobs_bp.route('/api/v1/jobs', methods=['GET'])
def list_jobs():
    """List recent jobs with basic information.
    
    Query parameters:
        limit: Maximum number of jobs to return (default: 50, max: 100)
        offset: Number of jobs to skip (default: 0)
        status: Filter by job status
        
    Returns:
        JSON response with list of jobs
    """
    try:
        # Parse query parameters
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status')
        
        # Build query
        query = Job.query.order_by(Job.created_at.desc())
        
        if status_filter:
            try:
                status_enum = JobStatus(status_filter)
                query = query.filter(Job.status == status_enum)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid status',
                    'message': f'Invalid status: {status_filter}'
                }), 400
        
        # Execute query with pagination
        jobs = query.offset(offset).limit(limit).all()
        total_count = query.count()
        
        # Prepare response
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                'job_id': job.job_id,
                'filename': job.original_filename,
                'status': job.status.value,
                'created_at': job.created_at.isoformat(),
                'updated_at': job.updated_at.isoformat() if job.updated_at else None,
                'file_size': job.file_size,
                'file_format': job.file_format
            })
        
        return jsonify({
            'success': True,
            'jobs': jobs_data,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            }
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid parameter',
            'message': str(e)
        }), 400
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error listing jobs: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': 'Failed to retrieve jobs list'
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error listing jobs: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500


@jobs_bp.route('/api/v1/jobs/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a job that is not yet completed.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        JSON response confirming cancellation
    """
    try:
        job = Job.query.filter_by(job_id=job_id).first()
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found',
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        # Check if job can be cancelled
        if not job.can_cancel or job.status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
            return jsonify({
                'success': False,
                'error': 'Cannot cancel job',
                'message': f'Job is {job.status} and cannot be cancelled'
            }), 400
        
        # Update job status
        if job.update_status(JobStatus.CANCELLED, 'Job cancelled by user'):
            job.can_cancel = False
            job.progress = 0
            db.session.commit()
            
            # Emit real-time cancellation update
            from backend.app.routes.realtime import emit_job_status_update
            emit_job_status_update(job_id, {
                'status': JobStatus.CANCELLED.value,
                'progress': 0,
                'processing_phase': 'cancelled',
                'error_message': 'Job cancelled by user',
                'can_cancel': False
            })
            
            current_app.logger.info(f"Job {job_id} cancelled by user")
        else:
            return jsonify({
                'success': False,
                'error': 'Cannot cancel job',
                'message': 'Job status transition not allowed'
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Job cancelled successfully',
            'job_id': job_id
        }), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error cancelling job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': 'Failed to cancel job'
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error cancelling job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500


@jobs_bp.route('/api/v1/jobs/<job_id>/queue-position', methods=['GET'])
def get_queue_position(job_id):
    """Get current queue position for a job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        JSON response with queue position information
    """
    try:
        job = Job.query.filter_by(job_id=job_id).first()
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found',
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        # Calculate queue position if job is uploaded
        queue_position = None
        estimated_wait = None
        
        if job.status == JobStatus.UPLOADED.value:
            # Count jobs uploaded before this one
            earlier_jobs = Job.query.filter(
                Job.status == JobStatus.UPLOADED.value,
                Job.created_at < job.created_at
            ).count()
            
            queue_position = earlier_jobs + 1
            
            # Update job's queue position
            job.queue_position = queue_position
            db.session.commit()
            
            # Estimate wait time (5 minutes per job ahead)
            estimated_wait = queue_position * 300  # 5 minutes in seconds
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'queue_position': queue_position,
            'estimated_wait_seconds': estimated_wait,
            'status': job.status
        }), 200
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error getting queue position for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': 'Failed to retrieve queue position'
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error getting queue position for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500


@jobs_bp.route('/api/v1/system/queue-status', methods=['GET'])
def get_queue_status():
    """Get overall queue status information.
    
    Returns:
        JSON response with queue statistics
    """
    try:
        queue_stats = ProgressService.get_queue_status()
        
        return jsonify({
            'success': True,
            'queue_status': queue_stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting queue status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'Failed to retrieve queue status'
        }), 500


@jobs_bp.route('/api/v1/jobs/<job_id>/export/<format_type>', methods=['GET'])
def export_transcript(job_id, format_type):
    """Export transcript in specified format for download.
    
    Args:
        job_id: Unique job identifier
        format_type: Export format (txt, json, srt, vtt, csv)
        
    Returns:
        File download response with appropriate headers
    """
    try:
        job = Job.query.filter_by(job_id=job_id).first()
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found',
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        # Check if job is completed
        if job.status != JobStatus.COMPLETED.value:
            return jsonify({
                'success': False,
                'error': 'Job not completed',
                'message': f'Job is currently {job.status}. Export is only available for completed jobs.'
            }), 400
        
        # Validate format type
        try:
            export_format = ExportFormat(format_type.lower())
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid format',
                'message': f'Unsupported export format: {format_type}. Supported formats: txt, json, srt, vtt, csv'
            }), 400
        
        # Initialize export service
        export_service = TranscriptExportService()
        
        # Generate export content
        try:
            export_content = export_service.export_transcript(job, export_format)
        except ExportError as e:
            current_app.logger.error(f"Export error for job {job_id}, format {format_type}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Export failed',
                'message': str(e)
            }), 400
        
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"transcript_{job_id}_{timestamp}.{export_format.value}"
        
        # Set content type and headers based on format
        content_type_map = {
            ExportFormat.JSON: 'application/json',
            ExportFormat.TXT: 'text/plain',
            ExportFormat.SRT: 'application/x-subrip',
            ExportFormat.VTT: 'text/vtt',
            ExportFormat.CSV: 'text/csv'
        }
        
        content_type = content_type_map.get(export_format, 'application/octet-stream')
        
        # Create response with proper headers
        from flask import Response
        
        response = Response(
            export_content,
            mimetype=f'{content_type}; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': f'{content_type}; charset=utf-8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        )
        
        current_app.logger.info(f"Successfully exported transcript for job {job_id} in format {format_type}")
        return response
        
    except ExportError as e:
        current_app.logger.error(f"Export error for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Export failed',
            'message': str(e)
        }), 400
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error exporting job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': 'Failed to retrieve job data for export'
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error exporting job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred during export'
        }), 500


@jobs_bp.route('/api/v1/jobs/<job_id>/export-formats', methods=['GET'])
def get_export_formats(job_id):
    """Get available export formats and statistics for a job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        JSON response with available formats and export statistics
    """
    try:
        job = Job.query.filter_by(job_id=job_id).first()
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found',
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        # Check if job is completed
        if job.status != JobStatus.COMPLETED.value:
            return jsonify({
                'success': False,
                'error': 'Job not completed',
                'message': f'Job is currently {job.status}. Export information is only available for completed jobs.'
            }), 400
        
        # Initialize export service
        export_service = TranscriptExportService()
        
        # Get export statistics
        try:
            export_stats = export_service.get_export_stats(job)
        except ExportError as e:
            return jsonify({
                'success': False,
                'error': 'Export validation failed',
                'message': str(e)
            }), 400
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'export_formats': {
                'available': [fmt.value for fmt in export_service.get_supported_formats()],
                'timed_formats': ['srt', 'vtt'] if export_stats['can_export_timed'] else [],
                'basic_formats': ['txt', 'json', 'csv']
            },
            'statistics': export_stats,
            'download_urls': {
                fmt.value: f"/api/v1/jobs/{job_id}/export/{fmt.value}"
                for fmt in export_service.get_supported_formats()
            }
        }), 200
        
    except ExportError as e:
        current_app.logger.error(f"Export validation error for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Export validation failed',
            'message': str(e)
        }), 400
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error getting export formats for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': 'Failed to retrieve job data'
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error getting export formats for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500


# Error handlers
@jobs_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    return jsonify({
        'success': False,
        'error': 'Not found',
        'message': 'The requested resource was not found'
    }), 404


@jobs_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500