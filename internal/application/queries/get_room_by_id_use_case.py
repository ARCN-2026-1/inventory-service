from __future__ import annotations

from uuid import UUID

from internal.application.errors import RoomNotFoundError
from internal.domain.entities.room import Room
from internal.domain.repositories.room_repository import RoomRepository


class GetRoomByIdUseCase:
    def __init__(self, repository: RoomRepository) -> None:
        self._repository = repository

    def execute(self, room_id: UUID) -> Room:
        room = self._repository.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundError("Room not found")
        return room
