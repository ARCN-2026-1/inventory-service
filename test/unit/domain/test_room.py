from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from internal.domain.entities.room import Room
from internal.domain.errors import DomainRuleViolation
from internal.domain.events.room_events import RoomStatusChanged
from internal.domain.valueobjects.room_operational_status import (
    RoomOperationalStatus,
)
from internal.domain.valueobjects.room_type import RoomType


def test_room_registers_with_availability_and_emits_event() -> None:
    registered_at = datetime(2026, 4, 23, tzinfo=timezone.utc)

    room = Room.register(
        room_id=UUID("1fcdc9c0-26d9-4e9f-b80a-3dca3a2fe6c7"),
        room_number="101",
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("100.00"),
        price_currency="usd",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=registered_at,
        availability_start=date(2026, 4, 24),
        availability_end=date(2026, 4, 27),
    )

    assert str(room.room_id) == "1fcdc9c0-26d9-4e9f-b80a-3dca3a2fe6c7"
    assert room.room_number == "101"
    assert room.base_price.amount == Decimal("100.00")
    assert room.base_price.currency == "USD"
    assert room.availability is not None
    assert room.availability.date_range.start_date == date(2026, 4, 24)
    assert room.availability.date_range.end_date == date(2026, 4, 27)
    events = room.pull_domain_events()
    assert len(events) == 1
    assert events[0].room_id == room.room_id
    assert events[0].room_number == "101"


def test_room_registers_without_initial_availability() -> None:
    room = Room.register(
        room_id=UUID("205c895d-fb57-4d9f-92a8-a5ba3e4f564f"),
        room_number="202",
        room_type=RoomType.SUITE,
        capacity=4,
        price_amount=Decimal("220.00"),
        price_currency="ARS",
        operational_status=RoomOperationalStatus.MAINTENANCE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
    )

    assert room.availability is None
    assert room.operational_status is RoomOperationalStatus.MAINTENANCE


def test_room_requires_positive_capacity() -> None:
    try:
        Room.register(
            room_id=UUID("8c2ee3d1-5a57-4a09-9618-f7f3f2dbf744"),
            room_number="303",
            room_type=RoomType.DELUXE,
            capacity=0,
            price_amount=Decimal("150.00"),
            price_currency="USD",
            operational_status=RoomOperationalStatus.OUT_OF_SERVICE,
            registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        )
    except DomainRuleViolation as error:
        assert str(error) == "Room capacity must be greater than zero"
    else:
        raise AssertionError("Expected DomainRuleViolation for non-positive capacity")


def test_room_reserve_marks_booking_id_and_emits_event() -> None:
    room = Room.register(
        room_id=UUID("4e5459b0-8d01-42f3-9839-ac68bf20f89b"),
        room_number="401",
        room_type=RoomType.DELUXE,
        capacity=2,
        price_amount=Decimal("199.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 4, 24),
        availability_end=date(2026, 4, 28),
    )
    room.pull_domain_events()
    booking_id = UUID("1d4bcf5d-fc4d-49c2-b4de-d7f17f7d1b8c")
    reserved_at = datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc)

    room.reserve(booking_id=booking_id, reserved_at=reserved_at)

    assert room.availability is not None
    assert room.availability.booking_id == booking_id
    events = room.pull_domain_events()
    assert len(events) == 1
    assert events[0].room_id == room.room_id
    assert events[0].booking_id == booking_id
    assert events[0].reserved_at == reserved_at


