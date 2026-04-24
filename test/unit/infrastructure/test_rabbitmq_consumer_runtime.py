from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import cast
from uuid import UUID

import run_inventory_reservation_consumer as runtime_module
from internal.infrastructure.config.settings import InventoryServiceSettings
from internal.infrastructure.messaging.rabbitmq_inventory_reservation_consumer import (
    RabbitMqInventoryReservationConsumer,
)
from internal.interfaces.messaging.contracts import InventoryResponseMessage
from internal.interfaces.messaging.inventory_reservation_consumer import (
    HandlingResult,
)


class FakeHandler:
    def __init__(self, result: HandlingResult) -> None:
        self.result = result
        self.payloads: list[dict[str, object]] = []

    def handle(self, payload: dict[str, object]) -> HandlingResult:
        self.payloads.append(payload)
        return self.result


class FakeChannel:
    def __init__(self) -> None:
        self.operations: list[str] = []
        self.exchange_declarations: list[tuple[str, str, bool]] = []
        self.queue_declarations: list[tuple[str, bool]] = []
        self.queue_bindings: list[tuple[str, str, str]] = []
        self.published_messages: list[dict[str, object]] = []
        self.acks: list[int] = []
        self.nacks: list[tuple[int, bool]] = []
        self.raise_on_publish: Exception | None = None

    def confirm_delivery(self) -> None:
        self.operations.append("confirm_delivery")

    def exchange_declare(
        self, *, exchange: str, exchange_type: str, durable: bool
    ) -> None:
        self.operations.append("exchange_declare")
        self.exchange_declarations.append((exchange, exchange_type, durable))

    def queue_declare(self, *, queue: str, durable: bool) -> None:
        self.operations.append(f"queue_declare:{queue}")
        self.queue_declarations.append((queue, durable))

    def queue_bind(self, *, exchange: str, queue: str, routing_key: str) -> None:
        self.operations.append(f"queue_bind:{queue}:{routing_key}")
        self.queue_bindings.append((exchange, queue, routing_key))

    def basic_publish(
        self,
        *,
        exchange: str,
        routing_key: str,
        body: str,
        properties: object,
        mandatory: bool,
    ) -> None:
        self.operations.append("basic_publish")
        if self.raise_on_publish is not None:
            raise self.raise_on_publish
        self.published_messages.append(
            {
                "exchange": exchange,
                "routing_key": routing_key,
                "body": body,
                "properties": properties,
                "mandatory": mandatory,
            }
        )

    def basic_ack(self, *, delivery_tag: int) -> None:
        self.operations.append("basic_ack")
        self.acks.append(delivery_tag)

    def basic_nack(self, *, delivery_tag: int, requeue: bool) -> None:
        self.operations.append("basic_nack")
        self.nacks.append((delivery_tag, requeue))


class FakeConnection:
    def __init__(self) -> None:
        self.channel_instance = FakeChannel()
        self.closed = False

    def channel(self) -> FakeChannel:
        return self.channel_instance

    def close(self) -> None:
        self.closed = True


class FakeUrlParameters:
    def __init__(self, url: str) -> None:
        self.url = url
        self.heartbeat: int | None = None
        self.blocked_connection_timeout: int | None = None


class FakeBlockingConnection:
    def __init__(self, parameter: FakeUrlParameters) -> None:
        self.parameter = parameter


class FakePikaModule:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def URLParameters(self, url: str) -> FakeUrlParameters:  # noqa: N802
        self.urls.append(url)
        return FakeUrlParameters(url)

    def BlockingConnection(  # noqa: N802
        self, parameter: FakeUrlParameters
    ) -> FakeBlockingConnection:
        return FakeBlockingConnection(parameter)


