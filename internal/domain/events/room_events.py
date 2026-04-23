from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from internal.domain.valueobjects.room_operational_status import RoomOperationalStatus


@dataclass(frozen=True, slots=True)
class RoomRegistered:
    room_id: UUID
    room_number: str
    registered_at: datetime


@dataclass(frozen=True, slots=True)
class RoomReserved:
    room_id: UUID
    booking_id: UUID
    reserved_at: datetime


@dataclass(frozen=True, slots=True)
class RoomReleased:
    room_id: UUID
    booking_id: UUID
    released_at: datetime


@dataclass(frozen=True, slots=True)
class RoomStatusChanged:
    room_id: UUID
    old_status: RoomOperationalStatus
    new_status: RoomOperationalStatus
    changed_at: datetime
