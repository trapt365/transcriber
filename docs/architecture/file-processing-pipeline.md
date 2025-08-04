# File Processing Pipeline

## Upload Workflow

```python
def process_upload(file) -> str:
    """
    Upload processing pipeline
    Returns: job_id for tracking
    """
    # 1. Validation
    validate_file_format(file)
    validate_file_size(file)
    validate_audio_content(file)
    
    # 2. Storage
    job_id = str(uuid.uuid4())
    file_path = save_file_securely(file, job_id)
    
    # 3. Database Record
    job = create_job_record(job_id, file.filename, file_path)
    
    # 4. Queue for Processing
    process_audio_task.delay(job_id)
    
    return job_id
```

## Processing Pipeline

```python
@celery.task(bind=True)
def process_audio_task(self, job_id: str):
    """
    Main audio processing task
    """
    try:
        # Update status
        update_job_status(job_id, JobStatus.PROCESSING, progress=10)
        
        # 1. Preprocess Audio
        audio_path = preprocess_audio(job_id)
        update_job_status(job_id, JobStatus.PROCESSING, progress=30)
        
        # 2. Yandex API Call
        transcript_data = call_yandex_api(audio_path)
        update_job_status(job_id, JobStatus.PROCESSING, progress=70)
        
        # 3. Process Results
        process_transcript_data(job_id, transcript_data)
        update_job_status(job_id, JobStatus.PROCESSING, progress=90)
        
        # 4. Generate Exports
        generate_export_formats(job_id)
        update_job_status(job_id, JobStatus.COMPLETED, progress=100)
        
    except Exception as e:
        handle_processing_error(job_id, e)
        update_job_status(job_id, JobStatus.FAILED, error=str(e))
```

## Yandex API Integration

```python
class YandexSpeechKitClient:
    def __init__(self):
        self.api_key = os.getenv('YANDEX_API_KEY')
        self.session = requests.Session()
        self.session.mount('https://', HTTPAdapter(max_retries=3))
    
    def transcribe_audio(self, audio_path: str) -> dict:
        """
        Transcribe audio with retry logic and error handling
        """
        config = {
            'specification': {
                'languageCode': 'auto',  # Universal mode
                'model': 'general',
                'profanityFilter': False,
                'literature_text': True,
                'format': 'lpcm',
                'sampleRateHertz': 16000,
            },
            'recognition_config': {
                'enable_speaker_diarization': True,
                'max_speaker_count': 10,
                'enable_automatic_punctuation': True,
            }
        }
        
        with open(audio_path, 'rb') as audio_file:
            response = self._call_api_with_retry(audio_file, config)
            
        return self._process_response(response)
    
    def _call_api_with_retry(self, audio_file, config) -> dict:
        """Implements exponential backoff retry"""
        for attempt in range(3):
            try:
                response = self.session.post(
                    'https://stt.api.cloud.yandex.net/speech/v1/stt:recognize',
                    headers={'Authorization': f'Api-Key {self.api_key}'},
                    files={'audio': audio_file},
                    data={'config': json.dumps(config)},
                    timeout=300  # 5 minutes timeout
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == 2:  # Last attempt
                    raise ExternalAPIError(f"Yandex API failed: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff
```

## File Cleanup Automation

```python
@celery.task
def cleanup_expired_files():
    """
    Automated cleanup task - runs every hour
    """
    expired_jobs = Job.query.filter(
        Job.expires_at < datetime.utcnow(),
        Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED])
    ).all()
    
    for job in expired_jobs:
        try:
            # Delete physical files
            if os.path.exists(job.file_path):
                os.remove(job.file_path)
            
            # Clean export files
            export_dir = f"exports/{job.job_id}"
            if os.path.exists(export_dir):
                shutil.rmtree(export_dir)
            
            # Update database
            job.status = JobStatus.DELETED
            db.session.commit()
            
            logger.info(f"Cleaned up job {job.job_id}")
            
        except Exception as e:
            logger.error(f"Cleanup failed for job {job.job_id}: {str(e)}")
