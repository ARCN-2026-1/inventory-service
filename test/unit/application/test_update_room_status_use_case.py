from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from internal.application.commands.update_room_status import UpdateRoomStatusCommand
from internal.application.errors import RoomNotFoundError
from internal.application.usecases.update_room_status import UpdateRoomStatusUseCase
from internal.domain.entities.room import Room
from internal.domain.errors import DomainRuleViolation
from internal.domain.valueobjects.room_operational_status import (
    RoomOperationalStatus,
)
from internal.domain.valueobjects.room_type import RoomType


class InMemoryRoomRepository:
    def __init__(self, rooms: list[Room] | None = None) -> None:
        self.rooms_by_id = {room.room_id: room for room in rooms or []}
        self.saved_rooms: list[Room] = []

    def add(self, room: Room) -> None:
        self.rooms_by_id[room.room_id] = room

    def get_by_room_number(self, room_number: str) -> Room | None:
        for room in self.rooms_by_id.values():
            if room.room_number == room_number:
                return room
        return None

    def get_by_id(self, room_id: UUID) -> Room | None:
        return self.rooms_by_id.get(room_id)

    def search(self, **kwargs):
        del kwargs
        return []

    def save(self, room: Room) -> None:
        self.rooms_by_id[room.room_id] = room
        self.saved_rooms.append(room)


def test_update_room_status_use_case_updates_existing_room() -> None:
    room = _build_room(
        room_id=UUID("f8d2ea0d-536a-44e1-8f9a-5f3d938b29eb"),
        status=RoomOperationalStatus.AVAILABLE,
    )
    repository = InMemoryRoomRepository([room])

    UpdateRoomStatusUseCase(repository).execute(
        UpdateRoomStatusCommand(
            room_id=room.room_id,
            new_status="MAINTENANCE",
            changed_at=datetime(2026, 4, 25, 8, 0, tzinfo=timezone.utc),
        )
    )

    assert room.operational_status is RoomOperationalStatus.MAINTENANCE
    assert repository.saved_rooms == [room]


def test_update_room_status_use_case_rejects_invalid_status_value() -> None:
    room = _build_room(
        room_id=UUID("6e13884a-ef9c-42a0-b7ca-3f9ecadf2e02"),
        status=RoomOperationalStatus.AVAILABLE,
    )
    repository = InMemoryRoomRepository([room])

    with pytest.raises(DomainRuleViolation, match="Invalid room operational status"):
        UpdateRoomStatusUseCase(repository).execute(
            UpdateRoomStatusCommand(
                room_id=room.room_id,
                new_status="BROKEN",
                changed_at=datetime(2026, 4, 25, 9, 0, tzinfo=timezone.utc),
            )
        )


def test_update_room_status_use_case_rejects_unknown_room_id() -> None:
    repository = InMemoryRoomRepository()

    with pytest.raises(RoomNotFoundError, match="Room not found"):
        UpdateRoomStatusUseCase(repository).execute(
            UpdateRoomStatusCommand(
                room_id=UUID("f03e44e0-ba2b-49a0-99ef-26f1f04d4827"),
                new_status="AVAILABLE",
                changed_at=datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc),
            )
        )


def _build_room(*, room_id: UUID, status: RoomOperationalStatus) -> Room:
    return Room.register(
        room_id=room_id,
        room_number=str(room_id)[:8],
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("150.00"),
        price_currency="USD",
        operational_status=status,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
    )
