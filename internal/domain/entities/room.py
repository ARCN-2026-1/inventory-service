from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from internal.domain.entities.room_availability import RoomAvailability
from internal.domain.errors import DomainRuleViolation
from internal.domain.events.room_events import (
    RoomRegistered,
    RoomReleased,
    RoomReserved,
    RoomStatusChanged,
)
from internal.domain.valueobjects.date_range import DateRange
from internal.domain.valueobjects.money import Money
from internal.domain.valueobjects.room_operational_status import RoomOperationalStatus
from internal.domain.valueobjects.room_type import RoomType


@dataclass(slots=True)
class Room:
    room_id: UUID
    room_number: str
    room_type: RoomType
    capacity: int
    base_price: Money
    operational_status: RoomOperationalStatus
    registered_at: datetime
    availability: RoomAvailability | None = None
    _domain_events: list[Any] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.room_number.strip():
            raise DomainRuleViolation("Room number is required")
        if self.capacity <= 0:
            raise DomainRuleViolation("Room capacity must be greater than zero")

    @classmethod
    def register(
        cls,
        *,
        room_id: UUID,
        room_number: str,
        room_type: RoomType,
        capacity: int,
        price_amount: Decimal,
        price_currency: str,
        operational_status: RoomOperationalStatus,
        registered_at: datetime,
        availability_start: date | None = None,
        availability_end: date | None = None,
    ) -> "Room":
        availability = None
        if availability_start is not None or availability_end is not None:
            if availability_start is None or availability_end is None:
                raise DomainRuleViolation(
                    "Availability start and end dates must be provided together"
                )
            availability = RoomAvailability(
                date_range=DateRange(
                    start_date=availability_start,
                    end_date=availability_end,
                )
            )

        room = cls(
            room_id=room_id,
            room_number=room_number,
            room_type=room_type,
            capacity=capacity,
            base_price=Money(amount=price_amount, currency=price_currency),
            operational_status=operational_status,
            registered_at=registered_at,
            availability=availability,
        )
        room._record_event(
            RoomRegistered(
                room_id=room.room_id,
                room_number=room.room_number,
                registered_at=room.registered_at,
            )
        )
        return room

    def pull_domain_events(self) -> list[Any]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    def reserve(self, *, booking_id: UUID, reserved_at: datetime) -> None:
        availability = self._require_availability()
        if availability.booking_id == booking_id:
            return
        if availability.booking_id is not None:
            raise DomainRuleViolation(f"Room {self.room_number} is already reserved")

        self.availability = RoomAvailability(
            date_range=availability.date_range,
            booking_id=booking_id,
        )
        self._record_event(
            RoomReserved(
                room_id=self.room_id,
                booking_id=booking_id,
                reserved_at=reserved_at,
            )
        )

    def release(self, *, booking_id: UUID, released_at: datetime) -> None:
        availability = self._require_availability()
        if availability.booking_id is None:
            return
        if availability.booking_id != booking_id:
            raise DomainRuleViolation(
                f"Room {self.room_number} is reserved for a different booking"
            )

        self.availability = RoomAvailability(date_range=availability.date_range)
        self._record_event(
            RoomReleased(
                room_id=self.room_id,
                booking_id=booking_id,
                released_at=released_at,
            )
        )

    def update_operational_status(
        self,
        *,
        new_status: RoomOperationalStatus,
        changed_at: datetime,
    ) -> None:
        if self.operational_status is new_status:
            return

        old_status = self.operational_status
        self.operational_status = new_status
        self._record_event(
            RoomStatusChanged(
                room_id=self.room_id,
                old_status=old_status,
                new_status=new_status,
                changed_at=changed_at,
            )
        )

    def _require_availability(self) -> RoomAvailability:
        if self.availability is None:
            raise DomainRuleViolation(
                f"Room {self.room_number} does not have availability configured"
            )
        return self.availability

    def _record_event(self, event: Any) -> None:
        self._domain_events.append(event)
