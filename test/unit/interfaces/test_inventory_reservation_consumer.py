from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from internal.application.commands.release_rooms import ReleaseRoomsCommand
from internal.application.commands.reserve_rooms import ReserveRoomsCommand
from internal.application.usecases.release_rooms import ReleaseRoomsResult
from internal.application.usecases.reserve_rooms import (
    FailedRoomReservation,
    ReserveRoomsResult,
)
from internal.interfaces.messaging.inventory_reservation_consumer import (
    InventoryReservationHandler,
)


class ReserveRoomsSpy:
    def __init__(self, result: ReserveRoomsResult | None = None) -> None:
        self.result = result or ReserveRoomsResult(
            reservation_confirmed=True,
            failed_rooms=[],
        )
        self.commands: list[ReserveRoomsCommand] = []
        self.error: Exception | None = None

    def execute(self, command: ReserveRoomsCommand) -> ReserveRoomsResult:
        self.commands.append(command)
        if self.error is not None:
            raise self.error
        return self.result


class ReleaseRoomsSpy:
    def __init__(self, result: ReleaseRoomsResult | None = None) -> None:
        self.result = result or ReleaseRoomsResult(released_room_ids=[])
        self.commands: list[ReleaseRoomsCommand] = []
        self.error: Exception | None = None

    def execute(self, command: ReleaseRoomsCommand) -> ReleaseRoomsResult:
        self.commands.append(command)
        if self.error is not None:
            raise self.error
        return self.result


def test_handler_discards_invalid_payload_without_response() -> None:
    handler = InventoryReservationHandler(
        reserve_rooms=ReserveRoomsSpy(),
        release_rooms=ReleaseRoomsSpy(),
    )

    result = handler.handle({"eventType": "BOOKING_Ok"})

    assert result.should_ack is True
    assert result.requeue is False
    assert result.response_event is None


def test_handler_acknowledges_booking_ok_and_returns_inventory_response() -> None:
    reserve_rooms = ReserveRoomsSpy(
        ReserveRoomsResult(
            reservation_confirmed=False,
            failed_rooms=[
                FailedRoomReservation(
                    room_id=UUID("cb72aecb-66cf-4ddd-bdfd-b42bdf9ccfc9"),
                    reason="Room is already reserved",
                )
            ],
        )
    )
    handler = InventoryReservationHandler(
        reserve_rooms=reserve_rooms,
        release_rooms=ReleaseRoomsSpy(),
    )

    result = handler.handle(_booking_payload(event_type="BOOKING_Ok"))

    assert result.should_ack is True
    assert result.requeue is False
    assert result.response_event is not None
    assert result.response_event.event_type == "BOOKING_Ok"
    assert result.response_event.booking_id == UUID(
        "5d94bbee-54ce-4f9d-bc93-062f5075dbf4"
    )
    assert result.response_event.reservation_confirmed is False
    assert len(result.response_event.failed_rooms) == 1
    assert result.response_event.failed_rooms[0].room_id == UUID(
        "cb72aecb-66cf-4ddd-bdfd-b42bdf9ccfc9"
    )
    assert result.response_event.failed_rooms[0].reason == "Room is already reserved"
    command = reserve_rooms.commands[0]
    assert command.booking_id == UUID("5d94bbee-54ce-4f9d-bc93-062f5075dbf4")
    assert command.room_ids == [UUID("61a0d564-cb2a-4115-acf5-415f1c2c4b9d")]


