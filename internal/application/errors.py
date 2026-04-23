class ApplicationError(Exception):
    """Base application-layer exception."""


class DuplicateRoomNumberError(ApplicationError):
    """Raised when a room number collides with an existing record."""


class RoomNotFoundError(ApplicationError):
    """Raised when a room identifier does not exist."""


class RoomNotAvailableError(ApplicationError):
    """Raised when a room cannot be reserved for a booking."""
