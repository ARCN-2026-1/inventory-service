from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from internal.domain.entities.room import Room
from internal.domain.valueobjects.room_operational_status import (
    RoomOperationalStatus,
)
from internal.domain.valueobjects.room_type import RoomType
from internal.interfaces.rest.app import create_app


class SearchStubRepository:
    def __init__(self, *, results: list[Room] | None = None) -> None:
        self.results = results or []
        self.search_calls: list[dict[str, object]] = []

    def add(self, room) -> None:
        raise AssertionError("search contract should not persist rooms")

    def get_by_room_number(self, room_number: str):
        raise AssertionError("search contract should not lookup room numbers")

    def get_by_id(self, room_id):
        raise AssertionError("search contract should not lookup room ids")

    def save(self, room) -> None:
        raise AssertionError("search contract should not save rooms")

    def list_all(self) -> list[Room]:
        return []

    def search(
        self,
        *,
        check_in: date,
        check_out: date,
        room_type: str | None = None,
        max_price: Decimal | None = None,
        min_capacity: int | None = None,
    ):
        self.search_calls.append(
            {
                "check_in": check_in,
                "check_out": check_out,
                "room_type": room_type,
                "max_price": max_price,
                "min_capacity": min_capacity,
            }
        )
        return self.results


def test_get_rooms_returns_room_summaries_for_valid_search() -> None:
    repository = SearchStubRepository(
        results=[
            _build_room(
                room_id="8cdf148e-b18e-4371-b1c3-b1da3155b7d6",
                room_number="701",
                room_type="SUITE",
                capacity=4,
                price_amount=Decimal("280.00"),
            )
        ]
    )
    client = TestClient(create_app(repository=repository))

    response = client.get(
        "/rooms",
        params={"check_in": "2026-05-10", "check_out": "2026-05-12"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "rooms": [
            {
                "roomId": "8cdf148e-b18e-4371-b1c3-b1da3155b7d6",
                "roomNumber": "701",
                "roomType": "SUITE",
                "capacity": 4,
                "priceAmount": "280.00",
                "priceCurrency": "USD",
            }
        ]
    }
    assert repository.search_calls == [
        {
            "check_in": date(2026, 5, 10),
            "check_out": date(2026, 5, 12),
            "room_type": None,
            "max_price": None,
            "min_capacity": None,
        }
    ]


def test_get_rooms_applies_optional_filters_and_ignores_booking_style_params() -> None:
    repository = SearchStubRepository()
    client = TestClient(create_app(repository=repository))

    response = client.get(
        "/rooms",
        params={
            "check_in": "2026-05-10",
            "check_out": "2026-05-12",
            "room_type": "DELUXE",
            "max_price": "200.00",
            "min_capacity": 3,
            "booking_id": "ignored",
            "guest_count": 2,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"rooms": []}
    assert repository.search_calls == [
        {
            "check_in": date(2026, 5, 10),
            "check_out": date(2026, 5, 12),
            "room_type": "DELUXE",
            "max_price": Decimal("200.00"),
            "min_capacity": 3,
        }
    ]


def test_get_rooms_returns_bad_request_for_invalid_stay_window() -> None:
    repository = SearchStubRepository()
    client = TestClient(create_app(repository=repository))

    response = client.get(
        "/rooms",
        params={"check_in": "2026-05-12", "check_out": "2026-05-12"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Availability end date must be after start date"
    }
    assert repository.search_calls == []


def _build_room(
    *,
    room_id: str,
    room_number: str,
    room_type: str,
    capacity: int,
    price_amount: Decimal,
) -> Room:
    return Room.register(
        room_id=UUID(room_id),
        room_number=room_number,
        room_type=RoomType(room_type),
        capacity=capacity,
        price_amount=price_amount,
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 5, 1),
        availability_end=date(2026, 5, 30),
    )
