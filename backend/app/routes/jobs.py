"""Job management routes for status tracking and results retrieval."""

from datetime import datetime
from flask import Blueprint, jsonify, render_template, current_app, abort, request
from sqlalchemy.exc import SQLAlchemyError

from backend.app.models.job import Job
from backend.app.models.result import JobResult
from backend.app.models.enums import JobStatus
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
        
        # Calculate progress percentage
        progress = 0
        if job.status == JobStatus.UPLOADED:
            progress = 10
        elif job.status == JobStatus.PROCESSING:
            progress = 50
        elif job.status == JobStatus.COMPLETED:
            progress = 100
        elif job.status == JobStatus.FAILED:
            progress = 0
        
        # Prepare response
        response_data = {
            'success': True,
            'job': {
                'job_id': job.job_id,
                'filename': job.original_filename,
                'status': job.status.value,
                'progress': progress,
                'created_at': job.created_at.isoformat(),
                'updated_at': job.updated_at.isoformat() if job.updated_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'file_info': {
                    'size': job.file_size,
                    'format': job.file_format
                },
                'error_message': job.error_message,
                'metadata': job.metadata or {}
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
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            return jsonify({
                'success': False,
                'error': 'Cannot cancel job',
                'message': f'Job is already {job.status.value} and cannot be cancelled'
            }), 400
        
        # Update job status
        job.status = JobStatus.FAILED
        job.error_message = 'Job cancelled by user'
        job.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        current_app.logger.info(f"Job {job_id} cancelled by user")
        
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