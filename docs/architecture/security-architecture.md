# Security Architecture

## Input Validation & Sanitization

```python
class FileValidator:
    ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac'}
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    
    @staticmethod
    def validate_upload(file) -> None:
        # Check file extension
        if not FileValidator._has_allowed_extension(file.filename):
            raise FileValidationError("Unsupported file format")
        
        # Check file size
        if file.content_length > FileValidator.MAX_FILE_SIZE:
            raise FileValidationError("File too large")
        
        # Validate audio content
        if not FileValidator._is_valid_audio(file):
            raise FileValidationError("Invalid audio file")
    
    @staticmethod
    def _is_valid_audio(file) -> bool:
        """Validate file is actually audio using librosa"""
        try:
            # Read first 10 seconds to validate
            y, sr = librosa.load(file, duration=10.0)
            return len(y) > 0 and sr > 0
        except Exception:
            return False
```

## Data Protection

```python
class SecureFileManager:
    def __init__(self):
        self.upload_dir = os.path.join(app.config['UPLOAD_FOLDER'])
        os.makedirs(self.upload_dir, mode=0o700, exist_ok=True)
    
    def save_file(self, file, job_id: str) -> str:
        """Save file with secure naming and permissions"""
        # Generate secure filename
        secure_name = f"{job_id}_{int(time.time())}.{file.filename.rsplit('.', 1)[1].lower()}"
        file_path = os.path.join(self.upload_dir, secure_name)
        
        # Save with restricted permissions
        file.save(file_path)
        os.chmod(file_path, 0o600)  # Read/write for owner only
        
        return file_path
    
    def encrypt_file(self, file_path: str) -> str:
        """Encrypt file at rest (production enhancement)"""
        from cryptography.fernet import Fernet
        key = os.getenv('FILE_ENCRYPTION_KEY').encode()
        fernet = Fernet(key)
        
        with open(file_path, 'rb') as f:
            encrypted_data = fernet.encrypt(f.read())
        
        encrypted_path = file_path + '.enc'
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        os.remove(file_path)  # Remove unencrypted file
        return encrypted_path
```

## API Security

```python
from flask_limiter import Limiter
from flask_talisman import Talisman
