from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from internal.application.commands.release_rooms import ReleaseRoomsCommand
from internal.application.commands.reserve_rooms import ReserveRoomsCommand
from internal.application.usecases.release_rooms import ReleaseRoomsResult
from internal.application.usecases.reserve_rooms import ReserveRoomsResult
from internal.interfaces.messaging.contracts import (
    BookingCreatedMessage,
    FailedRoom,
    InventoryResponseMessage,
)


class ReserveRoomsExecutor(Protocol):
    def execute(self, command: ReserveRoomsCommand) -> ReserveRoomsResult: ...


class ReleaseRoomsExecutor(Protocol):
    def execute(self, command: ReleaseRoomsCommand) -> ReleaseRoomsResult: ...


@dataclass(frozen=True, slots=True)
class HandlingResult:
    should_ack: bool
    requeue: bool
    response_event: InventoryResponseMessage | None = None


class InventoryReservationHandler:
    def __init__(
        self,
        *,
        reserve_rooms: ReserveRoomsExecutor,
        release_rooms: ReleaseRoomsExecutor,
    ) -> None:
        self._reserve_rooms = reserve_rooms
        self._release_rooms = release_rooms

    def handle(self, payload: dict[str, object]) -> HandlingResult:
        try:
            message = BookingCreatedMessage.from_payload(payload)
        except (TypeError, ValueError, KeyError):
            return HandlingResult(should_ack=True, requeue=False)

        try:
            if message.event_type == "BOOKING_Ok":
                result = self._reserve_rooms.execute(
                    ReserveRoomsCommand(
                        booking_id=message.booking_id,
                        room_ids=message.room_ids,
                        requested_at=message.timestamp,
                    )
                )
                response_event = InventoryResponseMessage.create(
                    event_type=message.event_type,
                    booking_id=message.booking_id,
                    reservation_confirmed=result.reservation_confirmed,
                    failed_rooms=[
                        FailedRoom(room_id=item.room_id, reason=item.reason)
                        for item in result.failed_rooms
                    ],
                    timestamp=message.timestamp,
                )
                return HandlingResult(
                    should_ack=True,
                    requeue=False,
                    response_event=response_event,
                )

            release_result = self._release_rooms.execute(
                ReleaseRoomsCommand(
                    booking_id=message.booking_id,
                    room_ids=message.room_ids,
                    released_at=message.timestamp,
                )
            )
            _ = release_result
            response_event = InventoryResponseMessage.create(
                event_type=message.event_type,
                booking_id=message.booking_id,
                reservation_confirmed=False,
                failed_rooms=[],
                timestamp=message.timestamp,
            )
            return HandlingResult(
                should_ack=True,
                requeue=False,
                response_event=response_event,
            )
        except Exception:
            return HandlingResult(should_ack=False, requeue=True)
