#!/usr/bin/env python3
"""Start Celery worker process."""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.celery_factory import create_celery_worker_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == '__main__':
    # Create Celery app with Flask context
    celery_app = create_celery_worker_app()
    
    # Start worker
    # This can be overridden with command line arguments
    worker_args = [
        'worker',
        '--loglevel=info',
        '--concurrency=4',
        '--queues=transcription,maintenance',
        '--hostname=worker@%h'
    ]
    
    # Add any additional arguments from command line
    if len(sys.argv) > 1:
        worker_args.extend(sys.argv[1:])
    
    print(f"Starting Celery worker with args: {' '.join(worker_args)}")
    celery_app.start(worker_args)