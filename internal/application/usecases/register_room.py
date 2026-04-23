from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from internal.application.commands.register_room import RegisterRoomCommand
from internal.application.errors import DuplicateRoomNumberError
from internal.domain.entities.room import Room
from internal.domain.repositories.room_repository import RoomRepository
from internal.domain.valueobjects.room_operational_status import RoomOperationalStatus
from internal.domain.valueobjects.room_type import RoomType


class RegisterRoomUseCase:
    def __init__(self, repository: RoomRepository) -> None:
        self._repository = repository

    def execute(self, command: RegisterRoomCommand) -> UUID:
        if self._repository.get_by_room_number(command.room_number) is not None:
            raise DuplicateRoomNumberError(
                f"Room number {command.room_number} already exists"
            )

        room = Room.register(
            room_id=uuid4(),
            room_number=command.room_number,
            room_type=RoomType(command.room_type),
            capacity=command.capacity,
            price_amount=command.price_amount,
            price_currency=command.price_currency,
            operational_status=RoomOperationalStatus(command.operational_status),
            registered_at=datetime.now(timezone.utc),
            availability_start=command.availability_start,
            availability_end=command.availability_end,
        )
        self._repository.add(room)
        return room.room_id
