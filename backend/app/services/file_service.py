"""File handling service for secure upload, validation, and storage management."""

import os
import uuid
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, BinaryIO
from datetime import datetime, timedelta

from backend.app.utils.exceptions import (
    FileValidationError, FileSizeError, FileFormatError, 
    FileContentError, StorageError
)
from backend.app.models.enums import AudioFormat


class FileService:
    """Service for handling file operations with validation and security."""
    
    # Supported audio MIME types
    SUPPORTED_MIME_TYPES = {
        'audio/wav': AudioFormat.WAV,
        'audio/wave': AudioFormat.WAV,
        'audio/x-wav': AudioFormat.WAV,
        'audio/mpeg': AudioFormat.MP3,
        'audio/mp3': AudioFormat.MP3,
        'audio/flac': AudioFormat.FLAC,
        'audio/x-flac': AudioFormat.FLAC,
        'audio/mp4': AudioFormat.M4A,
        'audio/m4a': AudioFormat.M4A,
        'audio/ogg': AudioFormat.OGG,
        'audio/x-ogg': AudioFormat.OGG
    }
    
    # File extensions to MIME types mapping
    EXTENSION_TO_MIME = {
        '.wav': 'audio/wav',
        '.mp3': 'audio/mpeg',
        '.flac': 'audio/flac',
        '.m4a': 'audio/mp4',
        '.ogg': 'audio/ogg'
    }
    
    def __init__(self, upload_folder: str, max_file_size: int = 500 * 1024 * 1024):
        """
        Initialize FileService.
        
        Args:
            upload_folder: Directory for storing uploaded files
            max_file_size: Maximum file size in bytes (default: 500MB)
        """
        self.upload_folder = Path(upload_folder)
        self.max_file_size = max_file_size
        
        # Ensure upload folder exists
        self.upload_folder.mkdir(parents=True, exist_ok=True)
    
    def validate_file(self, file_obj: BinaryIO, filename: str) -> Dict[str, Any]:
        """
        Validate uploaded file for format, size, and content.
        
        Args:
            file_obj: File object to validate
            filename: Original filename
            
        Returns:
            Dictionary with file metadata
            
        Raises:
            FileValidationError: If validation fails
        """
        metadata = {}
        
        # Basic filename validation
        if not filename or filename.strip() == '':
            raise FileValidationError("Filename cannot be empty")
        
        # Get file extension
        file_ext = Path(filename).suffix.lower()
        if not file_ext:
            raise FileFormatError("File must have an extension")
        
        metadata['original_filename'] = filename
        metadata['file_extension'] = file_ext
        
        # Validate file extension
        if file_ext not in self.EXTENSION_TO_MIME:
            supported_formats = ', '.join(self.EXTENSION_TO_MIME.keys())
            raise FileFormatError(
                f"Unsupported file format: {file_ext}. "
                f"Supported formats: {supported_formats}"
            )
        
        # Get expected MIME type from extension
        expected_mime = self.EXTENSION_TO_MIME[file_ext]
        metadata['expected_mime_type'] = expected_mime
        metadata['audio_format'] = self.SUPPORTED_MIME_TYPES[expected_mime]
        
        # Validate file size
        file_obj.seek(0, 2)  # Seek to end
        file_size = file_obj.tell()
        file_obj.seek(0)  # Reset to beginning
        
        if file_size == 0:
            raise FileValidationError("File cannot be empty")
        
        if file_size > self.max_file_size:
            raise FileSizeError(
                f"File size ({file_size} bytes) exceeds maximum allowed "
                f"size ({self.max_file_size} bytes)"
            )
        
        metadata['file_size'] = file_size
        
        # Basic content validation (magic number check)
        self._validate_file_content(file_obj, expected_mime, file_ext)
        
        # Calculate file hash for integrity
        file_obj.seek(0)
        file_hash = hashlib.md5()
        for chunk in iter(lambda: file_obj.read(4096), b""):
            file_hash.update(chunk)
        file_obj.seek(0)
        
        metadata['file_hash'] = file_hash.hexdigest()
        metadata['validated_at'] = datetime.utcnow().isoformat()
        
        return metadata
    
    def _validate_file_content(self, file_obj: BinaryIO, expected_mime: str, 
                              file_ext: str) -> None:
        """
        Validate file content using magic numbers.
        
        Args:
            file_obj: File object to validate
            expected_mime: Expected MIME type
            file_ext: File extension
            
        Raises:
            FileContentError: If content validation fails
        """
        file_obj.seek(0)
        header = file_obj.read(12)  # Read first 12 bytes for magic number
        file_obj.seek(0)
        
        if len(header) < 4:
            raise FileContentError("File too small to contain valid header")
        
        # Magic number validation
        magic_numbers = {
            '.wav': [b'RIFF', b'WAVE'],
            '.mp3': [b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'],
            '.flac': [b'fLaC'],
            '.m4a': [b'ftyp', b'\x00\x00\x00'],
            '.ogg': [b'OggS']
        }
        
        if file_ext in magic_numbers:
            valid_headers = magic_numbers[file_ext]
            header_valid = False
            
            for valid_header in valid_headers:
                if file_ext == '.wav':
                    # WAV files have RIFF at start and WAVE at offset 8
                    if header.startswith(b'RIFF') and header[8:12] == b'WAVE':
                        header_valid = True
                        break
                elif file_ext == '.m4a':
                    # M4A files have ftyp at offset 4 or specific pattern
                    if (header[4:8] == b'ftyp' or 
                        header.startswith(b'\x00\x00\x00')):
                        header_valid = True
                        break
                else:
                    if header.startswith(valid_header):
                        header_valid = True
                        break
            
            if not header_valid:
                raise FileContentError(
                    f"File content does not match expected format {file_ext}"
                )
    
    def save_file(self, file_obj: BinaryIO, filename: str, 
                  job_id: str = None) -> Dict[str, Any]:
        """
        Save file to secure storage with UUID-based naming.
        
        Args:
            file_obj: File object to save
            filename: Original filename
            job_id: Optional job ID for naming
            
        Returns:
            Dictionary with file storage information
            
        Raises:
            StorageError: If file saving fails
        """
        try:
            # Validate file first
            metadata = self.validate_file(file_obj, filename)
            
            # Generate secure filename
            if job_id is None:
                job_id = str(uuid.uuid4())
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            file_ext = metadata['file_extension']
            secure_filename = f"{job_id}_{timestamp}{file_ext}"
            
            # Create file path
            file_path = self.upload_folder / secure_filename
            
            # Ensure file doesn't already exist
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                file_path = original_path.parent / f"{stem}_{counter}{file_ext}"
                counter += 1
            
            # Save file
            file_obj.seek(0)
            with open(file_path, 'wb') as f:
                while True:
                    chunk = file_obj.read(4096)
                    if not chunk:
                        break
                    f.write(chunk)
            
            # Verify file was saved correctly
            if not file_path.exists():
                raise StorageError("File was not saved successfully")
            
            saved_size = file_path.stat().st_size
            if saved_size != metadata['file_size']:
                file_path.unlink()  # Delete corrupted file
                raise StorageError(
                    f"File size mismatch: expected {metadata['file_size']}, "
                    f"got {saved_size}"
                )
            
            storage_info = {
                'job_id': job_id,
                'filename': secure_filename,
                'file_path': str(file_path),
                'relative_path': str(file_path.relative_to(self.upload_folder)),
                'saved_at': datetime.utcnow().isoformat(),
                'storage_folder': str(self.upload_folder)
            }
            
            # Merge with validation metadata
            storage_info.update(metadata)
            
            return storage_info
            
        except Exception as e:
            if isinstance(e, (FileValidationError, StorageError)):
                raise
            raise StorageError(f"Failed to save file: {str(e)}") from e
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if file was deleted, False if file didn't exist
            
        Raises:
            StorageError: If deletion fails
        """
        try:
            path = Path(file_path)
            
            # Security check - ensure file is in upload folder
            if not str(path.resolve()).startswith(str(self.upload_folder.resolve())):
                raise StorageError("File path is outside upload folder")
            
            if not path.exists():
                return False
            
            path.unlink()
            return True
            
        except Exception as e:
            if isinstance(e, StorageError):
                raise
            raise StorageError(f"Failed to delete file: {str(e)}") from e
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about stored file.
        
        Args:
            file_path: Path to file
            
        Returns:
            File information dictionary or None if file doesn't exist
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return None
            
            stat = path.stat()
            
            return {
                'file_path': str(path),
                'filename': path.name,
                'file_size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'exists': True
            }
            
        except Exception:
            return None
    
    def cleanup_expired_files(self, expiration_hours: int = 24) -> Dict[str, Any]:
        """
        Clean up files older than specified hours.
        
        Args:
            expiration_hours: Hours after which files should be deleted
            
        Returns:
            Cleanup statistics
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=expiration_hours)
            cutoff_timestamp = cutoff_time.timestamp()
            
            deleted_count = 0
            deleted_size = 0
            errors = []
            
            for file_path in self.upload_folder.iterdir():
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        if stat.st_mtime < cutoff_timestamp:
                            file_size = stat.st_size
                            file_path.unlink()
                            deleted_count += 1
                            deleted_size += file_size
                    except Exception as e:
                        errors.append(f"Failed to delete {file_path}: {str(e)}")
            
            return {
                'deleted_files': deleted_count,
                'deleted_size_bytes': deleted_size,
                'cutoff_time': cutoff_time.isoformat(),
                'errors': errors,
                'cleanup_completed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise StorageError(f"Cleanup operation failed: {str(e)}") from e
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage folder statistics.
        
        Returns:
            Storage statistics dictionary
        """
        try:
            total_files = 0
            total_size = 0
            file_types = {}
            
            for file_path in self.upload_folder.iterdir():
                if file_path.is_file():
                    total_files += 1
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    
                    file_ext = file_path.suffix.lower()
                    if file_ext in file_types:
                        file_types[file_ext]['count'] += 1
                        file_types[file_ext]['size'] += file_size
                    else:
                        file_types[file_ext] = {'count': 1, 'size': file_size}
            
            return {
                'upload_folder': str(self.upload_folder),
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_types': file_types,
                'max_file_size_bytes': self.max_file_size,
                'stats_generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise StorageError(f"Failed to get storage stats: {str(e)}") from e