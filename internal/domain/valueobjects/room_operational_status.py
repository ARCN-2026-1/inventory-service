from enum import StrEnum


class RoomOperationalStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
