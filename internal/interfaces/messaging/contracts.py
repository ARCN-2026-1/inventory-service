from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, cast
from uuid import UUID, uuid4


def _require_field(payload: dict[str, object], field_name: str) -> object:
    if field_name not in payload:
        raise ValueError(f"Missing required field: {field_name}")
    return payload[field_name]


_BOOKING_EVENT_TYPES = {"BOOKING_Ok", "BOOKING_FALED", "BOOKING_FAILED"}


def _normalize_event_type(raw_value: object) -> str:
    value = str(raw_value)
    if value not in _BOOKING_EVENT_TYPES:
        raise ValueError(f"Unsupported booking event type: {value}")
    return value


@dataclass(frozen=True, slots=True)
class FailedRoom:
    room_id: UUID
    reason: str

    def to_payload(self) -> dict[str, str]:
        return {"roomId": str(self.room_id), "reason": self.reason}


@dataclass(frozen=True, slots=True)
class BookingCreatedMessage:
    event_id: UUID
    event_type: str
    timestamp: datetime
    booking_id: UUID
    customer_id: UUID
    start_date: date
    end_date: date
    room_ids: list[UUID]

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "BookingCreatedMessage":
        event_type = _normalize_event_type(_require_field(payload, "eventType"))
        room_ids_raw = _require_field(payload, "roomIds")
        if not isinstance(room_ids_raw, list):
            raise ValueError("roomIds must be a list")

        return cls(
            event_id=UUID(str(_require_field(payload, "eventId"))),
            event_type=event_type,
            timestamp=datetime.fromisoformat(str(_require_field(payload, "timestamp"))),
            booking_id=UUID(str(_require_field(payload, "bookingId"))),
            customer_id=UUID(str(_require_field(payload, "customerId"))),
            start_date=date.fromisoformat(str(_require_field(payload, "startDate"))),
            end_date=date.fromisoformat(str(_require_field(payload, "endDate"))),
            room_ids=[UUID(str(room_id)) for room_id in cast(list[Any], room_ids_raw)],
        )


@dataclass(frozen=True, slots=True)
class InventoryResponseMessage:
    event_id: UUID
    event_type: str
    timestamp: datetime
    booking_id: UUID
    status: str
    reservation_confirmed: bool
    failed_rooms: list[FailedRoom]

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        booking_id: UUID,
        reservation_confirmed: bool,
        failed_rooms: list[FailedRoom],
        timestamp: datetime,
    ) -> "InventoryResponseMessage":
        _ = _normalize_event_type(event_type)
        return cls(
            event_id=uuid4(),
            event_type=event_type,
            timestamp=timestamp,
            booking_id=booking_id,
            status="CONFIRMED" if reservation_confirmed else "FAILED",
            reservation_confirmed=reservation_confirmed,
            failed_rooms=failed_rooms,
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "eventId": str(self.event_id),
            "eventType": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "bookingId": str(self.booking_id),
            "status": self.status,
            "reservationConfirmed": self.reservation_confirmed,
            "failedRooms": [room.to_payload() for room in self.failed_rooms],
        }
