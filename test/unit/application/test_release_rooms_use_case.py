from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from internal.application.commands.release_rooms import ReleaseRoomsCommand
from internal.application.usecases.release_rooms import ReleaseRoomsUseCase
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


def test_release_rooms_use_case_releases_rooms_reserved_for_booking() -> None:
    booking_id = UUID("4732dc8e-ff34-4957-8cd0-64dc3a462fc2")
    room = _build_reserved_room(
        room_id=UUID("59cd8d31-a0d5-4eb7-b90f-0f15efdc6521"),
        room_number="601",
        booking_id=booking_id,
    )
    repository = InMemoryRoomRepository([room])
    use_case = ReleaseRoomsUseCase(repository)

    result = use_case.execute(
        ReleaseRoomsCommand(
            booking_id=booking_id,
            room_ids=[room.room_id],
            released_at=datetime(2026, 4, 25, 9, 0, tzinfo=timezone.utc),
        )
    )

    assert result.released_room_ids == [room.room_id]
    assert repository.saved_rooms == [room]
    assert room.availability is not None
    assert room.availability.booking_id is None


def test_release_rooms_use_case_skips_room_that_is_already_released() -> None:
    room = _build_available_room(
        room_id=UUID("e456b8c0-2e06-4d03-82c2-0eec9438b9d7"),
        room_number="602",
    )
    repository = InMemoryRoomRepository([room])
    use_case = ReleaseRoomsUseCase(repository)

    result = use_case.execute(
        ReleaseRoomsCommand(
            booking_id=UUID("af1eecc4-20c7-4659-bafc-05ae7bf868d0"),
            room_ids=[room.room_id],
            released_at=datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc),
        )
    )

    assert result.released_room_ids == []
    assert repository.saved_rooms == []
    assert room.availability is not None
    assert room.availability.booking_id is None


def test_release_rooms_use_case_skips_room_reserved_for_different_booking() -> None:
    room = _build_reserved_room(
        room_id=UUID("42dd9e32-fa74-4d59-8ea9-c7979779266c"),
        room_number="603",
        booking_id=UUID("338bc351-d02c-4b64-b61c-30e1e6cb82c8"),
    )
    repository = InMemoryRoomRepository([room])
    use_case = ReleaseRoomsUseCase(repository)

    result = use_case.execute(
        ReleaseRoomsCommand(
            booking_id=UUID("94aa0efb-c962-4fc4-b191-569f12f7155c"),
            room_ids=[room.room_id],
            released_at=datetime(2026, 4, 25, 11, 0, tzinfo=timezone.utc),
        )
    )

    assert result.released_room_ids == []
    assert repository.saved_rooms == []
    assert room.availability is not None
    assert room.availability.booking_id == UUID("338bc351-d02c-4b64-b61c-30e1e6cb82c8")


def _build_available_room(*, room_id: UUID, room_number: str) -> Room:
    return Room.register(
        room_id=room_id,
        room_number=room_number,
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("150.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 4, 24),
        availability_end=date(2026, 4, 28),
    )


def _build_reserved_room(*, room_id: UUID, room_number: str, booking_id: UUID) -> Room:
    room = _build_available_room(room_id=room_id, room_number=room_number)
    room.reserve(
        booking_id=booking_id,
        reserved_at=datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
    )
    room.pull_domain_events()
    return room
