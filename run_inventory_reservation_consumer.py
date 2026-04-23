from __future__ import annotations

from internal.application.usecases.release_rooms import ReleaseRoomsUseCase
from internal.application.usecases.reserve_rooms import ReserveRoomsUseCase
from internal.infrastructure.config.settings import InventoryServiceSettings
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


def open_rabbitmq_connection(url: str):
    import pika

    parameters = pika.URLParameters(url)
    parameters.heartbeat = 60
    parameters.blocked_connection_timeout = 30
    return pika.BlockingConnection(parameters)


def build_consumer(
    settings: InventoryServiceSettings | None = None,
) -> RabbitMqInventoryReservationConsumer:
    resolved_settings = settings or InventoryServiceSettings()
    repository = SqlAlchemyRoomRepository(
        create_session_factory(resolved_settings.database_url)
    )
    handler = InventoryReservationHandler(
        reserve_rooms=ReserveRoomsUseCase(repository),
        release_rooms=ReleaseRoomsUseCase(repository),
    )
    return RabbitMqInventoryReservationConsumer(
        connection_factory=lambda: open_rabbitmq_connection(
            resolved_settings.rabbitmq_url
        ),
        exchange_name=resolved_settings.rabbitmq_exchange_inventory,
        request_queue=resolved_settings.rabbitmq_queue_inventory_request,
        response_queue=resolved_settings.rabbitmq_queue_inventory_res,
        request_routing_key=resolved_settings.rabbitmq_inventory_request_routing_key,
        response_routing_key=resolved_settings.rabbitmq_inventory_response_routing_key,
        handler=handler,
    )


def main() -> None:
    consumer = build_consumer()
    connection = consumer._connection_factory()
    channel = connection.channel()
    consumer._declare_topology(channel)

    def on_message(channel, method, properties, body):
        del properties
        consumer.process_message(body, delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=InventoryServiceSettings().rabbitmq_queue_inventory_request,
        on_message_callback=on_message,
    )
    channel.start_consuming()


if __name__ == "__main__":
    main()
