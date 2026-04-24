from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from internal.application.commands.register_room import RegisterRoomCommand
from internal.application.errors import DuplicateRoomNumberError
from internal.application.usecases.register_room import RegisterRoomUseCase
from internal.domain.entities.room import Room
from internal.domain.valueobjects.room_operational_status import (
    RoomOperationalStatus,
)
from internal.domain.valueobjects.room_type import RoomType


class InMemoryRoomRepository:
    def __init__(self) -> None:
        self.saved_rooms: list[Room] = []
        self.room_by_number: dict[str, Room] = {}

    def add(self, room: Room) -> None:
        self.saved_rooms.append(room)
        self.room_by_number[room.room_number] = room

    def get_by_room_number(self, room_number: str) -> Room | None:
        return self.room_by_number.get(room_number)

    def get_by_id(self, room_id: UUID) -> Room | None:
        for room in self.saved_rooms:
            if room.room_id == room_id:
                return room
        return None

    def search(
        self,
        *,
        check_in: date,
        check_out: date,
        room_type: str | None = None,
        max_price: Decimal | None = None,
        min_capacity: int | None = None,
    ) -> list[Room]:
        del check_in, check_out, room_type, max_price, min_capacity
        return []

    def save(self, room: Room) -> None:
        self.room_by_number[room.room_number] = room

    def list_all(self) -> list[Room]:
        return list(self.saved_rooms)


def test_register_room_use_case_creates_room_and_returns_identifier() -> None:
    repository = InMemoryRoomRepository()
    use_case = RegisterRoomUseCase(repository)

    room_id = use_case.execute(
        RegisterRoomCommand(
            room_number="101",
            room_type="STANDARD",
            capacity=2,
            price_amount=Decimal("175.00"),
            price_currency="usd",
            operational_status="AVAILABLE",
            availability_start=date(2026, 4, 24),
            availability_end=date(2026, 4, 27),
        )
    )

    assert len(repository.saved_rooms) == 1
    saved_room = repository.saved_rooms[0]
    assert saved_room.room_id == room_id
    assert saved_room.room_type is RoomType.STANDARD
    assert saved_room.operational_status is RoomOperationalStatus.AVAILABLE
    assert saved_room.base_price.amount == Decimal("175.00")
    assert saved_room.availability is not None


def test_register_room_use_case_rejects_duplicate_room_number() -> None:
    repository = InMemoryRoomRepository()
    repository.room_by_number["101"] = Room.register(
        room_id=__import__("uuid").UUID("0db679b9-32d3-489c-b8fd-79a059f1650c"),
        room_number="101",
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("100.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
    )
    use_case = RegisterRoomUseCase(repository)

    with pytest.raises(
        DuplicateRoomNumberError, match="Room number 101 already exists"
    ):
        use_case.execute(
            RegisterRoomCommand(
                room_number="101",
                room_type="DELUXE",
                capacity=3,
                price_amount=Decimal("210.00"),
                price_currency="USD",
                operational_status="MAINTENANCE",
            )
        )