def test_room_reserve_rejects_when_room_is_already_reserved() -> None:
    room = Room.register(
        room_id=UUID("6d2d6e60-b261-47ba-bb9c-459be95fd115"),
        room_number="402",
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("155.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 4, 24),
        availability_end=date(2026, 4, 29),
    )
    room.reserve(
        booking_id=UUID("a4b55f26-4be7-43bf-940b-5e0d4db08b2b"),
        reserved_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(DomainRuleViolation, match="Room 402 is already reserved"):
        room.reserve(
            booking_id=UUID("b9f2ad2a-bf1c-4064-8bfa-02f5ea95b7b4"),
            reserved_at=datetime(2026, 4, 24, 11, 0, tzinfo=timezone.utc),
        )


def test_room_reserve_is_idempotent_for_same_booking() -> None:
    room = Room.register(
        room_id=UUID("f5e8d26e-f86a-49ff-babf-f036bd43a73c"),
        room_number="402A",
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("160.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 4, 24),
        availability_end=date(2026, 4, 29),
    )
    booking_id = UUID("e32f8d11-a5f4-449b-971d-c15ea56822ab")
    room.reserve(
        booking_id=booking_id,
        reserved_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone.utc),
    )
    room.pull_domain_events()

    room.reserve(
        booking_id=booking_id,
        reserved_at=datetime(2026, 4, 24, 11, 0, tzinfo=timezone.utc),
    )

    assert room.availability is not None
    assert room.availability.booking_id == booking_id
    assert room.pull_domain_events() == []


def test_room_release_clears_booking_id_and_emits_event() -> None:
    room = Room.register(
        room_id=UUID("3d1adcc3-5340-47bf-a8a5-2b90c75d3480"),
        room_number="403",
        room_type=RoomType.SUITE,
        capacity=4,
        price_amount=Decimal("320.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 4, 25),
        availability_end=date(2026, 4, 30),
    )
    booking_id = UUID("f744a67f-ef0b-4ac0-b080-971db88d02d5")
    room.reserve(
        booking_id=booking_id,
        reserved_at=datetime(2026, 4, 25, 9, 30, tzinfo=timezone.utc),
    )
    room.pull_domain_events()
    released_at = datetime(2026, 4, 26, 8, 15, tzinfo=timezone.utc)

    room.release(booking_id=booking_id, released_at=released_at)

    assert room.availability is not None
    assert room.availability.booking_id is None
    events = room.pull_domain_events()
    assert len(events) == 1
    assert events[0].room_id == room.room_id
    assert events[0].booking_id == booking_id
    assert events[0].released_at == released_at


def test_room_release_rejects_wrong_booking_identifier() -> None:
    room = Room.register(
        room_id=UUID("1b91c59b-0d3a-4369-b333-aa62d005a9da"),
        room_number="404",
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("170.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 4, 24),
        availability_end=date(2026, 4, 27),
    )
    room.reserve(
        booking_id=UUID("61c11ebc-f14a-48f3-a06d-8574ec1a72cc"),
        reserved_at=datetime(2026, 4, 24, 14, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(
        DomainRuleViolation,
        match="Room 404 is reserved for a different booking",
    ):
        room.release(
            booking_id=UUID("8a242afd-35c7-4db8-a37d-c7b13e40bdd9"),
            released_at=datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc),
        )


def test_room_update_operational_status_updates_state_and_emits_event() -> None:
    room = Room.register(
        room_id=UUID("f1cbeb6d-4ab4-4cf6-a6d9-0fd3bfc6d710"),
        room_number="405",
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("180.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
    )
    room.pull_domain_events()
    changed_at = datetime(2026, 4, 25, 11, 0, tzinfo=timezone.utc)

    room.update_operational_status(
        new_status=RoomOperationalStatus.OUT_OF_SERVICE,
        changed_at=changed_at,
    )

    assert room.operational_status is RoomOperationalStatus.OUT_OF_SERVICE
    events = room.pull_domain_events()
    assert len(events) == 1
    assert isinstance(events[0], RoomStatusChanged)
    assert events[0].room_id == room.room_id
    assert events[0].old_status is RoomOperationalStatus.AVAILABLE
    assert events[0].new_status is RoomOperationalStatus.OUT_OF_SERVICE
    assert events[0].changed_at == changed_at


def test_room_update_operational_status_is_idempotent_for_same_status() -> None:
    room = Room.register(
        room_id=UUID("f74b5928-4cbf-4d8a-acdf-2184cd0dca92"),
        room_number="406",
        room_type=RoomType.SUITE,
        capacity=4,
        price_amount=Decimal("350.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.MAINTENANCE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
    )
    room.pull_domain_events()

    room.update_operational_status(
        new_status=RoomOperationalStatus.MAINTENANCE,
        changed_at=datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc),
    )

    assert room.operational_status is RoomOperationalStatus.MAINTENANCE
    assert room.pull_domain_events() == []
