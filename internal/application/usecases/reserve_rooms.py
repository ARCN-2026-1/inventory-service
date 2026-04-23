from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from uuid import UUID

from internal.application.commands.reserve_rooms import ReserveRoomsCommand
from internal.application.errors import RoomNotAvailableError, RoomNotFoundError
from internal.domain.errors import DomainRuleViolation
from internal.domain.repositories.room_repository import RoomRepository

ROOM_NOT_FOUND_REASON: Final[str] = "Room not found"
ROOM_ALREADY_RESERVED_REASON: Final[str] = "Room is already reserved"


@dataclass(frozen=True, slots=True)
class FailedRoomReservation:
    room_id: UUID
    reason: str


@dataclass(frozen=True, slots=True)
class ReserveRoomsResult:
    reservation_confirmed: bool
    failed_rooms: list[FailedRoomReservation]


class ReserveRoomsUseCase:
    def __init__(self, repository: RoomRepository) -> None:
        self._repository = repository

    def execute(self, command: ReserveRoomsCommand) -> ReserveRoomsResult:
        failed_rooms: list[FailedRoomReservation] = []

        for room_id in command.room_ids:
            room = self._repository.get_by_id(room_id)
            if room is None:
                failed_rooms.append(
                    FailedRoomReservation(
                        room_id=room_id,
                        reason=self._map_failure_reason(
                            RoomNotFoundError(ROOM_NOT_FOUND_REASON)
                        ),
                    )
                )
                continue

            try:
                room.reserve(
                    booking_id=command.booking_id,
                    reserved_at=command.requested_at,
                )
            except DomainRuleViolation as error:
                failed_rooms.append(
                    FailedRoomReservation(
                        room_id=room_id,
                        reason=self._map_failure_reason(
                            RoomNotAvailableError(str(error))
                        ),
                    )
                )
                continue

            self._repository.save(room)

        return ReserveRoomsResult(
            reservation_confirmed=len(failed_rooms) == 0,
            failed_rooms=failed_rooms,
        )

    def _map_failure_reason(
        self, error: RoomNotFoundError | RoomNotAvailableError
    ) -> str:
        if isinstance(error, RoomNotFoundError):
            return ROOM_NOT_FOUND_REASON
        if "already reserved" in str(error):
            return ROOM_ALREADY_RESERVED_REASON
        return str(error)
