# Exploration: bootstrap-inventory-service

## Current State

The `inventory-service` standalone repo exists at `/home/msi/dev/inventory-service` and contains only:
- `.git/` — initialized repo
- `.atl/` — agent tooling metadata
- `openspec/` — SDD config already bootstrapped (`config.yaml` is present and complete)

There is **no Python code, no pyproject.toml, no Dockerfile, no alembic setup, no tests**. The repo is a clean slate ready to be scaffolded.

### Reference Artifacts Available

| Source | Content |
|--------|---------|
| `hotel-ddd/docs/ddd/bounded-contexts/inventory.md` | Full DDD spec: aggregate Root (Room), entity (RoomAvailability), value objects, invariants, policies, domain events |
| `hotel-ddd/docs/ddd/context-map.md` | Integration contracts: Booking→Inventory sync (SearchRooms) + async (BlockRoomAvailability, ReleaseRoomAvailability via RabbitMQ) |
| `customer-service/` | Complete canonical Python/FastAPI/hexagonal skeleton to mirror exactly |
| `hotel-ddd/services/inventory-service/` | Empty stub skeleton (`.gitkeep` only) — no code to reuse |

### customer-service Structural Fingerprint (canonical reference)

```
internal/
  domain/
    entities/          # dataclass(slots=True) aggregate roots
    events/            # frozen dataclass domain events
    valueobjects/      # value objects (Email pattern → RoomType, Money, etc.)
    repositories/      # abstract Protocol repository interfaces
    services/          # domain service abstractions (EventPublisher protocol)
    errors.py          # DomainRuleViolation
  application/
    commands/          # input command dataclasses
    queries/           # query dataclasses
    dto/               # output DTO dataclasses
    usecases/          # orchestrate domain + infra
    errors.py          # application-level exceptions
  infrastructure/
    config/settings.py # pydantic-settings, env_prefix
    persistence/
      models.py        # SQLAlchemy ORM models (DeclarativeBase)
      unit_of_work.py  # create_session_factory
      sqlalchemy_*_repository.py
    messaging/
      factory.py           # create_event_publisher, connection_factory
      rabbitmq_*_consumer.py  # ensure_topology + polling loop
      rabbitmq_event_publisher.py
      in_memory_event_publisher.py
  interfaces/
    rest/
      app.py           # create_app(settings) → FastAPI
      schemas.py       # Pydantic request/response schemas
      security.py      # JWT middleware
    messaging/
      *_consumer.py    # message handler (parse → use case → result)
      contracts.py     # typed message schema
main.py                # from internal.interfaces.rest.app import create_app; app = create_app()
consumer.py            # build_worker_runtime() + main()
pyproject.toml
alembic.ini
alembic/env.py + versions/
Dockerfile
docker-compose.yml
```

### RabbitMQ Pattern (customer-service)

- **Topic exchange**, durable, one per service
- `ensure_topology()` declares exchange + queue + binding before consuming
- `process_next_message()` uses `basic_get` (polling, not push)
- Request/response style: consumer reads from input queue, publishes result to response exchange
- Settings: `rabbitmq_input_queue`, `rabbitmq_request_exchange`, `rabbitmq_request_routing_key`, `rabbitmq_response_exchange`, `rabbitmq_response_routing_key`

### MySQL/Alembic Pattern (customer-service)

- `alembic.ini` hardcodes local dev URL; `env.py` overrides from settings at runtime
- `INVENTORY_SERVICE_` env prefix for all settings
- DB connection: `mysql+pymysql://inventory:secret@<host>:3306/inventory_service?charset=utf8mb4`
- One dedicated DB user per service, one schema per service, shared MySQL instance
- `alembic/env.py` imports `Base.metadata` from ORM models

---

## Affected Areas

- `/home/msi/dev/inventory-service/` — entire repo to be scaffolded from scratch
- `openspec/config.yaml` — already present, guides generation rules
- `hotel-ddd/docs/ddd/bounded-contexts/inventory.md` — source of truth for domain model
- `hotel-ddd/docs/ddd/context-map.md` — integration contracts with Booking

---

## Domain Model Summary (from DDD source of truth)

### Aggregate Root: Room
- `room_id: UUID`
- `room_number: str`
- `room_type: RoomType` (enum: Simple | Doble | Suite | Familiar)
- `capacity: int`
- `price_per_night: Money` (value object — amount > 0)
- `operational_status: RoomOperationalStatus` (enum: Operativa | EnMantenimiento | Inactiva)
- `availability_periods: list[RoomAvailability]` — child entity collection

### Entity: RoomAvailability
- `availability_id: UUID`
- `room_id: UUID`
- `reservation_id: UUID`
- `date_range: DateRange` (value object — start_date, end_date)

### Value Objects
- `RoomType`, `RoomOperationalStatus`, `Money`, `DateRange`, `RoomFilter`

### Key Invariants
1. No overlapping `availability_periods` on same Room
2. Only `Operativa` rooms can accept new blocks
3. `price_per_night > 0` always
4. `Inactiva` rooms cannot have new periods

### Domain Events
- `RoomRegistered` — after `RegisterRoom` command
- `RoomStatusChanged` — after `UpdateRoomStatus` command
- `RoomAvailabilityBlocked` — after `BlockRoomAvailability` (triggered by Booking)
- `RoomAvailabilityReleased` — after `ReleaseRoomAvailability` (triggered by Booking)

