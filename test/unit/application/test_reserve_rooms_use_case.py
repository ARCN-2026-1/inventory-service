from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from internal.application.commands.reserve_rooms import ReserveRoomsCommand
from internal.application.usecases.reserve_rooms import ReserveRoomsUseCase
from internal.domain.entities.room import Room
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
        self.rooms_by_id[room.room_id] = room
        self.saved_rooms.append(room)


def test_reserve_rooms_use_case_confirms_reservation_for_all_available_rooms() -> None:
    room = _build_room(
        room_id=UUID("f8b1972e-08e2-4ff6-a943-a9d1ce913851"),
        room_number="501",
    )
    repository = InMemoryRoomRepository([room])
    use_case = ReserveRoomsUseCase(repository)

    result = use_case.execute(
        ReserveRoomsCommand(
            booking_id=UUID("67984548-f5dd-4976-92d0-a73e58c9482d"),
            room_ids=[room.room_id],
            requested_at=datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
        )
    )

    assert result.reservation_confirmed is True
    assert result.failed_rooms == []
    assert repository.saved_rooms == [room]
    assert room.availability is not None
    assert room.availability.booking_id == UUID("67984548-f5dd-4976-92d0-a73e58c9482d")


def test_reserve_rooms_use_case_returns_failed_room_when_room_does_not_exist() -> None:
    repository = InMemoryRoomRepository()
    use_case = ReserveRoomsUseCase(repository)
    missing_room_id = UUID("28699cf9-4f6d-4488-86e2-c18ab4d79bcb")

    result = use_case.execute(
        ReserveRoomsCommand(
            booking_id=UUID("22dccda3-b0f7-4369-ac89-33b45baeb279"),
            room_ids=[missing_room_id],
            requested_at=datetime(2026, 4, 24, 12, 30, tzinfo=timezone.utc),
        )
    )

    assert result.reservation_confirmed is False
    assert len(result.failed_rooms) == 1
    assert result.failed_rooms[0].room_id == missing_room_id
    assert result.failed_rooms[0].reason == "Room not found"
    assert repository.saved_rooms == []


def test_reserve_rooms_use_case_returns_failed_room_when_room_is_already_reserved() -> (
    None
):
    room = _build_room(
        room_id=UUID("1b6de5b4-39cc-43f4-b32d-62fcd478f7af"),
        room_number="502",
    )
    room.reserve(
        booking_id=UUID("4defe0f4-4d3c-462e-a768-46dcb70c3973"),
        reserved_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone.utc),
    )
    room.pull_domain_events()
    repository = InMemoryRoomRepository([room])
    use_case = ReserveRoomsUseCase(repository)

    result = use_case.execute(
        ReserveRoomsCommand(
            booking_id=UUID("7ce365a8-9a84-43e6-a0a5-a3932397c0ad"),
            room_ids=[room.room_id],
            requested_at=datetime(2026, 4, 24, 13, 0, tzinfo=timezone.utc),
        )
    )

    assert result.reservation_confirmed is False
    assert len(result.failed_rooms) == 1
    assert result.failed_rooms[0].room_id == room.room_id
    assert result.failed_rooms[0].reason == "Room is already reserved"
    assert repository.saved_rooms == []
    assert room.availability is not None
    assert room.availability.booking_id == UUID("4defe0f4-4d3c-462e-a768-46dcb70c3973")


def _build_room(*, room_id: UUID, room_number: str) -> Room:
    return Room.register(
        room_id=room_id,
        room_number=room_number,
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("140.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 4, 24),
        availability_end=date(2026, 4, 28),
    )
