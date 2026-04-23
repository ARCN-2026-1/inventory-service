from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReserveRoomsCommand:
    booking_id: UUID
    room_ids: list[UUID]
    requested_at: datetime
