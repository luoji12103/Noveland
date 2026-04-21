class ConversationError(RuntimeError):
    """Base error for conversation session operations."""


class ConversationValidationError(ValueError):
    """Raised when a conversation contract or invariant is invalid."""


class ConversationStateError(ConversationError):
    """Raised when a session transition is not allowed."""
