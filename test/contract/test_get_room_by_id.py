from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from internal.domain.entities.room import Room
from internal.domain.entities.room_availability import RoomAvailability
from internal.domain.valueobjects.date_range import DateRange
from internal.domain.valueobjects.money import Money
from internal.domain.valueobjects.room_operational_status import (
    RoomOperationalStatus,
)
from internal.domain.valueobjects.room_type import RoomType
from internal.interfaces.rest.app import create_app


class FakeRoomRepository:
    def __init__(self, room: Room | None = None) -> None:
        self._room = room

    def add(self, room) -> None:
        del room

    def get_by_room_number(self, room_number: str):
        del room_number
        return None

    def get_by_id(self, room_id: UUID):
        if self._room is None or self._room.room_id != room_id:
            return None
        return self._room

    def search(self, **kwargs):
        del kwargs
        return []

    def list_all(self):
        return []

    def save(self, room) -> None:
        del room


def test_get_room_by_id_returns_room_detail() -> None:
    room = Room(
        room_id=UUID("11111111-1111-1111-1111-111111111111"),
        room_number="101",
        room_type=RoomType.STANDARD,
        capacity=2,
        base_price=Money(amount=Decimal("100.00"), currency="USD"),
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
        availability=RoomAvailability(
            date_range=DateRange(
                start_date=datetime(2026, 4, 24).date(),
                end_date=datetime(2026, 4, 26).date(),
            ),
            booking_id=UUID("22222222-2222-2222-2222-222222222222"),
        ),
    )
    client = TestClient(create_app(repository=FakeRoomRepository(room)))

    response = client.get("/rooms/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    assert response.json() == {
        "roomId": "11111111-1111-1111-1111-111111111111",
        "roomNumber": "101",
        "roomType": "STANDARD",
        "capacity": 2,
        "priceAmount": "100.00",
        "priceCurrency": "USD",
        "operationalStatus": "AVAILABLE",
        "availabilityStart": "2026-04-24",
        "availabilityEnd": "2026-04-26",
        "bookingId": "22222222-2222-2222-2222-222222222222",
        "registeredAt": "2026-04-24T12:00:00Z",
    }


def test_get_room_by_id_returns_not_found_for_unknown_room() -> None:
    client = TestClient(create_app(repository=FakeRoomRepository()))

    response = client.get("/rooms/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 404
    assert response.json() == {"detail": "Room not found"}
