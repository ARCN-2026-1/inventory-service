from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from internal.interfaces.messaging.contracts import (
    BookingCreatedMessage,
    FailedRoom,
    InventoryResponseMessage,
)


def test_booking_created_message_accepts_booking_service_aliases() -> None:
    message = BookingCreatedMessage.from_payload(
        {
            "eventId": "ca7ebdca-4807-48dc-8bb5-7ef87f42f412",
            "eventType": "BOOKING_Ok",
            "timestamp": "2026-04-24T12:00:00+00:00",
            "bookingId": "2651ef51-e6d8-43d7-9d67-31dba2027708",
            "customerId": "0cc5d9bd-c24d-45fd-aaf2-c8177d44da6f",
            "startDate": "2026-04-25",
            "endDate": "2026-04-28",
            "roomIds": [
                "a8b05f28-f03d-4cd0-8a02-0a7253d8fb4d",
                "7403c2ff-4f7f-4440-bb32-90a55fffe755",
            ],
        }
    )

    assert message.event_id == UUID("ca7ebdca-4807-48dc-8bb5-7ef87f42f412")
    assert message.event_type == "BOOKING_Ok"
    assert message.booking_id == UUID("2651ef51-e6d8-43d7-9d67-31dba2027708")
    assert message.customer_id == UUID("0cc5d9bd-c24d-45fd-aaf2-c8177d44da6f")
    assert message.timestamp == datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    assert message.start_date == date(2026, 4, 25)
    assert message.end_date == date(2026, 4, 28)
    assert message.room_ids == [
        UUID("a8b05f28-f03d-4cd0-8a02-0a7253d8fb4d"),
        UUID("7403c2ff-4f7f-4440-bb32-90a55fffe755"),
    ]


def test_booking_created_message_accepts_corrected_failed_alias_too() -> None:
    message = BookingCreatedMessage.from_payload(
        {
            "eventId": "ca7ebdca-4807-48dc-8bb5-7ef87f42f412",
            "eventType": "BOOKING_FAILED",
            "timestamp": "2026-04-24T12:00:00+00:00",
            "bookingId": "2651ef51-e6d8-43d7-9d67-31dba2027708",
            "customerId": "0cc5d9bd-c24d-45fd-aaf2-c8177d44da6f",
            "startDate": "2026-04-25",
            "endDate": "2026-04-28",
            "roomIds": ["a8b05f28-f03d-4cd0-8a02-0a7253d8fb4d"],
        }
    )

    assert message.event_type == "BOOKING_FAILED"


def test_inventory_response_message_serializes_full_booking_payload_shape() -> None:
    response = InventoryResponseMessage(
        event_id=UUID("0a268f65-f12d-4dfd-b482-88b92c5f4d56"),
        event_type="BOOKING_FALED",
        timestamp=datetime(2026, 4, 24, 13, 45, tzinfo=timezone.utc),
        booking_id=UUID("093c0c94-7d34-4f96-91fd-8559e028e2cb"),
        status="FAILED",
        reservation_confirmed=False,
        failed_rooms=[
            FailedRoom(
                room_id=UUID("c19d682e-c719-43be-a703-7b8cc8a43fc3"),
                reason="Room not found",
            )
        ],
    )

    assert response.to_payload() == {
        "eventId": "0a268f65-f12d-4dfd-b482-88b92c5f4d56",
        "eventType": "BOOKING_FALED",
        "timestamp": "2026-04-24T13:45:00+00:00",
        "bookingId": "093c0c94-7d34-4f96-91fd-8559e028e2cb",
        "status": "FAILED",
        "reservationConfirmed": False,
        "failedRooms": [
            {
                "roomId": "c19d682e-c719-43be-a703-7b8cc8a43fc3",
                "reason": "Room not found",
            }
        ],
    }
