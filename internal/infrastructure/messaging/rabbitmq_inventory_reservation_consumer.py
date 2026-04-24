from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any, Protocol

import pika.exceptions

from internal.interfaces.messaging.contracts import InventoryResponseMessage
from internal.interfaces.messaging.inventory_reservation_consumer import (
    InventoryReservationHandler,
)

logger = logging.getLogger(__name__)
logger.propagate = True


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

    def process_message(
        self,
        body: bytes,
        *,
        delivery_tag: int,
        channel: Any | None = None,
    ) -> dict[str, object]:
        owns_connection = channel is None
        connection = None
        if channel is None:
            connection = self._connection_factory()
            channel = connection.channel()
        assert channel is not None
        try:
            self._declare_topology(channel)
            logger.info(
                "Received inventory worker message delivery_tag=%s body=%s",
                delivery_tag,
                _body_preview(body),
            )

            if not channel.is_open:
                logger.error(
                    "Channel is not open delivery_tag=%s",
                    delivery_tag,
                )
                channel.basic_nack(delivery_tag=delivery_tag, requeue=True)
                return {"acked": False, "requeue": True, "published": False}

            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.warning(
                    "Discarding inventory worker message due to invalid JSON "
                    "delivery_tag=%s",
                    delivery_tag,
                )
                channel.basic_ack(delivery_tag=delivery_tag)
                logger.info(
                    "Inventory ack decision=ack requeue=false delivery_tag=%s",
                    delivery_tag,
                )
                return {"acked": True, "requeue": False, "published": False}

            if not isinstance(payload, dict):
                logger.warning(
                    "Discarding inventory worker message because payload is not an "
                    "object delivery_tag=%s payload_type=%s",
                    delivery_tag,
                    type(payload).__name__,
                )
                channel.basic_ack(delivery_tag=delivery_tag)
                logger.info(
                    "Inventory ack decision=ack requeue=false delivery_tag=%s",
                    delivery_tag,
                )
                return {"acked": True, "requeue": False, "published": False}

            logger.info(
                "Parsed inventory worker payload delivery_tag=%s payload=%s",
                delivery_tag,
                _payload_log_subset(payload),
            )
            result = self._handler.handle(payload)
            publish_succeeded = False
            if result.response_event is not None:
                try:
                    logger.info(
                        "Publishing inventory response delivery_tag=%s event_type=%s "
                        "booking_id=%s reservation_confirmed=%s",
                        delivery_tag,
                        result.response_event.event_type,
                        result.response_event.booking_id,
                        result.response_event.reservation_confirmed,
                    )
                    self._publish_response(channel, result.response_event)
                    publish_succeeded = True
                    logger.info(
                        "Published inventory response delivery_tag=%s event_type=%s",
                        delivery_tag,
                        result.response_event.event_type,
                    )
                except (
                    pika.exceptions.AMQPError,
                    RuntimeError,
                    ValueError,
                ):
                    logger.exception(
                        "Failed publishing inventory response delivery_tag=%s "
                        "decision=nack requeue=true",
                        delivery_tag,
                    )
                    channel.basic_nack(delivery_tag=delivery_tag, requeue=True)
                    return {"acked": False, "requeue": True, "published": False}
            if result.should_ack:
                channel.basic_ack(delivery_tag=delivery_tag)
                logger.info(
                    "Inventory ack decision=ack requeue=false delivery_tag=%s",
                    delivery_tag,
                )
            else:
                channel.basic_nack(delivery_tag=delivery_tag, requeue=result.requeue)
                logger.info(
                    "Inventory ack decision=nack requeue=%s delivery_tag=%s",
                    result.requeue,
                    delivery_tag,
                )
            return {
                "acked": result.should_ack,
                "requeue": result.requeue,
                "published": publish_succeeded,
            }
        finally:
            if (
                owns_connection
                and connection is not None
                and hasattr(connection, "close")
            ):
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


def _body_preview(body: bytes, *, max_len: int = 400) -> str:
    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError:
        return "<non-utf8-body>"

    if len(decoded) <= max_len:
        return decoded
    return f"{decoded[:max_len]}...<truncated>"


def _payload_log_subset(payload: dict[str, object]) -> dict[str, object | None]:
    room_ids = payload.get("roomIds")

    return {
        "eventId": payload.get("eventId"),
        "eventType": payload.get("eventType"),
        "bookingId": payload.get("bookingId"),
        "customerId": payload.get("customerId"),
        "roomIdsCount": len(room_ids) if isinstance(room_ids, list) else None,
        "timestamp": payload.get("timestamp"),
    }
