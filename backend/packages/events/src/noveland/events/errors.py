from __future__ import annotations


class EventStoreError(RuntimeError):
    """Base error for event store failures."""


class EventValidationError(ValueError):
    """Raised when event input does not match the event contract."""


class EventAppendError(EventStoreError):
    """Raised when an event cannot be appended."""


class SnapshotValidationError(ValueError):
    """Raised when snapshot input does not match the snapshot contract."""
