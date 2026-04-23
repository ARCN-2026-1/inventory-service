# Exploration: inventory-booking-messaging

## Current State

`inventory-service` is a FastAPI / Python 3.11 DDD-hexagonal service.
It already has:

- **Domain**: `Room` aggregate with `RoomAvailability` (single date-range VO per room), `RoomRegistered` event, `DomainRuleViolation` for invariant enforcement.
- **Application**: `RegisterRoomUseCase` + `RegisterRoomCommand`. No reserve / release use cases exist yet.
- **Infrastructure**: SQLAlchemy 2 persistence (MySQL), `InventoryServiceSettings` with only `database_url`. **No RabbitMQ integration**.
- **Interfaces**: REST only (`POST /rooms`, `GET /health`). No messaging interface layer.
- **Dependency**: `pika` is **not** in `pyproject.toml`.

`booking-service` (Java / Spring AMQP) already:
- Publishes `BookingCreatedEvent` to exchange `${RABBITMQ_EXCHANGE_INVENTORY}` with routing-key `inventory.request`, bound to queue `inventory.request.queue`.
- Listens for `InventoryResponse` on queue `${RABBITMQ_QUEUE_INVENTORY_RES}`, bound to the same exchange with routing-key `inventory.response.key`.
- Sends `BookingCreatedEvent` with `eventType = BOOKING_Ok` for a normal reservation request.
- Sends `BookingCreatedEvent` with `eventType = BOOKING_FALED` for a rollback/release request (triggered when the payment step fails).
- Decides the saga's next step from `InventoryResponse.reservationConfirmed` (boolean) and `InventoryResponse.status` (string).

`customer-service` (Python) is the canonical reference for the messaging pattern in Python services. It uses:
- `internal/interfaces/messaging/contracts.py` — pure dataclass message contract with a `from_payload()` factory that validates eagerly.
- `internal/interfaces/messaging/customer_validation_consumer.py` — pure handler returning `HandlingResult(should_ack, requeue, event)`.
- `internal/infrastructure/messaging/rabbitmq_customer_validation_consumer.py` — pika-based runner that calls `ensure_topology()` and `process_next_message()`.
- Settings with `rabbitmq_url`, queue names, exchange names, and routing keys.

---

## Booking Contract (exact, confirmed from source)

### Inbound — `BookingCreatedEvent` (JSON):
```json
{
  "eventId":    "<uuid-string>",
  "eventType":  "BOOKING_Ok" | "BOOKING_FALED",
  "timestamp":  "<ISO-8601 datetime>",
  "bookingId":  "<uuid-string>",
  "customerId": "<uuid-string>",
  "startDate":  "<YYYY-MM-DD>",
  "endDate":    "<YYYY-MM-DD>",
  "roomIds":    ["<uuid-string>", ...]
}
```

| `eventType`     | Inventory responsibility                          |
|-----------------|---------------------------------------------------|
| `BOOKING_Ok`    | Attempt to **reserve** all listed rooms for the date range |
| `BOOKING_FALED` | **Release** the previously reserved rooms for the booking |

### Outbound — `InventoryResponse` (JSON, to booking):
```json
{
  "eventId":              "<new uuid>",
  "eventType":            "BOOKING_Ok" | "BOOKING_FALED",
  "timestamp":            "<ISO-8601>",
  "bookingId":            "<echo inbound bookingId>",
  "status":               "<descriptive string>",
  "reservationConfirmed": true | false,
  "failedRooms":          [{"roomId": "<uuid>", "reason": "<string>"}]
}
```

Booking reads only `reservationConfirmed` to decide saga progression.
`status` and `failedRooms` are for logging / rejection messages.

### Topology (from `booking-service` RabbitMqConfig):
| Element | Value |
|---------|-------|
| Exchange (inbound to inventory) | `${RABBITMQ_EXCHANGE_INVENTORY}` (DirectExchange) |
| Routing key (booking → inventory) | `inventory.request` |
| Queue (inventory listens on) | `inventory.request.queue` |
| Routing key (inventory → booking) | `inventory.response.key` |
| Queue (booking listens on inventory res) | `${RABBITMQ_QUEUE_INVENTORY_RES}` |

Booking uses Jackson2JsonMessageConverter — payload is plain JSON, no AMQP type headers required.

---

## Affected Areas

- `pyproject.toml` — add `pika` dependency.
- `internal/domain/entities/room.py` — add `reserve(booking_id, date_range)` and `release(booking_id)` methods + domain invariants.
- `internal/domain/entities/room_availability.py` — needs `booking_id` tracking to support release; or a separate `Reservation` entity/VO.
- `internal/domain/events/room_events.py` — add `RoomReserved` and `RoomReleased` domain events.
- `internal/domain/repositories/room_repository.py` — add `get_by_id(room_id)` (booking uses UUIDs for rooms).
- `internal/application/commands/` — add `ReserveRoomsCommand` and `ReleaseRoomsCommand`.
- `internal/application/usecases/` — add `ReserveRoomsUseCase` and `ReleaseRoomsUseCase`.
- `internal/application/errors.py` — add `RoomNotFoundError`, `RoomNotAvailableError`.
- `internal/infrastructure/config/settings.py` — add RabbitMQ settings fields.
- `internal/infrastructure/messaging/` — new package: `rabbitmq_inventory_reservation_consumer.py` (pika consumer).
- `internal/infrastructure/persistence/models.py` — add `ReservationModel` (or extend `RoomAvailabilityModel`) to track `booking_id`.
- `internal/infrastructure/persistence/sqlalchemy_room_repository.py` — add `get_by_id()`.
- `internal/interfaces/messaging/` — new package: `contracts.py` (BookingCreatedMessage), `inventory_reservation_consumer.py` (pure handler).
- `alembic/` — new migration for reservation tracking column/table.
- `test/unit/interfaces/` — consumer handler tests (pure, no pika).
- `test/integration/` — pika-based consumer integration tests.
- `.env.example` — add RabbitMQ env vars.

