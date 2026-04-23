# Proposal: inventory-booking-messaging

## Intent

Integrate `inventory-service` with `booking-service` via RabbitMQ to support distributed transactions (sagas). We need to process incoming `BookingCreatedEvent` messages to reserve or release rooms, and emit `InventoryResponse` messages back to the booking service to continue or abort the saga.

## Scope

### In Scope
- Add `pika` dependency.
- Extend `Room` domain (and `RoomAvailability` model) to track `booking_id` for reservations.
- Create `ReserveRoomsUseCase` and `ReleaseRoomsUseCase`.
- Implement a RabbitMQ consumer for `inventory.request.queue` (Direct exchange) following the existing Python messaging patterns.
- Publish `InventoryResponse` to `${RABBITMQ_QUEUE_INVENTORY_RES}`.

### Out of Scope
- Multi-reservation per room for non-overlapping dates (sticking to one active booking per room for now).
- Changing the `booking-service` contract (we must handle typos like `BOOKING_FALED`).
- Any REST API modifications.

## Capabilities

### New Capabilities
- `booking-messaging`: Listen for booking events (`BOOKING_Ok`, `BOOKING_FALED`) over RabbitMQ, reserve/release rooms accordingly, and publish outcome responses.

### Modified Capabilities
- None

## Approach

Use **Approach 1** from exploration:
Follow the clean messaging architecture from `customer-service`. We will add pure dataclass contracts, a pure handler returning `HandlingResult`, and a pika-based runner (`rabbitmq_inventory_reservation_consumer.py`). We will extend the `RoomAvailability` model with a `booking_id` column to track reservations and add a `get_by_id` repository method to support UUID-based room lookups.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `pyproject.toml` | Modified | Add `pika` dependency. |
| `internal/domain/entities/room.py` | Modified | Add `reserve()` and `release()` methods. |
| `internal/infrastructure/persistence/models.py` | Modified | Add `booking_id` to `RoomAvailabilityModel`. |
| `internal/infrastructure/persistence/sqlalchemy_room_repository.py` | Modified | Add `get_by_id()` method. |
| `alembic/` | New | Migration for `booking_id` column. |
| `internal/application/usecases/` | New | `ReserveRoomsUseCase`, `ReleaseRoomsUseCase`. |
| `internal/interfaces/messaging/` | New | `contracts.py`, `inventory_reservation_consumer.py`. |
| `internal/infrastructure/messaging/` | New | `rabbitmq_inventory_reservation_consumer.py`. |
| `internal/infrastructure/config/settings.py` | Modified | Add RabbitMQ configuration fields. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Contract typos (`BOOKING_FALED`) | High | Explicitly define the typo in our internal contract to match the source of truth exactly. |
| Exchange type mismatch | Med | Explicitly use `DirectExchange` to match `booking-service` instead of `topic`. |

## Rollback Plan

Revert the PR. Downgrade the database using Alembic to remove the `booking_id` column from `RoomAvailabilityModel`. The service will stop listening to RabbitMQ and no longer process booking events.

## Dependencies

- RabbitMQ broker availability.
- Database schema migration (Alembic).

## Success Criteria

- [ ] `inventory-service` successfully starts and connects to RabbitMQ.
- [ ] Processing a `BOOKING_Ok` event reserves the rooms and publishes a `reservationConfirmed=true` response.
- [ ] Processing a `BOOKING_FALED` event releases the rooms.
- [ ] Integration tests verify the full messaging round-trip using Testcontainers.