"""Custom exception classes for the transcriber application."""


class TranscriberError(Exception):
    """Base exception for transcriber application."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary format for API responses."""
        return {
            'error': self.error_code,
            'message': self.message,
            'details': self.details
        }


class FileValidationError(TranscriberError):
    """Raised when file validation fails."""
    pass


class FileSizeError(FileValidationError):
    """Raised when file size exceeds limits."""
    pass


class FileFormatError(FileValidationError):
    """Raised when file format is not supported."""
    pass


class FileContentError(FileValidationError):
    """Raised when file content is invalid or corrupted."""
    pass


class StorageError(TranscriberError):
    """Raised when file storage operations fail."""
    pass


class ProcessingError(TranscriberError):
    """Raised when processing operations fail."""
    pass


class DatabaseError(TranscriberError):
    """Raised when database operations fail."""
    pass


class ExternalAPIError(TranscriberError):
    """Raised when external API calls fail."""
    pass


class ConfigurationError(TranscriberError):
    """Raised when configuration is invalid or missing."""
    pass


class AuthenticationError(TranscriberError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(TranscriberError):
    """Raised when authorization fails."""
    pass


class RateLimitError(TranscriberError):
    """Raised when rate limits are exceeded."""
    pass


class JobNotFoundError(TranscriberError):
    """Raised when requested job is not found."""
    pass


class JobStateError(TranscriberError):
    """Raised when job state transition is invalid."""
    pass


class ExportError(TranscriberError):
    """Raised when export operations fail."""
    pass