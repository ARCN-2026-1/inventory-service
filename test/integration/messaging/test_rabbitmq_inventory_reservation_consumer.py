from __future__ import annotations

import json
import time
from collections.abc import Iterator
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pika
import pytest
from testcontainers.mysql import MySqlContainer
from testcontainers.rabbitmq import RabbitMqContainer

from alembic import command
from alembic.config import Config
from internal.application.usecases.release_rooms import ReleaseRoomsUseCase
from internal.application.usecases.reserve_rooms import ReserveRoomsUseCase
from internal.domain.entities.room import Room
from internal.domain.valueobjects.room_operational_status import (
    RoomOperationalStatus,
)
from internal.domain.valueobjects.room_type import RoomType
from internal.infrastructure.messaging.rabbitmq_inventory_reservation_consumer import (
    RabbitMqInventoryReservationConsumer,
)
from internal.infrastructure.persistence.database import create_session_factory
from internal.infrastructure.persistence.sqlalchemy_room_repository import (
    SqlAlchemyRoomRepository,
)
from internal.interfaces.messaging.inventory_reservation_consumer import (
    InventoryReservationHandler,
)


def _require_docker_daemon() -> None:
    try:
        import docker

        client = docker.from_env()
        client.ping()
        client.close()
    except Exception as error:  # pragma: no cover - environment guard
        pytest.skip(
            "Docker daemon unavailable; RabbitMQ/MySQL integration tests require "
            f"Docker. Original error: {error}"
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


def test_consumer_processes_reservation_success_round_trip(
    migrated_database_url: str,
) -> None:
    repository = SqlAlchemyRoomRepository(create_session_factory(migrated_database_url))
    room = _build_room(
        room_id=UUID("bc1c94b6-b555-4579-9f3a-6700b1efe22b"),
        room_number="701",
    )
    repository.add(room)

    with RabbitMqContainer("rabbitmq:3.13-alpine") as rabbitmq:
        consumer = _build_consumer(repository, rabbitmq)
        connection = pika.BlockingConnection(rabbitmq.get_connection_params())
        channel = connection.channel()
        _declare_topology(channel)

        channel.basic_publish(
            exchange="inventory.direct",
            routing_key="inventory.request",
            body=json.dumps(_booking_payload(room.room_id, event_type="BOOKING_Ok")),
        )

        body, delivery_tag = _wait_for_request_message(channel)
        outcome = consumer.process_message(body, delivery_tag=delivery_tag)
        response = _wait_for_response_message(channel)

        connection.close()

    reloaded = repository.get_by_id(room.room_id)

    assert outcome == {"acked": True, "requeue": False, "published": True}
    assert reloaded is not None
    assert reloaded.availability is not None
    assert reloaded.availability.booking_id == UUID(
        "dfdf2f3d-68ef-4b0b-a93a-ee6fa35f2f49"
    )
    assert response["eventType"] == "BOOKING_Ok"
    assert response["bookingId"] == "dfdf2f3d-68ef-4b0b-a93a-ee6fa35f2f49"
    assert response["reservationConfirmed"] is True
    assert response["failedRooms"] == []


def test_consumer_processes_insufficient_inventory_with_failed_room_response(
    migrated_database_url: str,
) -> None:
    repository = SqlAlchemyRoomRepository(create_session_factory(migrated_database_url))

    with RabbitMqContainer("rabbitmq:3.13-alpine") as rabbitmq:
        consumer = _build_consumer(repository, rabbitmq)
        connection = pika.BlockingConnection(rabbitmq.get_connection_params())
        channel = connection.channel()
        _declare_topology(channel)

        channel.basic_publish(
            exchange="inventory.direct",
            routing_key="inventory.request",
            body=json.dumps(
                _booking_payload(
                    UUID("5dc2fa54-b62a-4050-a4c0-f677d778f18b"),
                    event_type="BOOKING_Ok",
                )
            ),
        )

        body, delivery_tag = _wait_for_request_message(channel)
        outcome = consumer.process_message(body, delivery_tag=delivery_tag)
        response = _wait_for_response_message(channel)

        connection.close()

    assert outcome == {"acked": True, "requeue": False, "published": True}
    assert response["reservationConfirmed"] is False
    assert response["failedRooms"] == [
        {
            "roomId": "5dc2fa54-b62a-4050-a4c0-f677d778f18b",
            "reason": "Room not found",
        }
    ]


def test_consumer_processes_booking_faled_and_releases_room(
    migrated_database_url: str,
) -> None:
    repository = SqlAlchemyRoomRepository(create_session_factory(migrated_database_url))
    booking_id = UUID("f753fc7b-e75e-41b2-8d10-fbfd6951ad12")
    room = _build_room(
        room_id=UUID("0ed2b950-31de-42ed-a0ff-ac6c29e5ce27"),
        room_number="702",
    )
    repository.add(room)
    room.reserve(
        booking_id=booking_id,
        reserved_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
    )
    room.pull_domain_events()
    repository.save(room)

    with RabbitMqContainer("rabbitmq:3.13-alpine") as rabbitmq:
        consumer = _build_consumer(repository, rabbitmq)
        connection = pika.BlockingConnection(rabbitmq.get_connection_params())
        channel = connection.channel()
        _declare_topology(channel)

        payload = _booking_payload(room.room_id, event_type="BOOKING_FALED")
        payload["bookingId"] = str(booking_id)
        channel.basic_publish(
            exchange="inventory.direct",
            routing_key="inventory.request",
            body=json.dumps(payload),
        )

        body, delivery_tag = _wait_for_request_message(channel)
        outcome = consumer.process_message(body, delivery_tag=delivery_tag)
        response = _wait_for_response_message(channel)

        connection.close()

    reloaded = repository.get_by_id(room.room_id)

    assert outcome == {"acked": True, "requeue": False, "published": True}
    assert reloaded is not None
    assert reloaded.availability is not None
    assert reloaded.availability.booking_id is None
    assert response["eventType"] == "BOOKING_FALED"
    assert response["reservationConfirmed"] is False


def test_consumer_nacks_transient_errors_for_requeue() -> None:
    class FailingReserveRoomsUseCase:
        def execute(self, command: Any):
            del command
            raise RuntimeError("temporary mysql outage")

    handler = InventoryReservationHandler(
        reserve_rooms=FailingReserveRoomsUseCase(),
        release_rooms=ReleaseRoomsUseCase(_NoOpRepository()),
    )

    class FakeChannel:
        def __init__(self) -> None:
            self.exchange_declarations: list[tuple[str, str, bool]] = []
            self.queue_declarations: list[tuple[str, bool]] = []
            self.queue_bindings: list[tuple[str, str, str]] = []
            self.published_messages: list[dict[str, object]] = []
            self.acks: list[int] = []
            self.nacks: list[tuple[int, bool]] = []

        def exchange_declare(
            self, *, exchange: str, exchange_type: str, durable: bool
        ) -> None:
            self.exchange_declarations.append((exchange, exchange_type, durable))

        def queue_declare(self, *, queue: str, durable: bool) -> None:
            self.queue_declarations.append((queue, durable))

        def queue_bind(self, *, exchange: str, queue: str, routing_key: str) -> None:
            self.queue_bindings.append((exchange, queue, routing_key))

        def basic_publish(
            self, *, exchange: str, routing_key: str, body: str, properties: object
        ) -> None:
            self.published_messages.append(
                {
                    "exchange": exchange,
                    "routing_key": routing_key,
                    "body": body,
                    "properties": properties,
                }
            )

        def basic_ack(self, *, delivery_tag: int) -> None:
            self.acks.append(delivery_tag)

        def basic_nack(self, *, delivery_tag: int, requeue: bool) -> None:
            self.nacks.append((delivery_tag, requeue))

    class FakeConnection:
        def __init__(self) -> None:
            self.channel_instance = FakeChannel()
            self.closed = False

        def channel(self) -> FakeChannel:
            return self.channel_instance

        def close(self) -> None:
            self.closed = True

    connection = FakeConnection()
    consumer = RabbitMqInventoryReservationConsumer(
        connection_factory=lambda: connection,
        exchange_name="inventory.direct",
        request_queue="inventory.request.queue",
        response_queue="inventory.response.queue",
        request_routing_key="inventory.request",
        response_routing_key="inventory.response.key",
        handler=handler,
        properties_factory=lambda event_type: {"type": event_type},
    )

    outcome = consumer.process_message(
        json.dumps(
            _booking_payload(
                UUID("b95187a8-4afb-46ee-9f1a-07365b96d5fd"),
                event_type="BOOKING_Ok",
            )
        ).encode("utf-8"),
        delivery_tag=99,
    )

    assert outcome == {"acked": False, "requeue": True, "published": False}
    assert connection.channel_instance.acks == []
    assert connection.channel_instance.nacks == [(99, True)]
    assert connection.closed is True


def test_consumer_discards_invalid_message_without_crashing() -> None:
    connection = _FakeAckConnection()
    consumer = RabbitMqInventoryReservationConsumer(
        connection_factory=lambda: connection,
        exchange_name="inventory.direct",
        request_queue="inventory.request.queue",
        response_queue="inventory.response.queue",
        request_routing_key="inventory.request",
        response_routing_key="inventory.response.key",
        handler=InventoryReservationHandler(
            reserve_rooms=ReserveRoomsUseCase(_NoOpRepository()),
            release_rooms=ReleaseRoomsUseCase(_NoOpRepository()),
        ),
        properties_factory=lambda event_type: {"type": event_type},
    )

    outcome = consumer.process_message(b"{not-json}", delivery_tag=7)

    assert outcome == {"acked": True, "requeue": False, "published": False}
    assert connection.channel_instance.acks == [7]
    assert connection.channel_instance.nacks == []
    assert connection.closed is True


class _NoOpRepository:
    def add(self, room: Room) -> None:
        del room

    def get_by_room_number(self, room_number: str) -> Room | None:
        del room_number
        return None

    def get_by_id(self, room_id: UUID) -> Room | None:
        del room_id
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
        del room


class _FakeAckChannel:
    def __init__(self) -> None:
        self.acks: list[int] = []
        self.nacks: list[tuple[int, bool]] = []

    def exchange_declare(
        self, *, exchange: str, exchange_type: str, durable: bool
    ) -> None:
        del exchange, exchange_type, durable

    def queue_declare(self, *, queue: str, durable: bool) -> None:
        del queue, durable

    def queue_bind(self, *, exchange: str, queue: str, routing_key: str) -> None:
        del exchange, queue, routing_key

    def basic_publish(
        self, *, exchange: str, routing_key: str, body: str, properties: object
    ) -> None:
        del exchange, routing_key, body, properties

    def basic_ack(self, *, delivery_tag: int) -> None:
        self.acks.append(delivery_tag)

    def basic_nack(self, *, delivery_tag: int, requeue: bool) -> None:
        self.nacks.append((delivery_tag, requeue))


class _FakeAckConnection:
    def __init__(self) -> None:
        self.channel_instance = _FakeAckChannel()
        self.closed = False

    def channel(self) -> _FakeAckChannel:
        return self.channel_instance

    def close(self) -> None:
        self.closed = True


def _build_consumer(
    repository: SqlAlchemyRoomRepository,
    rabbitmq: RabbitMqContainer,
) -> RabbitMqInventoryReservationConsumer:
    return RabbitMqInventoryReservationConsumer(
        connection_factory=lambda: pika.BlockingConnection(
            rabbitmq.get_connection_params()
        ),
        exchange_name="inventory.direct",
        request_queue="inventory.request.queue",
        response_queue="inventory.response.queue",
        request_routing_key="inventory.request",
        response_routing_key="inventory.response.key",
        handler=InventoryReservationHandler(
            reserve_rooms=ReserveRoomsUseCase(repository),
            release_rooms=ReleaseRoomsUseCase(repository),
        ),
    )


def _declare_topology(
    channel: Any,
) -> None:
    channel.exchange_declare(
        exchange="inventory.direct", exchange_type="direct", durable=True
    )
    channel.queue_declare(queue="inventory.request.queue", durable=True)
    channel.queue_bind(
        exchange="inventory.direct",
        queue="inventory.request.queue",
        routing_key="inventory.request",
    )
    channel.queue_declare(queue="inventory.response.queue", durable=True)
    channel.queue_bind(
        exchange="inventory.direct",
        queue="inventory.response.queue",
        routing_key="inventory.response.key",
    )


def _wait_for_request_message(
    channel: Any,
) -> tuple[bytes, int]:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        method_frame, properties, body = channel.basic_get(
            queue="inventory.request.queue",
            auto_ack=False,
        )
        del properties
        if method_frame is not None:
            return body, method_frame.delivery_tag
        time.sleep(0.05)
    pytest.fail("Timed out waiting for inventory request message")


def _wait_for_response_message(
    channel: Any,
) -> dict[str, object]:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        method_frame, properties, body = channel.basic_get(
            queue="inventory.response.queue",
            auto_ack=True,
        )
        del properties
        if method_frame is not None:
            return json.loads(body.decode("utf-8"))
        time.sleep(0.05)
    pytest.fail("Timed out waiting for inventory response message")


def _build_room(*, room_id: UUID, room_number: str) -> Room:
    return Room.register(
        room_id=room_id,
        room_number=room_number,
        room_type=RoomType.STANDARD,
        capacity=2,
        price_amount=Decimal("100.00"),
        price_currency="USD",
        operational_status=RoomOperationalStatus.AVAILABLE,
        registered_at=datetime(2026, 4, 23, tzinfo=timezone.utc),
        availability_start=date(2026, 4, 25),
        availability_end=date(2026, 4, 28),
    )


def _booking_payload(room_id: UUID, *, event_type: str) -> dict[str, object]:
    return {
        "eventId": "ded36318-fddd-4442-88f7-799dd4cf0cd2",
        "eventType": event_type,
        "timestamp": "2026-04-24T12:00:00+00:00",
        "bookingId": "dfdf2f3d-68ef-4b0b-a93a-ee6fa35f2f49",
        "customerId": "ebd5fe2f-5fb0-4fdb-a4e8-5392a334da8d",
        "startDate": "2026-04-25",
        "endDate": "2026-04-28",
        "roomIds": [str(room_id)],
    }