def test_handler_acknowledges_successful_booking_ok_with_confirmed_response() -> None:
    reserve_rooms = ReserveRoomsSpy(
        ReserveRoomsResult(
            reservation_confirmed=True,
            failed_rooms=[],
        )
    )
    handler = InventoryReservationHandler(
        reserve_rooms=reserve_rooms,
        release_rooms=ReleaseRoomsSpy(),
    )

    result = handler.handle(_booking_payload(event_type="BOOKING_Ok"))

    assert result.should_ack is True
    assert result.requeue is False
    assert result.response_event is not None
    assert result.response_event.event_type == "BOOKING_Ok"
    assert result.response_event.booking_id == UUID(
        "5d94bbee-54ce-4f9d-bc93-062f5075dbf4"
    )
    assert result.response_event.reservation_confirmed is True
    assert result.response_event.status == "CONFIRMED"
    assert result.response_event.failed_rooms == []
    command = reserve_rooms.commands[0]
    assert command.booking_id == UUID("5d94bbee-54ce-4f9d-bc93-062f5075dbf4")
    assert command.room_ids == [UUID("61a0d564-cb2a-4115-acf5-415f1c2c4b9d")]


def test_handler_acknowledges_booking_faled_and_releases_rooms() -> None:
    release_rooms = ReleaseRoomsSpy(
        ReleaseRoomsResult(
            released_room_ids=[UUID("61a0d564-cb2a-4115-acf5-415f1c2c4b9d")]
        )
    )
    handler = InventoryReservationHandler(
        reserve_rooms=ReserveRoomsSpy(),
        release_rooms=release_rooms,
    )

    result = handler.handle(_booking_payload(event_type="BOOKING_FALED"))

    assert result.should_ack is True
    assert result.requeue is False
    assert result.response_event is not None
    assert result.response_event.event_type == "BOOKING_FALED"
    assert result.response_event.reservation_confirmed is False
    assert result.response_event.failed_rooms == []
    command = release_rooms.commands[0]
    assert command.booking_id == UUID("5d94bbee-54ce-4f9d-bc93-062f5075dbf4")
    assert command.room_ids == [UUID("61a0d564-cb2a-4115-acf5-415f1c2c4b9d")]


def test_handler_acknowledges_booking_failed_and_releases_rooms() -> None:
    release_rooms = ReleaseRoomsSpy(
        ReleaseRoomsResult(
            released_room_ids=[UUID("61a0d564-cb2a-4115-acf5-415f1c2c4b9d")]
        )
    )
    handler = InventoryReservationHandler(
        reserve_rooms=ReserveRoomsSpy(),
        release_rooms=release_rooms,
    )

    result = handler.handle(_booking_payload(event_type="BOOKING_FAILED"))

    assert result.should_ack is True
    assert result.requeue is False
    assert result.response_event is not None
    assert result.response_event.event_type == "BOOKING_FAILED"
    assert result.response_event.reservation_confirmed is False
    assert result.response_event.failed_rooms == []
    command = release_rooms.commands[0]
    assert command.booking_id == UUID("5d94bbee-54ce-4f9d-bc93-062f5075dbf4")
    assert command.room_ids == [UUID("61a0d564-cb2a-4115-acf5-415f1c2c4b9d")]


def test_handler_nacks_transient_processing_errors_for_requeue() -> None:
    reserve_rooms = ReserveRoomsSpy()
    reserve_rooms.error = RuntimeError("database unavailable")
    handler = InventoryReservationHandler(
        reserve_rooms=reserve_rooms,
        release_rooms=ReleaseRoomsSpy(),
    )

    result = handler.handle(_booking_payload(event_type="BOOKING_Ok"))

    assert result.should_ack is False
    assert result.requeue is True
    assert result.response_event is None


def _booking_payload(*, event_type: str) -> dict[str, object]:
    return {
        "eventId": "1d7d151e-e186-4768-b596-5fcb332af4d7",
        "eventType": event_type,
        "timestamp": datetime(2026, 4, 24, 10, 0, tzinfo=timezone.utc).isoformat(),
        "bookingId": "5d94bbee-54ce-4f9d-bc93-062f5075dbf4",
        "customerId": "ca7f4e7f-b0e2-49f5-b479-fcde4f4b90af",
        "startDate": date(2026, 4, 25).isoformat(),
        "endDate": date(2026, 4, 28).isoformat(),
        "roomIds": ["61a0d564-cb2a-4115-acf5-415f1c2c4b9d"],
    }
