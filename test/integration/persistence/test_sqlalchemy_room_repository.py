from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from testcontainers.mysql import MySqlContainer

from alembic import command
from alembic.config import Config
from internal.domain.entities.room import Room
from internal.domain.errors import DomainRuleViolation
from internal.domain.valueobjects.room_operational_status import (
    RoomOperationalStatus,
)
from internal.domain.valueobjects.room_type import RoomType
from internal.infrastructure.persistence.database import create_session_factory
from internal.infrastructure.persistence.sqlalchemy_room_repository import (
    SqlAlchemyRoomRepository,
)


def _require_docker_daemon() -> None:
    try:
        import docker

        client = docker.from_env()
        client.ping()
        client.close()
    except Exception as error:  # pragma: no cover - environment guard
        pytest.skip(
            "Docker daemon unavailable; MySQL testcontainers require Docker. "
            f"Original error: {error}"
        )


@pytest.fixture(scope="module")
def mysql_database_url() -> Iterator[str]:
    _require_docker_daemon()
    with MySqlContainer(
        "mysql:8.0.36",
        username="inventory",
        password="secret",
        dbname="inventory_service",
    ) as mysql:
        yield mysql.get_connection_url().replace("mysql://", "mysql+pymysql://", 1)


@pytest.fixture(scope="module")
def migrated_database_url(mysql_database_url: str) -> Iterator[str]:
    alembic_config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[3] / "alembic")
    )
    alembic_config.set_main_option("sqlalchemy.url", mysql_database_url)
    command.upgrade(alembic_config, "head")
    yield mysql_database_url