def test_consumer_declares_direct_topology_and_publishes_response() -> None:
    connection = FakeConnection()
    response_event = InventoryResponseMessage(
        event_id=UUID("e8bd95ae-8620-422f-aef1-e1f0909efe1a"),
        event_type="BOOKING_Ok",
        timestamp=datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
        booking_id=UUID("6b08d13c-f5d7-43c8-9d74-7db5b8d8a2f4"),
        status="CONFIRMED",
        reservation_confirmed=True,
        failed_rooms=[],
    )
    consumer = RabbitMqInventoryReservationConsumer(
        connection_factory=lambda: connection,
        exchange_name="inventory.direct",
        request_queue="inventory.request.queue",
        response_queue="inventory.response.queue",
        request_routing_key="inventory.request",
        response_routing_key="inventory.response.key",
        handler=FakeHandler(
            HandlingResult(
                should_ack=True,
                requeue=False,
                response_event=response_event,
            )
        ),
        properties_factory=lambda event_type: {"type": event_type},
    )

    outcome = consumer.process_message(
        json.dumps(
            {
                "eventId": "38f4ee99-b032-45f3-8190-605492ed1ef0",
                "eventType": "BOOKING_Ok",
                "timestamp": "2026-04-24T12:00:00+00:00",
                "bookingId": "6b08d13c-f5d7-43c8-9d74-7db5b8d8a2f4",
                "customerId": "fba06311-3720-4d85-9089-475479d9365c",
                "startDate": "2026-04-25",
                "endDate": "2026-04-28",
                "roomIds": ["3f0a4cf8-e5df-4d46-8f17-77e7323db6d7"],
            }
        ).encode("utf-8"),
        delivery_tag=21,
    )

    assert outcome == {"acked": True, "requeue": False, "published": True}
    assert connection.channel_instance.exchange_declarations == [
        ("inventory.direct", "direct", True)
    ]
    assert connection.channel_instance.queue_bindings == [
        ("inventory.direct", "inventory.request.queue", "inventory.request"),
        ("inventory.direct", "inventory.response.queue", "inventory.response.key"),
    ]
    assert connection.channel_instance.published_messages[0]["routing_key"] == (
        "inventory.response.key"
    )
    assert connection.channel_instance.published_messages[0]["mandatory"] is True
    assert connection.channel_instance.operations.index("confirm_delivery") < (
        connection.channel_instance.operations.index("basic_publish")
    )
    assert connection.channel_instance.operations.index("basic_publish") < (
        connection.channel_instance.operations.index("basic_ack")
    )
    assert connection.channel_instance.acks == [21]
    assert connection.closed is True


def test_consumer_nacks_when_response_publish_is_not_confirmed() -> None:
    connection = FakeConnection()
    connection.channel_instance.raise_on_publish = RuntimeError("broker unavailable")
    response_event = InventoryResponseMessage(
        event_id=UUID("1a33008d-b45c-4d0e-ab9e-e92f9304e5dd"),
        event_type="BOOKING_Ok",
        timestamp=datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
        booking_id=UUID("6b08d13c-f5d7-43c8-9d74-7db5b8d8a2f4"),
        status="CONFIRMED",
        reservation_confirmed=True,
        failed_rooms=[],
    )
    consumer = RabbitMqInventoryReservationConsumer(
        connection_factory=lambda: connection,
        exchange_name="inventory.direct",
        request_queue="inventory.request.queue",
        response_queue="inventory.response.queue",
        request_routing_key="inventory.request",
        response_routing_key="inventory.response.key",
        handler=FakeHandler(
            HandlingResult(
                should_ack=True,
                requeue=False,
                response_event=response_event,
            )
        ),
        properties_factory=lambda event_type: {"type": event_type},
    )

    outcome = consumer.process_message(
        json.dumps(
            {
                "eventId": "38f4ee99-b032-45f3-8190-605492ed1ef0",
                "eventType": "BOOKING_Ok",
                "timestamp": "2026-04-24T12:00:00+00:00",
                "bookingId": "6b08d13c-f5d7-43c8-9d74-7db5b8d8a2f4",
                "customerId": "fba06311-3720-4d85-9089-475479d9365c",
                "startDate": "2026-04-25",
                "endDate": "2026-04-28",
                "roomIds": ["3f0a4cf8-e5df-4d46-8f17-77e7323db6d7"],
            }
        ).encode("utf-8"),
        delivery_tag=22,
    )

    assert outcome == {"acked": False, "requeue": True, "published": False}
    assert connection.channel_instance.acks == []
    assert connection.channel_instance.nacks == [(22, True)]
    assert connection.closed is True


def test_consumer_logs_ack_decision_on_invalid_message(
    caplog,
) -> None:
    connection = FakeConnection()
    consumer = RabbitMqInventoryReservationConsumer(
        connection_factory=lambda: connection,
        exchange_name="inventory.direct",
        request_queue="inventory.request.queue",
        response_queue="inventory.response.queue",
        request_routing_key="inventory.request",
        response_routing_key="inventory.response.key",
        handler=FakeHandler(
            HandlingResult(
                should_ack=True,
                requeue=False,
                response_event=None,
            )
        ),
        properties_factory=lambda event_type: {"type": event_type},
    )
    caplog.set_level(logging.INFO)

    outcome = consumer.process_message(b"{not-json}", delivery_tag=70)

    assert outcome == {"acked": True, "requeue": False, "published": False}
    assert "Discarding inventory worker message due to invalid JSON" in caplog.text
    assert "Inventory ack decision=ack requeue=false delivery_tag=70" in caplog.text


