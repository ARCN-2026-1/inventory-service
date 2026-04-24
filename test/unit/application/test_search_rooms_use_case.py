from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from internal.application.queries.search_rooms_query import (
    RoomSummary,
    SearchRoomsQuery,
)
from internal.application.queries.search_rooms_use_case import SearchRoomsUseCase
from internal.domain.entities.room import Room
from internal.domain.errors import DomainRuleViolation
from internal.domain.valueobjects.room_operational_status import (
    RoomOperationalStatus,
)
from internal.domain.valueobjects.room_type import RoomType


class SearchSpyRoomRepository:
    def __init__(self, rooms: list[Room] | None = None) -> None:
        self.rooms = rooms or []
        self.search_calls: list[dict[str, object]] = []

    def add(self, room: Room) -> None:
        self.rooms.append(room)

    def get_by_room_number(self, room_number: str) -> Room | None:
        return None

    def get_by_id(self, room_id: UUID) -> Room | None:
        return None

    def save(self, room: Room) -> None:
        return None

    def list_all(self) -> list[Room]:
        return list(self.rooms)

    def search(
        self,
        *,
        check_in: date,
        check_out: date,
        room_type: str | None = None,
        max_price: Decimal | None = None,
        min_capacity: int | None = None,
    ) -> list[Room]:
        self.search_calls.append(
            {
                "check_in": check_in,
                "check_out": check_out,
                "room_type": room_type,
                "max_price": max_price,
                "min_capacity": min_capacity,
            }
        )
        return self.rooms


def test_search_rooms_use_case_builds_date_range_and_maps_room_summaries() -> None:
    repository = SearchSpyRoomRepository(
        rooms=[
            _build_room(
                room_id=UUID("11111111-1111-1111-1111-111111111111"),
                room_number="501",
                room_type=RoomType.SUITE,
                capacity=4,
                price_amount=Decimal("320.00"),
            )
        ]
    )

    result = SearchRoomsUseCase(repository).execute(
        SearchRoomsQuery(
            check_in=date(2026, 5, 10),
            check_out=date(2026, 5, 12),
        )
    )

    assert repository.search_calls == [
        {
            "check_in": date(2026, 5, 10),
            "check_out": date(2026, 5, 12),
            "room_type": None,
            "max_price": None,
            "min_capacity": None,
        }
    ]
    assert result == [
        RoomSummary(
            room_id="11111111-1111-1111-1111-111111111111",
            room_number="501",
            room_type="SUITE",
            capacity=4,
            price_amount=Decimal("320.00"),
            price_currency="USD",
        )
    ]


def test_search_rooms_use_case_forwards_optional_filters() -> None:
    repository = SearchSpyRoomRepository()

    result = SearchRoomsUseCase(repository).execute(
        SearchRoomsQuery(
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 3),
            room_type="DELUXE",
            max_price=Decimal("250.00"),
            min_capacity=3,
        )
    )

    assert result == []
    assert repository.search_calls == [
        {
            "check_in": date(2026, 6, 1),
            "check_out": date(2026, 6, 3),
            "room_type": "DELUXE",
            "max_price": Decimal("250.00"),
            "min_capacity": 3,
        }
    ]


def test_search_rooms_use_case_rejects_non_increasing_stay_window() -> None:
    repository = SearchSpyRoomRepository()

    with pytest.raises(
        DomainRuleViolation, match="Availability end date must be after start date"
    ):
        SearchRoomsUseCase(repository).execute(
            SearchRoomsQuery(
                check_in=date(2026, 6, 3),
                check_out=date(2026, 6, 3),
            )
        )


def _build_room(
    *,
    room_id: UUID,
    room_number: str,
    room_type: RoomType,
    capacity: int,
    price_amount: Decimal,
) -> Room:
    return Room.register(
        room_id=room_id,
        room_number=room_number,
        room_type=room_type,
        capacity=capacity,
        price_amount=price_amount,
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 5, 1),
        availability_end=date(2026, 5, 30),
    )
