class MediaError(Exception):
    """Base media package error."""


class MediaValidationError(ValueError, MediaError):
    """Raised when media input violates the media contract."""


class MediaNotFoundError(MediaError):
    """Raised when a media record cannot be found in scope."""


class MediaConflictError(MediaError):
    """Raised when a media operation conflicts with current state."""


class MediaStorageError(MediaError):
    """Raised when media object storage fails."""