def test_consumer_uses_runtime_channel_for_ack_without_opening_new_connection() -> None:
    runtime_channel = FakeChannel()

    def _unexpected_connection_factory() -> FakeConnection:
        raise AssertionError("connection factory should not be called")

    consumer = RabbitMqInventoryReservationConsumer(
        connection_factory=_unexpected_connection_factory,
        exchange_name="inventory.direct",
        request_queue="inventory.request.queue",
        response_queue="inventory.response.queue",
        request_routing_key="inventory.request",
        response_routing_key="inventory.response.key",
        handler=FakeHandler(
            HandlingResult(
                should_ack=True,
                requeue=False,
                response_event=None,
            )
        ),
        properties_factory=lambda event_type: {"type": event_type},
    )

    outcome = consumer.process_message(
        json.dumps(
            {
                "eventId": "38f4ee99-b032-45f3-8190-605492ed1ef0",
                "eventType": "BOOKING_Ok",
                "timestamp": "2026-04-24T12:00:00+00:00",
                "bookingId": "6b08d13c-f5d7-43c8-9d74-7db5b8d8a2f4",
                "customerId": "fba06311-3720-4d85-9089-475479d9365c",
                "startDate": "2026-04-25",
                "endDate": "2026-04-28",
                "roomIds": ["3f0a4cf8-e5df-4d46-8f17-77e7323db6d7"],
            }
        ).encode("utf-8"),
        delivery_tag=71,
        channel=runtime_channel,
    )

    assert outcome == {"acked": True, "requeue": False, "published": False}
    assert runtime_channel.acks == [71]


def test_open_rabbitmq_connection_passes_url_parameters_to_pika(
    monkeypatch,
) -> None:
    fake_pika = FakePikaModule()
    monkeypatch.setitem(sys.modules, "pika", fake_pika)

    connection = runtime_module.open_rabbitmq_connection(
        "amqp://guest:guest@localhost:5672/%2F"
    )
    fake_connection = cast(FakeBlockingConnection, connection)

    assert fake_pika.urls == ["amqp://guest:guest@localhost:5672/%2F"]
    assert fake_connection.parameter.url == "amqp://guest:guest@localhost:5672/%2F"
    assert fake_connection.parameter.heartbeat == 60
    assert fake_connection.parameter.blocked_connection_timeout == 30


def test_build_consumer_uses_inventory_settings_for_rabbitmq_topology(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_create_session_factory(database_url: str) -> str:
        captured["database_url"] = database_url
        return "session-factory"

    class FakeRepository:
        def __init__(self, session_factory: object) -> None:
            captured["session_factory"] = session_factory

    monkeypatch.setattr(
        runtime_module, "create_session_factory", fake_create_session_factory
    )
    monkeypatch.setattr(runtime_module, "SqlAlchemyRoomRepository", FakeRepository)

    settings = InventoryServiceSettings(
        database_url="sqlite://",
        rabbitmq_url="amqp://inventory:secret@localhost:5672/%2F",
        rabbitmq_exchange_inventory="inventory.direct",
        rabbitmq_queue_inventory_request="inventory.request.queue",
        rabbitmq_queue_inventory_res="inventory.response.queue",
        rabbitmq_inventory_request_routing_key="inventory.request",
        rabbitmq_inventory_response_routing_key="inventory.response.key",
    )

    consumer = runtime_module.build_consumer(settings)

    assert captured == {
        "database_url": "sqlite://",
        "session_factory": "session-factory",
    }
    assert consumer.exchange_name == "inventory.direct"
    assert consumer.request_queue == "inventory.request.queue"
    assert consumer.response_queue == "inventory.response.queue"
    assert consumer.request_routing_key == "inventory.request"
    assert consumer.response_routing_key == "inventory.response.key"


def test_configure_logging_sets_info_level_for_worker_runtime(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_basic_config(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(runtime_module.logging, "basicConfig", fake_basic_config)

    runtime_module.configure_logging()

    assert captured["level"] == logging.INFO
    assert captured["format"] == "%(asctime)s %(levelname)s %(name)s %(message)s"