---

## Key Design Question: Reservation Tracking

Current `RoomAvailability` is a simple `DateRange` VO with no booking reference. To support:
1. **Reserve**: mark a room as unavailable for a booking.
2. **Release**: undo the reservation for a specific booking.

Two options exist:

### Option A — Extend `RoomAvailability` with `booking_id`
Make `RoomAvailability` a mutable aggregate child with `booking_id: UUID | None`.
- Simple: no new table, just adds a column.
- Limitation: one room = one reservation at a time (no multi-booking per room for different dates).
- Sufficient for the current scope (saga reserves exactly the rooms in the booking).

### Option B — Separate `Reservation` entity
Add a `Reservation(reservation_id, room_id, booking_id, date_range, status)` entity, tracked as a child collection of `Room`.
- Full flexibility for overlapping date ranges and multiple concurrent bookings.
- More moving parts: new table, repo method, additional migration.
- Needed if rooms should be bookable for non-overlapping periods simultaneously.

**Recommendation**: Start with **Option A** (extend `RoomAvailability` + `booking_id` column).
The current domain model is immature, booking sends one booking per room list, and the saga only tracks one reservation per booking. We can migrate to Option B if multi-reservation is ever required.

---

## Approaches

### Approach 1 — Mirror customer-service pattern exactly (recommended)
Follow the exact same layering: `interfaces/messaging/contracts.py` + pure consumer + pika infra runner + settings extension.

- **Pros**: consistent with the only existing Python service pattern; all tests are pure (no pika in unit); pika only enters at integration level; clean separation.
- **Cons**: requires touching 10+ files; needs `pika` added.
- **Effort**: Medium.

### Approach 2 — Single fat consumer in infrastructure
Put all logic (parsing, use-case call, publish reply) directly in the pika callback.

- **Pros**: fewer files.
- **Cons**: untestable without a broker; violates hexagonal boundaries; diverges from customer-service patterns; breaks `strict_tdd`.
- **Effort**: Low (but wrong).

### Approach 3 — FastAPI lifespan + asyncio pika
Use `aio-pika` or `aiormq` inside a FastAPI lifespan for a unified async process.

- **Pros**: single process; no separate worker needed.
- **Cons**: adds async complexity; customer-service uses sync pika successfully; needs different tooling.
- **Effort**: High.

---

## Recommendation

**Use Approach 1.**

Vertical slice to implement safely:
1. Add `pika` + `pika-stubs` to `pyproject.toml`.
2. Extend `Room` domain with `reserve()` and `release()` + domain events.
3. Extend `RoomAvailabilityModel` with `booking_id` + Alembic migration.
4. Add `get_by_id()` to `RoomRepository` protocol and SQLAlchemy implementation.
5. Add `ReserveRoomsUseCase` and `ReleaseRoomsUseCase` application commands.
6. Add `internal/interfaces/messaging/contracts.py` — `BookingCreatedMessage.from_payload()`.
7. Add `internal/interfaces/messaging/inventory_reservation_consumer.py` — pure handler returning `HandlingResult`.
8. Add `internal/infrastructure/messaging/rabbitmq_inventory_reservation_consumer.py` — pika runner with `ensure_topology()`.
9. Extend `InventoryServiceSettings` with RabbitMQ fields.
10. Update `.env.example`.
11. Wire everything in `main.py` (or a separate worker entry point).

---

## Contract Testing Strategy

Follow the customer-service pattern:

**Unit tests** (`test/unit/interfaces/test_inventory_reservation_consumer.py`):
- Test the pure consumer handler with stub use cases.
- Scenarios: `BOOKING_Ok` all rooms available → `reservationConfirmed=true`; one room unavailable → `reservationConfirmed=false` + `failedRooms`; `BOOKING_FALED` → release triggered; invalid payload → discard (no requeue); unknown eventType → discard.

**Integration tests** (`test/integration/test_rabbitmq_inventory_reservation_consumer.py`):
- Use `testcontainers` (already in dev dependencies) to spin up a real RabbitMQ.
- Publish a `BookingCreatedEvent` JSON to `inventory.request.queue`.
- Call `consumer.process_next_message()`.
- Assert the `InventoryResponse` JSON appears on the booking response exchange/queue.
- This proves the full round-trip without booking-service running.

No pact / contract file needed — the contract is fully specified in the booking source code and verified by the integration test.

---

## Risks

- `BookingEventType` enum values are `BOOKING_Ok` (mixed case) and `BOOKING_FALED` (typo — single `L`). The Python contract MUST match exactly; any normalization will break.
- `RoomAvailability` currently has no `booking_id`; a migration is required before the consumer can work end-to-end.
- `roomIds` in the inbound event contains room UUIDs, but `RoomRepository` only exposes `get_by_room_number()`. A new `get_by_id()` method is mandatory.
- No `pika` in current dependencies — must be added and reflected in `uv.lock`.
- The booking-service uses a `DirectExchange` but customer-service uses `topic` in `ensure_topology()`. Inventory MUST declare a `direct` exchange to match booking.
- `pika` is not in `pyproject.toml` — will cause `ModuleNotFoundError` at runtime until added.

---

## Ready for Proposal

Yes. All contract details are confirmed from booking source. The minimum vertical slice and affected files are fully mapped. Proceed to `sdd-propose`.