### Commands and Actors
| Command | Actor | Transport |
|---------|-------|-----------|
| RegisterRoom | Admin | REST POST /rooms |
| UpdateRoomStatus | Admin | REST PATCH /rooms/{id}/status |
| SearchRooms | Customer/Booking | REST GET /rooms |
| BlockRoomAvailability | System (Booking) | RabbitMQ (async) |
| ReleaseRoomAvailability | System (Booking) | RabbitMQ (async) |

### Integration contracts (context-map)
- **Sync**: Booking calls inventory REST `GET /rooms?...` before creating a reservation
- **Async (inbound)**: Booking publishes `ReservationCreated` → inventory blocks availability
- **Async (inbound)**: Booking publishes `ReservationCancelled` → inventory releases availability

---

## Approaches

### 1. Full bootstrap in one change (everything at once)
Scaffold pyproject, Dockerfile, settings, full Room domain + all use cases, all REST routes, RabbitMQ consumer + topology, Alembic setup, tests.
- Pros: Everything works end-to-end immediately
- Cons: Change is huge, hard to review, high risk of mistakes in all layers at once
- Effort: High

### 2. Layered bootstrap — skeleton + first domain slice (recommended)
**Change 1 (bootstrap-inventory-service):** Project skeleton + Room domain model + `RegisterRoom` use case (admin REST) + MySQL/Alembic setup + pyproject + Dockerfile + health endpoint. No RabbitMQ consumer yet.
**Change 2:** `SearchRooms` query (REST GET /rooms with filter).
**Change 3:** RabbitMQ consumer for `BlockRoomAvailability` + `ReleaseRoomAvailability`.
**Change 4:** `UpdateRoomStatus` admin endpoint.
- Pros: Small reviewable changes, each independently deployable, mirrors customer-service bootstrap pattern
- Cons: Booking integration requires Change 3 before full e2e
- Effort: Medium per change, Low risk per review

### 3. Minimal skeleton only (no domain)
Just pyproject, Dockerfile, settings, health endpoint, Alembic empty init.
- Pros: Fastest to merge
- Cons: Provides no business value; still requires a domain change immediately after
- Effort: Low, but pointless

---

## Recommendation

**Use Approach 2 — Layered bootstrap.**

The **first change (`bootstrap-inventory-service`)** should deliver:

1. **Project skeleton** (pyproject.toml, Dockerfile, docker-compose.yml, .gitignore, sonar-project.properties) — mirror customer-service
2. **Domain layer**: `Room` aggregate, `RoomAvailability` entity, `RoomType`, `RoomOperationalStatus`, `Money`, `DateRange` value objects, `RoomRepository` protocol, domain events (`RoomRegistered`), `DomainRuleViolation`
3. **Application layer**: `RegisterRoomCommand`, `RegisterRoomUseCase`, application errors
4. **Infrastructure layer**: `InventoryServiceSettings` (env_prefix `INVENTORY_SERVICE_`), SQLAlchemy models (`rooms` + `room_availability` tables), `SqlAlchemyRoomRepository`, Alembic init + first migration
5. **Interfaces layer**: `POST /rooms` (admin-only REST), `GET /health`
6. **Tests**: Unit tests for Room aggregate invariants; integration test for repository; contract test for POST /rooms

**Deferred to subsequent changes:**
- `SearchRooms` REST query with `RoomFilter` (Change 2)
- RabbitMQ `BlockRoomAvailability` + `ReleaseRoomAvailability` consumer (Change 3)
- `UpdateRoomStatus` admin endpoint + `RoomStatusChanged` event (Change 4)
- `RoomAvailabilityBlocked` / `RoomAvailabilityReleased` domain events and their full Booking integration (Change 3)

### RabbitMQ topology for inventory-service (when implemented)
```
exchange: inventory.exchange (topic, durable)
input queue: inventory.availability.requests
request routing key: inventory.availability.request
response exchange: inventory.exchange
response routing key: inventory.availability.response.key
```

### MySQL/Alembic for inventory-service
```
DB user: inventory
DB password: secret (dev)
DB schema: inventory_service
alembic.ini url: mysql+pymysql://inventory:secret@localhost:3306/inventory_service?charset=utf8mb4
env_prefix: INVENTORY_SERVICE_
```

---

## Risks

- **Overlap invariant complexity**: The `Room.availability_periods` overlap check is non-trivial; must be covered with comprehensive unit tests in Change 1 even if the block operation is deferred (domain method `block_availability` can be written in Change 1, consumer wired in Change 3).
- **Money value object**: No existing `Money` type in customer-service — must be defined fresh. Use `Decimal` for amount, avoid float.
- **DateRange**: Same — new value object; must guard `start_date < end_date`.
- **No auth in inventory-service yet**: customer-service has JWT/bcrypt. For the first change, admin routes can be unprotected or use a simple API key via settings — decision needed before spec phase.
- **Shared MySQL instance**: Need to ensure the `inventory` DB user and `inventory_service` schema exist before Alembic runs. This is an ops concern that must be documented in a `scripts/` or `README.md`.

---

## Ready for Proposal

**Yes.** The scope of the first change is clear, bounded, and mirrors the proven customer-service pattern. The orchestrator can proceed to `sdd-propose` with:
- Change name: `bootstrap-inventory-service`
- First domain slice: `Room` aggregate + `RegisterRoom` use case + REST endpoint
- Deferred: SearchRooms, RabbitMQ consumer, UpdateRoomStatus
- Open question to resolve in proposal: admin auth strategy for first change (full JWT vs. unprotected vs. simple API key)
