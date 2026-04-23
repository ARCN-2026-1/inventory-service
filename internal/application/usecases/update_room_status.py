from __future__ import annotations

from internal.application.commands.update_room_status import UpdateRoomStatusCommand
from internal.application.errors import RoomNotFoundError
from internal.domain.errors import DomainRuleViolation
from internal.domain.repositories.room_repository import RoomRepository
from internal.domain.valueobjects.room_operational_status import RoomOperationalStatus


class UpdateRoomStatusUseCase:
    def __init__(self, repository: RoomRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateRoomStatusCommand) -> None:
        room = self._repository.get_by_id(command.room_id)
        if room is None:
            raise RoomNotFoundError("Room not found")

        status = self._parse_status(command.new_status)
        previous_status = room.operational_status
        room.update_operational_status(new_status=status, changed_at=command.changed_at)

        if previous_status is status:
            return

        self._repository.save(room)

    def _parse_status(self, raw_status: str) -> RoomOperationalStatus:
        try:
            return RoomOperationalStatus(raw_status)
        except ValueError as error:
            raise DomainRuleViolation("Invalid room operational status") from error
