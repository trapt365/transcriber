"""Upload routes for file handling and job creation."""

import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, current_app
from werkzeug.utils import secure_filename
from marshmallow import Schema, fields, ValidationError

from backend.app.services.file_service import FileService
from backend.app.models.job import Job
from backend.app.models.enums import JobStatus
from backend.tasks.audio_processing import process_audio_task
from backend.app.utils.exceptions import (
    FileValidationError, 
    ProcessingError, 
    TranscriberError
)
from backend.extensions import db

# Create blueprint
upload_bp = Blueprint('upload', __name__)

# Validation schemas
class FileUploadSchema(Schema):
    """Schema for file upload validation."""
    metadata = fields.Dict(missing={})


@upload_bp.route('/upload', methods=['GET'])
def upload_page():
    """Render the upload page."""
    return render_template('index.html')


@upload_bp.route('/api/v1/upload', methods=['POST'])
def upload_file():
    """Handle file upload and create processing job.
    
    Returns:
        JSON response with job_id for successful uploads
        JSON error response for failures
    """
    try:
        # Validate request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided',
                'message': 'Please select a file to upload'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected',
                'message': 'Please select a file to upload'
            }), 400
        
        # Initialize services
        file_service = FileService(
            upload_folder=current_app.config['UPLOAD_FOLDER'],
            max_file_size=current_app.config.get('MAX_FILE_SIZE', 500 * 1024 * 1024)
        )
        
        # Use existing save_file method (includes validation)
        try:
            file_info = file_service.save_file(file, file.filename)
            # Add format field for compatibility
            if 'audio_format' in file_info:
                file_info['format'] = file_info['audio_format'].value
        except FileValidationError as e:
            return jsonify({
                'success': False,
                'error': 'File validation failed',
                'message': str(e)
            }), 400
        
        # Create job record
        try:
            job = Job(
                job_id=str(uuid.uuid4()),
                filename=file_info['filename'],
                original_filename=file_info['original_filename'],
                file_path=file_info['file_path'],
                file_size=file_info['file_size'],
                file_format=file_info.get('format', 'unknown'),
                status=JobStatus.UPLOADED,
                created_at=datetime.utcnow(),
                metadata={
                    'client_metadata': request.form.get('metadata', {}),
                    'upload_info': {
                        'content_type': file.content_type,
                        'user_agent': request.headers.get('User-Agent'),
                        'ip_address': request.remote_addr
                    }
                }
            )
            
            db.session.add(job)
            db.session.commit()
            
            current_app.logger.info(f"Job created successfully: {job.job_id}")
            
        except Exception as e:
            # Clean up uploaded file on database error
            try:
                os.remove(file_info['file_path'])
            except OSError:
                pass
            
            current_app.logger.error(f"Database error creating job: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Database error',
                'message': 'Failed to create processing job'
            }), 500
        
        # Queue processing job with Celery (async)
        try:
            # Update job status to queued
            job.status = JobStatus.QUEUED
            db.session.commit()
            
            # Start Celery task
            task_result = process_audio_task.delay(job.id)  # Use job.id (integer) instead of job_id (UUID string)
            current_app.logger.info(f"Job queued for processing: {job.job_id}, task_id: {task_result.id}")
        except Exception as e:
            current_app.logger.warning(f"Failed to queue job {job.job_id}: {str(e)}")
            # Don't fail the upload if queuing fails - job can be processed later
        
        # Return success response
        return jsonify({
            'success': True,
            'job_id': job.job_id,
            'filename': job.original_filename,
            'message': 'File uploaded successfully and queued for processing',
            'status_url': f'/status/{job.job_id}',
            'file_info': {
                'size': file_info['file_size'],
                'format': file_info.get('format', 'unknown')
            }
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'message': 'Invalid request data',
            'details': e.messages
        }), 400
        
    except TranscriberError as e:
        current_app.logger.error(f"Transcriber error in upload: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Processing error',
            'message': str(e)
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error in upload: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please try again.'
        }), 500


@upload_bp.route('/api/v1/upload/validate', methods=['POST'])
def validate_file():
    """Validate file without uploading.
    
    Useful for pre-upload validation.
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'valid': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'valid': False,
                'error': 'No file selected'
            }), 400
        
        # Initialize file service
        file_service = FileService(
            upload_folder=current_app.config['UPLOAD_FOLDER'],
            max_file_size=current_app.config.get('MAX_FILE_SIZE', 500 * 1024 * 1024)
        )
        
        # Validate file (without saving)
        try:
            is_valid, errors = file_service.validate_file(file)
            
            if is_valid:
                return jsonify({
                    'valid': True,
                    'message': 'File is valid for upload',
                    'file_info': {
                        'name': secure_filename(file.filename),
                        'size': len(file.read()),
                        'type': file.content_type
                    }
                }), 200
            else:
                return jsonify({
                    'valid': False,
                    'errors': errors
                }), 400
                
        except FileValidationError as e:
            return jsonify({
                'valid': False,
                'error': str(e)
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in file validation: {str(e)}")
        return jsonify({
            'valid': False,
            'error': 'Validation failed'
        }), 500


@upload_bp.route('/api/v1/upload/status', methods=['GET'])
def upload_status():
    """Get upload service status and configuration."""
    try:
        file_service = FileService(
            upload_folder=current_app.config['UPLOAD_FOLDER']
        )
        
        return jsonify({
            'status': 'available',
            'max_file_size': current_app.config.get('MAX_FILE_SIZE', 500 * 1024 * 1024),
            'supported_formats': file_service.SUPPORTED_FORMATS,
            'upload_folder_exists': os.path.exists(current_app.config['UPLOAD_FOLDER']),
            'disk_space_available': file_service.get_available_disk_space()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting upload status: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


# Error handlers for the blueprint
@upload_bp.errorhandler(413)
def file_too_large(error):
    """Handle file too large error."""
    return jsonify({
        'success': False,
        'error': 'File too large',
        'message': f'File size exceeds maximum limit of {current_app.config.get("MAX_CONTENT_LENGTH", "unknown")}'
    }), 413


@upload_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'message': 'Invalid request format or parameters'
    }), 400


@upload_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again.'
    }), 500