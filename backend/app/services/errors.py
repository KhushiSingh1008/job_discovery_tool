"""Domain errors; the API layer maps them to HTTP status codes."""


class DomainError(Exception):
    """Base class for expected, user-facing failures."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class InvalidTransitionError(DomainError):
    pass
