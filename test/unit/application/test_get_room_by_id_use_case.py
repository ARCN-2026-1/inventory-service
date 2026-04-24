from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from internal.application.errors import RoomNotFoundError
from internal.application.queries.get_room_by_id_use_case import GetRoomByIdUseCase
from internal.domain.entities.room import Room
from internal.domain.valueobjects.money import Money
from internal.domain.valueobjects.room_operational_status import (
    RoomOperationalStatus,
)
from internal.domain.valueobjects.room_type import RoomType


class StubRoomRepository:
    def __init__(self, room: Room | None = None) -> None:
        self.room = room

    def add(self, room: Room) -> None:
        del room

    def get_by_room_number(self, room_number: str) -> Room | None:
        del room_number
        return None

    def get_by_id(self, room_id: UUID) -> Room | None:
        if self.room is None or self.room.room_id != room_id:
            return None
        return self.room

    def search(self, **kwargs) -> list[Room]:
        del kwargs
        return []

    def save(self, room: Room) -> None:
        del room

    def list_all(self) -> list[Room]:
        return []


def test_get_room_by_id_use_case_returns_room() -> None:
    room = Room(
        room_id=UUID("11111111-1111-1111-1111-111111111111"),
        room_number="101",
        room_type=RoomType.STANDARD,
        capacity=2,
        base_price=Money(amount=Decimal("100.00"), currency="USD"),
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime.now(timezone.utc),
    )

    result = GetRoomByIdUseCase(StubRoomRepository(room)).execute(room.room_id)

    assert result is room


def test_get_room_by_id_use_case_raises_not_found_for_unknown_room() -> None:
    use_case = GetRoomByIdUseCase(StubRoomRepository())

    with pytest.raises(RoomNotFoundError, match="Room not found"):
        use_case.execute(UUID("11111111-1111-1111-1111-111111111111"))
