from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from internal.domain.entities.room import Room
from internal.domain.valueobjects.room_operational_status import (
    RoomOperationalStatus,
)
from internal.domain.valueobjects.room_type import RoomType
from internal.interfaces.rest.app import create_app


class InMemoryRoomRepository:
    def __init__(self, rooms: list[Room] | None = None) -> None:
        self.rooms_by_id = {room.room_id: room for room in rooms or []}
        self.rooms_by_number = {room.room_number: room for room in rooms or []}
        self.saved_rooms: list[Room] = []

    def add(self, room: Room) -> None:
        self.rooms_by_id[room.room_id] = room
        self.rooms_by_number[room.room_number] = room

    def get_by_room_number(self, room_number: str) -> Room | None:
        return self.rooms_by_number.get(room_number)

    def get_by_id(self, room_id: UUID) -> Room | None:
        return self.rooms_by_id.get(room_id)

    def search(self, **kwargs):
        del kwargs
        return []

    def save(self, room: Room) -> None:
        self.rooms_by_id[room.room_id] = room
        self.rooms_by_number[room.room_number] = room
        self.saved_rooms.append(room)

    def list_all(self) -> list[Room]:
        return list(self.rooms_by_id.values())


def test_patch_rooms_status_returns_204_for_valid_transition() -> None:
    room = _build_room(
        room_id=UUID("ef1dfd99-f12d-4b4e-ae92-f6a686f46a39"),
        status=RoomOperationalStatus.AVAILABLE,
    )
    repository = InMemoryRoomRepository([room])
    client = TestClient(create_app(repository=repository))

    response = client.patch(
        f"/rooms/{room.room_id}/status",
        json={"operationalStatus": "MAINTENANCE"},
    )

    assert response.status_code == 204
    assert response.content == b""


def test_patch_rooms_status_rejects_invalid_status() -> None:
    room = _build_room(
        room_id=UUID("09f66fb5-749d-4ce0-8f9a-f26297be61b6"),
        status=RoomOperationalStatus.AVAILABLE,
    )
    client = TestClient(create_app(repository=InMemoryRoomRepository([room])))

    response = client.patch(
        f"/rooms/{room.room_id}/status",
        json={"operationalStatus": "BROKEN"},
    )

    assert response.status_code == 400


def test_patch_rooms_status_returns_404_for_unknown_room() -> None:
    client = TestClient(create_app(repository=InMemoryRoomRepository()))

    response = client.patch(
        "/rooms/e54df397-48f7-4a8b-bc87-a89da3bfdbcc/status",
        json={"operationalStatus": "AVAILABLE"},
    )

    assert response.status_code == 404


def test_patch_rooms_status_is_idempotent_when_status_is_the_same() -> None:
    room = _build_room(
        room_id=UUID("352ed055-4b8f-4c1f-93bb-c54ad3200f4d"),
        status=RoomOperationalStatus.OUT_OF_SERVICE,
    )
    repository = InMemoryRoomRepository([room])
    client = TestClient(create_app(repository=repository))

    response = client.patch(
        f"/rooms/{room.room_id}/status",
        json={"operationalStatus": "OUT_OF_SERVICE"},
    )

    assert response.status_code == 204
    assert repository.saved_rooms == []


def _build_room(*, room_id: UUID, status: RoomOperationalStatus) -> Room:
    room = Room.register(
        room_id=room_id,
        room_number=str(room_id)[:8],
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("100.00"),
        price_currency="USD",
        operational_status=status,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
    )
    room.pull_domain_events()
    return room
