from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol

import pika.exceptions

from internal.interfaces.messaging.contracts import InventoryResponseMessage
from internal.interfaces.messaging.inventory_reservation_consumer import (
    InventoryReservationHandler,
)


class MessageHandlerProtocol(Protocol):
    def handle(self, payload: dict[str, object]) -> Any: ...


class RabbitMqInventoryReservationConsumer:
    def __init__(
        self,
        *,
        connection_factory: Callable[[], Any],
        exchange_name: str,
        request_queue: str,
        response_queue: str,
        request_routing_key: str,
        response_routing_key: str,
        handler: InventoryReservationHandler | MessageHandlerProtocol,
        properties_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._exchange_name = exchange_name
        self._request_queue = request_queue
        self._response_queue = response_queue
        self._request_routing_key = request_routing_key
        self._response_routing_key = response_routing_key
        self._handler = handler
        self._properties_factory = properties_factory or _build_message_properties

    @property
    def exchange_name(self) -> str:
        return self._exchange_name

    @property
    def request_queue(self) -> str:
        return self._request_queue

    @property
    def response_queue(self) -> str:
        return self._response_queue

    @property
    def request_routing_key(self) -> str:
        return self._request_routing_key

    @property
    def response_routing_key(self) -> str:
        return self._response_routing_key

    def process_message(self, body: bytes, *, delivery_tag: int) -> dict[str, object]:
        connection = self._connection_factory()
        channel = connection.channel()
        try:
            self._declare_topology(channel)
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                channel.basic_ack(delivery_tag=delivery_tag)
                return {"acked": True, "requeue": False, "published": False}
            result = self._handler.handle(payload)
            publish_succeeded = False
            if result.response_event is not None:
                try:
                    self._publish_response(channel, result.response_event)
                    publish_succeeded = True
                except (
                    pika.exceptions.AMQPError,
                    RuntimeError,
                    ValueError,
                ):
                    channel.basic_nack(delivery_tag=delivery_tag, requeue=True)
                    return {"acked": False, "requeue": True, "published": False}
            if result.should_ack:
                channel.basic_ack(delivery_tag=delivery_tag)
            else:
                channel.basic_nack(delivery_tag=delivery_tag, requeue=result.requeue)
            return {
                "acked": result.should_ack,
                "requeue": result.requeue,
                "published": publish_succeeded,
            }
        finally:
            if hasattr(connection, "close"):
                connection.close()

    def _declare_topology(self, channel: Any) -> None:
        channel.exchange_declare(
            exchange=self._exchange_name,
            exchange_type="direct",
            durable=True,
        )
        channel.queue_declare(queue=self._request_queue, durable=True)
        channel.queue_bind(
            exchange=self._exchange_name,
            queue=self._request_queue,
            routing_key=self._request_routing_key,
        )
        channel.queue_declare(queue=self._response_queue, durable=True)
        channel.queue_bind(
            exchange=self._exchange_name,
            queue=self._response_queue,
            routing_key=self._response_routing_key,
        )

    def _publish_response(
        self, channel: Any, response_event: InventoryResponseMessage
    ) -> None:
        channel.confirm_delivery()
        channel.basic_publish(
            exchange=self._exchange_name,
            routing_key=self._response_routing_key,
            body=json.dumps(response_event.to_payload()),
            properties=self._properties_factory(response_event.event_type),
            mandatory=True,
        )


def _build_message_properties(event_type: str) -> Any:
    import pika

    return pika.BasicProperties(
        content_type="application/json",
        delivery_mode=2,
        type=event_type,
    )
