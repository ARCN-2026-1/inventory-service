from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from internal.domain.valueobjects.date_range import DateRange


@dataclass(frozen=True, slots=True)
class RoomAvailability:
    date_range: DateRange
    booking_id: UUID | None = None
