"""Real-time WebSocket communication routes."""

from flask import request
from flask_socketio import emit, join_room, leave_room, disconnect
from backend.extensions import socketio
from backend.app.models import Job
from backend.extensions import db
import logging

logger = logging.getLogger(__name__)


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'status': 'connected', 'sid': request.sid})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on('subscribe_job_status')
def handle_job_status_subscription(data):
    """Subscribe to job status updates."""
    try:
        job_id = data.get('job_id')
        if not job_id:
            emit('error', {'message': 'job_id is required'})
            return
        
        # Verify job exists
        job = Job.find_by_job_id(job_id)
        if not job:
            emit('error', {'message': 'Job not found'})
            return
        
        # Join room for this job
        join_room(job_id)
        logger.info(f"Client {request.sid} subscribed to job {job_id}")
        
        # Send current status immediately
        emit('job_status_update', {
            'job_id': job_id,
            'status': job.status,
            'progress': job.progress,
            'processing_phase': job.processing_phase,
            'estimated_completion': job.estimated_completion.isoformat() if job.estimated_completion else None,
            'queue_position': job.queue_position,
            'can_cancel': job.can_cancel,
            'error_message': job.error_message
        })
        
    except Exception as e:
        logger.error(f"Error in job status subscription: {str(e)}")
        emit('error', {'message': 'Failed to subscribe to job status'})


@socketio.on('unsubscribe_job_status')
def handle_job_status_unsubscription(data):
    """Unsubscribe from job status updates."""
    try:
        job_id = data.get('job_id')
        if job_id:
            leave_room(job_id)
            logger.info(f"Client {request.sid} unsubscribed from job {job_id}")
            emit('unsubscribed', {'job_id': job_id})
    except Exception as e:
        logger.error(f"Error in job status unsubscription: {str(e)}")


def emit_job_status_update(job_id: str, status_data: dict):
    """Emit job status update to all subscribers."""
    try:
        socketio.emit('job_status_update', {
            'job_id': job_id,
            **status_data
        }, room=job_id)
        logger.debug(f"Emitted status update for job {job_id}: {status_data}")
    except Exception as e:
        logger.error(f"Error emitting job status update: {str(e)}")


def emit_queue_position_update(job_id: str, position: int, estimated_wait: int = None):
    """Emit queue position update to subscribers."""
    try:
        data = {
            'job_id': job_id,
            'queue_position': position
        }
        if estimated_wait is not None:
            data['estimated_wait_seconds'] = estimated_wait
        
        socketio.emit('queue_position_update', data, room=job_id)
        logger.debug(f"Emitted queue position update for job {job_id}: position {position}")
    except Exception as e:
        logger.error(f"Error emitting queue position update: {str(e)}")


def emit_processing_error(job_id: str, error_message: str, suggested_actions: list = None):
    """Emit processing error to subscribers."""
    try:
        data = {
            'job_id': job_id,
            'error_message': error_message,
            'suggested_actions': suggested_actions or []
        }
        
        socketio.emit('processing_error', data, room=job_id)
        logger.debug(f"Emitted processing error for job {job_id}: {error_message}")
    except Exception as e:
        logger.error(f"Error emitting processing error: {str(e)}")