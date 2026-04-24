from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from internal.domain.valueobjects.room_type import RoomType
from internal.interfaces.rest.app import create_app


class FakeRoomRepository:
    def __init__(self) -> None:
        self._rooms = []

    def add(self, room) -> None:
        self._rooms.append(room)

    def get_by_room_number(self, room_number: str):
        return next((r for r in self._rooms if r.room_number == room_number), None)

    def get_by_id(self, room_id: UUID):
        return next((r for r in self._rooms if r.room_id == room_id), None)

    def search(self, **kwargs):
        return []

    def list_all(self):
        return self._rooms

    def save(self, room) -> None:
        del room


def test_get_all_rooms_returns_all_rooms() -> None:
    from datetime import datetime, timezone

    from internal.domain.entities.room import Room
    from internal.domain.valueobjects.money import Money
    from internal.domain.valueobjects.room_operational_status import (
        RoomOperationalStatus,
    )

    repo = FakeRoomRepository()
    repo._rooms = [
        Room(
            room_id=UUID("11111111-1111-1111-1111-111111111111"),
            room_number="101",
            room_type=RoomType.STANDARD,
            capacity=2,
            base_price=Money(amount=Decimal("100.00"), currency="USD"),
            operational_status=RoomOperationalStatus.AVAILABLE,
            registered_at=datetime.now(timezone.utc),
        ),
        Room(
            room_id=UUID("22222222-2222-2222-2222-222222222222"),
            room_number="102",
            room_type=RoomType.DELUXE,
            capacity=4,
            base_price=Money(amount=Decimal("200.00"), currency="USD"),
            operational_status=RoomOperationalStatus.AVAILABLE,
            registered_at=datetime.now(timezone.utc),
        ),
    ]

    client = TestClient(create_app(repository=repo))

    response = client.get("/rooms/all")

    assert response.status_code == 200
    data = response.json()
    assert data["rooms"] == [
        {
            "roomId": "11111111-1111-1111-1111-111111111111",
            "roomNumber": "101",
            "roomType": "STANDARD",
            "capacity": 2,
            "priceAmount": "100.00",
            "priceCurrency": "USD",
        },
        {
            "roomId": "22222222-2222-2222-2222-222222222222",
            "roomNumber": "102",
            "roomType": "DELUXE",
            "capacity": 4,
            "priceAmount": "200.00",
            "priceCurrency": "USD",
        },
    ]


def test_get_all_rooms_returns_empty_list_when_no_rooms() -> None:
    repo = FakeRoomRepository()

    client = TestClient(create_app(repository=repo))

    response = client.get("/rooms/all")

    assert response.status_code == 200
    assert response.json() == {"rooms": []}
