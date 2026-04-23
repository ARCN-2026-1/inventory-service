# Tasks: Inventory Booking Messaging

## Phase 1: Domain (RED/GREEN/REFACTOR)

- [x] 1.1 RED: add `test/unit/domain/test_room.py` cases for `Room.reserve()`/`Room.release()`, including already-reserved and wrong-booking failures from the spec.
- [x] 1.2 GREEN: update `internal/domain/entities/{room.py,room_availability.py}` to store nullable `booking_id` and enforce reserve/release invariants with `DomainRuleViolation`.
- [x] 1.3 REFACTOR: extend `internal/domain/events/room_events.py` with `RoomReserved` and `RoomReleased`, then keep event recording/pull behavior consistent.

## Phase 2: Application (RED/GREEN/REFACTOR)

- [x] 2.1 RED: create `test/unit/application/test_reserve_rooms_use_case.py` for success, missing-room, and already-reserved scenarios returning failed room details.
- [x] 2.2 RED: create `test/unit/application/test_release_rooms_use_case.py` for `BOOKING_FALED` rollback, including rooms already released or unrelated to the booking.
- [x] 2.3 GREEN: add `internal/application/commands/{reserve_rooms.py,release_rooms.py}` and `internal/application/usecases/{reserve_rooms.py,release_rooms.py}`.
- [x] 2.4 REFACTOR: update `internal/application/errors.py` and `internal/domain/repositories/room_repository.py` with `RoomNotFoundError`, `RoomNotAvailableError`, `get_by_id()`, and save/update support.

## Phase 3: Persistence & Config

- [x] 3.1 RED: add `test/integration/persistence/test_sqlalchemy_room_repository.py` coverage for `booking_id` round-trip and `get_by_id()` lookups.
- [x] 3.2 GREEN: update `internal/infrastructure/persistence/{models.py,sqlalchemy_room_repository.py}` to persist `booking_id`, map updated availability, and save reservations/releases.
- [x] 3.3 GREEN: create `alembic/versions/*_add_booking_id_to_room_availability.py` for nullable `room_availability.booking_id`.
- [x] 3.4 REFACTOR: update `internal/infrastructure/config/settings.py` and `pyproject.toml` with RabbitMQ settings and `pika` dependency.

## Phase 4: Messaging Interfaces & Runner

- [x] 4.1 RED: add `test/unit/interfaces/test_inventory_reservation_consumer.py` for parse failures, ack/nack decisions, `BOOKING_Ok`, and `BOOKING_FALED` handling.
- [x] 4.2 RED: add `test/contract/test_inventory_booking_messages.py` for incoming payload aliases and outgoing `InventoryResponse` JSON shape expected by booking-service.
- [x] 4.3 GREEN: create `internal/interfaces/messaging/{contracts.py,inventory_reservation_consumer.py}` with pure parsing, `HandlingResult`, and response construction.
- [x] 4.4 GREEN: create `internal/infrastructure/messaging/rabbitmq_inventory_reservation_consumer.py` and `run_inventory_reservation_consumer.py` for direct-exchange consume/publish plus ack/nack wiring.

## Phase 5: End-to-End Verification

- [x] 5.1 RED/GREEN: add `test/integration/messaging/test_rabbitmq_inventory_reservation_consumer.py` using MySQL and RabbitMQ containers for reserve success, insufficient inventory, rollback release, transient nack, and invalid-message discard.
- [x] 5.2 REFACTOR: align package exports/init files only where needed so the worker and tests import messaging components without leaking domain logic into `shared/`.
