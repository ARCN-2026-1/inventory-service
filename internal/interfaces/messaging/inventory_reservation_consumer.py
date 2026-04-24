from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


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
        payload_snapshot = _build_payload_snapshot(payload)
        logger.info(
            "Received inventory reservation payload=%s",
            payload_snapshot,
        )
        try:
            message = BookingCreatedMessage.from_payload(payload)
        except (TypeError, ValueError, KeyError) as error:
            logger.warning(
                "Discarding inventory reservation message due to validation "
                "failure error=%s payload=%s",
                error,
                payload_snapshot,
            )
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
                logger.info(
                    "Inventory reservation processed event_type=%s booking_id=%s "
                    "reservation_confirmed=%s failed_rooms=%s",
                    message.event_type,
                    message.booking_id,
                    result.reservation_confirmed,
                    len(result.failed_rooms),
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
            response_event = InventoryResponseMessage.create(
                event_type=message.event_type,
                booking_id=message.booking_id,
                reservation_confirmed=False,
                failed_rooms=[],
                timestamp=message.timestamp,
            )
            logger.info(
                "Inventory release processed event_type=%s booking_id=%s "
                "released_rooms=%s",
                message.event_type,
                message.booking_id,
                len(release_result.released_room_ids),
            )
            return HandlingResult(
                should_ack=True,
                requeue=False,
                response_event=response_event,
            )
        except Exception:
            logger.exception(
                "Inventory reservation processing failed booking_id=%s event_type=%s",
                payload.get("bookingId"),
                payload.get("eventType"),
            )
            return HandlingResult(should_ack=False, requeue=True)


def _build_payload_snapshot(payload: dict[str, object]) -> dict[str, object | None]:
    room_ids = payload.get("roomIds")

    return {
        "eventId": payload.get("eventId"),
        "eventType": payload.get("eventType"),
        "bookingId": payload.get("bookingId"),
        "customerId": payload.get("customerId"),
        "roomIdsCount": len(room_ids) if isinstance(room_ids, list) else None,
        "timestamp": payload.get("timestamp"),
    }
