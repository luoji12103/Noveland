class MemoryError(RuntimeError):
    """Base error for memory operations."""


class MemoryValidationError(ValueError):
    """Raised when memory input is invalid."""


class MemoryBackendUnavailableError(MemoryError):
    """Raised when the configured memory backend cannot be initialized."""


class MemoryWriteFailedError(MemoryError):
    """Raised when a memory write fails."""


class MemorySearchFailedError(MemoryError):
    """Raised when a memory search fails."""


class MemoryPrivacyDeletionError(MemoryError):
    """Raised when scoped deletion fails."""


class MemoryContractViolationError(MemoryError):
    """Raised when a backend returns an invalid response shape."""