def test_repository_persists_room_and_availability(migrated_database_url: str) -> None:
    repository = SqlAlchemyRoomRepository(create_session_factory(migrated_database_url))
    room = Room.register(
        room_id=UUID("ef3a5927-79b5-4648-bf94-5b7969734791"),
        room_number="101",
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("120.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 4, 24),
        availability_end=date(2026, 4, 26),
    )

    repository.add(room)
    reloaded = repository.get_by_room_number("101")

    assert reloaded is not None
    assert reloaded.room_id == room.room_id
    assert reloaded.availability is not None
    assert reloaded.availability.date_range.start_date == date(2026, 4, 24)
    assert reloaded.availability.date_range.end_date == date(2026, 4, 26)


def test_repository_rejects_duplicate_room_number(migrated_database_url: str) -> None:
    repository = SqlAlchemyRoomRepository(create_session_factory(migrated_database_url))
    first_room = Room.register(
        room_id=UUID("5c5eefc6-d084-430c-b8d9-e60db99cf370"),
        room_number="102",
        room_type=RoomType.DELUXE,
        capacity=3,
        price_amount=Decimal("180.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
    )
    duplicate_room = Room.register(
        room_id=UUID("359eb20f-26d3-40d6-bf29-89506389c7eb"),
        room_number="102",
        room_type=RoomType.SUITE,
        capacity=4,
        price_amount=Decimal("250.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.MAINTENANCE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
    )

    repository.add(first_room)

    with pytest.raises(DomainRuleViolation, match="Room number 102 already exists"):
        repository.add(duplicate_room)


def test_repository_round_trips_booking_id_and_get_by_id(
    migrated_database_url: str,
) -> None:
    repository = SqlAlchemyRoomRepository(create_session_factory(migrated_database_url))
    booking_id = UUID("6bfc2c1b-eb3a-4706-9e1b-9ea8fb5a2b69")
    room = Room.register(
        room_id=UUID("c26d8a9e-d7a6-4a88-bc5a-db4024172cde"),
        room_number="103",
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("160.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 4, 25),
        availability_end=date(2026, 4, 27),
    )
    room.reserve(
        booking_id=booking_id,
        reserved_at=datetime(2026, 4, 24, 8, 30, tzinfo=timezone.utc),
    )
    room.pull_domain_events()

    repository.add(room)
    reloaded = repository.get_by_id(room.room_id)

    assert reloaded is not None
    assert reloaded.room_id == room.room_id
    assert reloaded.availability is not None
    assert reloaded.availability.booking_id == booking_id


def test_repository_save_updates_booking_id(migrated_database_url: str) -> None:
    repository = SqlAlchemyRoomRepository(create_session_factory(migrated_database_url))
    booking_id = UUID("693c609b-dc11-4d52-a90c-d4d892c01521")
    room = Room.register(
        room_id=UUID("90f03079-ac0e-48ae-b5ee-f845abcf97a8"),
        room_number="104",
        room_type=RoomType.DELUXE,
        capacity=3,
        price_amount=Decimal("210.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 4, 25),
        availability_end=date(2026, 4, 29),
    )
    repository.add(room)
    room.reserve(
        booking_id=booking_id,
        reserved_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
    )
    room.pull_domain_events()

    repository.save(room)
    reserved = repository.get_by_id(room.room_id)

    assert reserved is not None
    assert reserved.availability is not None
    assert reserved.availability.booking_id == booking_id

    room.release(
        booking_id=booking_id,
        released_at=datetime(2026, 4, 24, 18, 0, tzinfo=timezone.utc),
    )
    room.pull_domain_events()

    repository.save(room)
    released = repository.get_by_id(room.room_id)

    assert released is not None
    assert released.availability is not None
    assert released.availability.booking_id is None


def test_repository_search_returns_only_rooms_available_for_requested_stay(
    migrated_database_url: str,
) -> None:
    repository = SqlAlchemyRoomRepository(create_session_factory(migrated_database_url))
    available_room = Room.register(
        room_id=UUID("f7d309d3-01ce-425d-a66a-24bf30656c2d"),
        room_number="201",
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("140.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 5, 1),
        availability_end=date(2026, 5, 10),
    )
    booked_room = Room.register(
        room_id=UUID("6c26b3c4-b778-4cb8-9fe3-ae2e482aa7f9"),
        room_number="202",
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("145.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 5, 1),
        availability_end=date(2026, 5, 10),
    )
    booked_room.reserve(
        booking_id=UUID("083c12a4-9b1f-476a-aac6-fe4b4bb9ca25"),
        reserved_at=datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
    )
    booked_room.pull_domain_events()
    maintenance_room = Room.register(
        room_id=UUID("05ffde5b-e74c-4764-a20f-5315001c9f2e"),
        room_number="203",
        room_type=RoomType.DELUXE,
        capacity=3,
        price_amount=Decimal("200.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.MAINTENANCE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 5, 1),
        availability_end=date(2026, 5, 10),
    )
    missing_overlap_room = Room.register(
        room_id=UUID("da4ac5d2-8cbe-48ad-bca0-ecc1e44d0a34"),
        room_number="204",
        room_type=RoomType.SUITE,
        capacity=4,
        price_amount=Decimal("320.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 5, 6),
        availability_end=date(2026, 5, 8),
    )

    for room in [available_room, booked_room, maintenance_room, missing_overlap_room]:
        repository.add(room)

    result = repository.search(check_in=date(2026, 5, 2), check_out=date(2026, 5, 5))

    assert [room.room_number for room in result] == ["201"]


def test_repository_search_applies_optional_room_filters(
    migrated_database_url: str,
) -> None:
    repository = SqlAlchemyRoomRepository(create_session_factory(migrated_database_url))
    matching_room = Room.register(
        room_id=UUID("3f1ddf90-1d4f-4a06-b597-6e4510adc3ef"),
        room_number="205",
        room_type=RoomType.SUITE,
        capacity=4,
        price_amount=Decimal("250.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 5, 1),
        availability_end=date(2026, 5, 10),
    )
    expensive_room = Room.register(
        room_id=UUID("d7d84058-f841-488c-8e49-4fc421c0b516"),
        room_number="206",
        room_type=RoomType.SUITE,
        capacity=4,
        price_amount=Decimal("310.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 5, 1),
        availability_end=date(2026, 5, 10),
    )
    small_capacity_room = Room.register(
        room_id=UUID("8efe3475-c3a9-4647-b89e-cd8bfb44bdbf"),
        room_number="207",
        room_type=RoomType.SUITE,
        capacity=2,
        price_amount=Decimal("220.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 5, 1),
        availability_end=date(2026, 5, 10),
    )
    wrong_type_room = Room.register(
        room_id=UUID("86dc77db-f4af-4246-9d7f-d7d76caf0a7b"),
        room_number="208",
        room_type=RoomType.DELUXE,
        capacity=4,
        price_amount=Decimal("240.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 5, 1),
        availability_end=date(2026, 5, 10),
    )

    for room in [matching_room, expensive_room, small_capacity_room, wrong_type_room]:
        repository.add(room)

    result = repository.search(
        check_in=date(2026, 5, 2),
        check_out=date(2026, 5, 5),
        room_type="SUITE",
        max_price=Decimal("250.00"),
        min_capacity=4,
    )

    assert [room.room_number for room in result] == ["205"]
