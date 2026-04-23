# Design: Inventory Booking Messaging

## Technical Approach

Implement a new messaging slice that follows the repo’s hexagonal split: `internal/interfaces/messaging` parses JSON and decides ack/nack, `internal/application` orchestrates reserve/release use cases, and `internal/infrastructure` owns SQLAlchemy and pika wiring. Reservation state will live on `RoomAvailability.booking_id`, which matches the current one-room/one-active-booking scope from the proposal and spec.

## Architecture Decisions

### Decision: Store booking ownership on `RoomAvailability`

| Option | Tradeoff | Decision |
|---|---|---|
| New `Reservation` table/entity | More flexible for future overlaps, larger scope now | No |
| Add nullable `booking_id` to `room_availability` | Single active reservation per room, simplest rollback/release | Yes |

**Rationale**: The current model already treats availability as a single child record. Adding `booking_id` satisfies reserve/release scenarios without inventing a second aggregate model.

### Decision: Keep handler pure; keep pika in runner

| Option | Tradeoff | Decision |
|---|---|---|
| Fat pika callback with business logic | Fewer files, poor testability, breaks hexagonal boundaries | No |
| Pure handler + infra runner | More files, clean unit tests and isolated broker concerns | Yes |

**Rationale**: This mirrors the confirmed `customer-service` Python pattern and preserves strict TDD.

### Decision: Match booking topology with one direct exchange

| Option | Tradeoff | Decision |
|---|---|---|
| Reuse topic-style defaults | Easier copy/paste, contract mismatch risk | No |
| Declare the booking-owned direct exchange and exact routing keys | Requires explicit config, interoperable with booking-service | Yes |

**Rationale**: Booking already binds `inventory.request.queue` and `${RABBITMQ_QUEUE_INVENTORY_RES}` on a `DirectExchange`; inventory must match exactly, including `BOOKING_FALED`.

## Data Flow

```text
BookingCreatedEvent JSON
  -> direct exchange (${RABBITMQ_EXCHANGE_INVENTORY}, routing key inventory.request)
  -> inventory.request.queue
  -> RabbitMqInventoryReservationConsumer.process_next_message()
  -> BookingCreatedMessage.from_payload()
  -> InventoryReservationHandler.handle()
  -> ReserveRoomsUseCase | ReleaseRoomsUseCase
  -> RoomRepository.get_by_id()/save
  -> MySQL room_availability.booking_id
  -> InventoryResponseMessage
  -> direct exchange (routing key inventory.response.key)
  -> ${RABBITMQ_QUEUE_INVENTORY_RES}
```

If payload parsing fails, the runner rejects/discards safely (or dead-letters if broker policy exists). If DB/broker work fails transiently, the handler returns `should_ack=False, requeue=True` so the runner `nack`s.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | Modify | Add `pika` (and optional typing stubs). |
| `internal/domain/entities/room.py` | Modify | Add `reserve()` / `release()` invariants and emit domain events. |
| `internal/domain/entities/room_availability.py` | Modify | Add nullable `booking_id` to the entity state. |
| `internal/domain/events/room_events.py` | Modify | Add `RoomReserved` and `RoomReleased`. |
| `internal/domain/repositories/room_repository.py` | Modify | Add `get_by_id()` and persistence update capability. |
| `internal/application/errors.py` | Modify | Add `RoomNotFoundError` / `RoomNotAvailableError`. |
| `internal/application/commands/reserve_rooms.py` | Create | Command for booking-driven reservations. |
| `internal/application/commands/release_rooms.py` | Create | Command for booking rollback releases. |
| `internal/application/usecases/reserve_rooms.py` | Create | Reserve all requested rooms and collect failures. |
| `internal/application/usecases/release_rooms.py` | Create | Release rooms by `booking_id`. |
| `internal/interfaces/messaging/contracts.py` | Create | `BookingCreatedMessage`, `InventoryResponseMessage`, `FailedRoom`. |
| `internal/interfaces/messaging/inventory_reservation_consumer.py` | Create | Pure handler returning `HandlingResult`. |
| `internal/infrastructure/messaging/rabbitmq_inventory_reservation_consumer.py` | Create | pika topology, consume, publish, ack/nack. |
| `internal/infrastructure/config/settings.py` | Modify | Add RabbitMQ URL, exchange, queue, and routing-key settings. |
| `internal/infrastructure/persistence/{models.py,sqlalchemy_room_repository.py}` | Modify | Persist `booking_id`, implement `get_by_id()`, and save updates. |
| `alembic/versions/*_add_booking_id_to_room_availability.py` | Create | Schema migration for reservation tracking. |
| `run_inventory_reservation_consumer.py` | Create | Worker entrypoint separate from `main.py`. |
| `test/unit/interfaces`, `test/unit/application`, `test/integration`, `test/contract` | Modify/Create | Messaging-focused unit/integration/contract coverage. |

## Interfaces / Contracts

```python
@dataclass(slots=True)
class BookingCreatedMessage:
    event_id: UUID
    event_type: Literal["BOOKING_Ok", "BOOKING_FALED"]
    booking_id: UUID
    customer_id: UUID
    start_date: date
    end_date: date
    room_ids: list[UUID]

@dataclass(slots=True)
class HandlingResult:
    should_ack: bool
    requeue: bool
    response_event: InventoryResponseMessage | None = None
```

`InventoryResponseMessage` echoes `booking_id`, keeps the same `eventType`, sets `reservationConfirmed`, and includes `failedRooms[{roomId, reason}]`. `InventoryServiceSettings` gains `rabbitmq_url`, `rabbitmq_exchange_inventory`, `rabbitmq_queue_inventory_request`, `rabbitmq_queue_inventory_res`, `rabbitmq_inventory_request_routing_key`, and `rabbitmq_inventory_response_routing_key`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `Room.reserve/release`, failure invariants, use-case branching, contract parsing, handler ack/nack decisions | Pure pytest in `test/unit/domain`, `test/unit/application`, `test/unit/interfaces`. |
| Integration | Alembic migration, SQLAlchemy round-trip for `booking_id`, real RabbitMQ topology/publish/consume round-trip | pytest + MySQL/RabbitMQ testcontainers. |
| Contract | JSON payload aliases and response shape expected by booking-service | pytest/FastAPI-style contract tests without broker. |

No E2E suite is planned because `openspec/config.yaml` marks e2e unavailable.

## Migration / Rollout

Add one Alembic migration that makes `room_availability.booking_id` nullable. Deploy order: run migration, deploy API unchanged, then start the consumer worker. No historical backfill is required.

## Open Questions

None.
