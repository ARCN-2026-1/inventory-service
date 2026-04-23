from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from internal.application.commands.release_rooms import ReleaseRoomsCommand
from internal.domain.errors import DomainRuleViolation
from internal.domain.repositories.room_repository import RoomRepository


@dataclass(frozen=True, slots=True)
class ReleaseRoomsResult:
    released_room_ids: list[UUID]


class ReleaseRoomsUseCase:
    def __init__(self, repository: RoomRepository) -> None:
        self._repository = repository

    def execute(self, command: ReleaseRoomsCommand) -> ReleaseRoomsResult:
        released_room_ids: list[UUID] = []

        for room_id in command.room_ids:
            room = self._repository.get_by_id(room_id)
            if room is None or room.availability is None:
                continue
            if room.availability.booking_id is None:
                continue

            try:
                room.release(
                    booking_id=command.booking_id,
                    released_at=command.released_at,
                )
            except DomainRuleViolation:
                continue

            self._repository.save(room)
            released_room_ids.append(room_id)

        return ReleaseRoomsResult(released_room_ids=released_room_ids)
