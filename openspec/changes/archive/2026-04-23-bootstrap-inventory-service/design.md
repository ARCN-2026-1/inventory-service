# Design: Bootstrap Inventory Service

## Technical Approach

Bootstrap `inventory-service` by mirroring the `customer-service` FastAPI + hexagonal skeleton, but only for the first slice: `RegisterRoom` and `GET /health`. Domain invariants stay in `internal/domain`, orchestration in `internal/application`, persistence adapters in `internal/infrastructure`, and HTTP wiring in `internal/interfaces/rest`. MySQL + Alembic are used from day one so the bootstrap matches the target runtime.

`room_number` uniqueness is enforced twice by design: the use case checks existence through `RoomRepository.get_by_room_number`, and the first migration creates a database-level unique constraint on `rooms.room_number` to protect against concurrent writes and out-of-band inserts.

## Architecture Decisions

### Decision: Mirror `customer-service`

| Option | Tradeoff | Decision |
|---|---|---|
| New layout | Faster initially, inconsistent with repo standard | No |
| Mirror canonical service | Lower cognitive load, easier maintenance | Yes |

**Rationale**: `openspec/config.yaml` names `customer-service` as the canonical reference.

### Decision: Keep Change 1 without auth

| Option | Tradeoff | Decision |
|---|---|---|
| Add auth now | Better security, larger scope | No |
| No auth yet | Matches confirmed scope, smaller bootstrap | Yes |

**Rationale**: Proposal and spec explicitly defer authentication.

### Decision: Start with MySQL + Alembic

| Option | Tradeoff | Decision |
|---|---|---|
| SQLite first | Easier local setup, wrong runtime target | No |
| MySQL first | More setup, production-aligned | Yes |

**Rationale**: The proposal already commits to a shared MySQL instance and dedicated schema.

### Decision: Enforce `room_number` uniqueness in app and DB

| Option | Tradeoff | Decision |
|---|---|---|
| App check only | Simpler code, race-condition gap remains | No |
| DB constraint only | Strong integrity, weaker domain feedback path | No |
| App check + DB unique constraint | Slight duplication, strongest safety | Yes |

**Rationale**: The user confirmed DB-level uniqueness. The application gives deterministic business feedback, and the database remains the final integrity boundary.

## Data Flow

```text
Client -> REST /rooms -> RegisterRoomCommand
       -> RegisterRoomUseCase.execute()
       -> RoomRepository.get_by_room_number()
       -> Room.register()
       -> RoomRepository.add(room)
       -> SQLAlchemy session -> MySQL UNIQUE(room_number)
       -> 201 {room_id}
```

Duplicate path:

```text
Client -> REST /rooms
REST -> UseCase
UseCase -> repository lookup detects duplicate OR
Repository -> DB unique constraint rejects concurrent duplicate
Repository/UseCase -> duplicate-room-number error
REST -> conflict response
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | Create | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PyMySQL, pytest, testcontainers, ruff, black, pyright. |
| `main.py` | Create | ASGI entrypoint using `create_app()`. |
| `internal/domain/entities/{room.py,room_availability.py}` | Create | Aggregate/entity behavior and event collection. |
| `internal/domain/valueobjects/{money,date_range,room_type,room_operational_status}.py` | Create | Domain invariants and enum-style value objects. |
| `internal/domain/repositories/room_repository.py` | Create | Repository protocol with lookup by `room_number`. |
| `internal/application/commands/register_room.py` | Create | Input command dataclass. |
| `internal/application/usecases/register_room.py` | Create | Registration orchestration and duplicate check. |
| `internal/infrastructure/config/settings.py` | Create | `INVENTORY_SERVICE_` settings. |
| `internal/infrastructure/persistence/models.py` | Create | SQLAlchemy models with unique `room_number`. |
| `internal/infrastructure/persistence/sqlalchemy_room_repository.py` | Create | Persistence adapter translating duplicate writes consistently. |
| `alembic.ini`, `alembic/env.py`, `alembic/versions/*.py` | Create | MySQL migration bootstrap including unique constraint/index on `rooms.room_number`. |
| `internal/interfaces/rest/{app.py,schemas.py}` | Create | `/rooms`, `/health`, and error mapping. |
| `test/unit`, `test/integration`, `test/contract` | Create | Layered tests for domain, persistence, and HTTP contracts. |

## Interfaces / Contracts

```python
@dataclass(slots=True)
class RegisterRoomCommand:
    room_number: str
    room_type: str
    capacity: int
    price_amount: Decimal
    price_currency: str
    operational_status: str
    availability_start: date | None = None
    availability_end: date | None = None
```

`RoomRepository`:
- `get_by_room_number(room_number: str) -> Room | None`
- `add(room: Room) -> None`

REST:
- `POST /rooms` -> `201 Created` with `{ "room_id": "uuid" }`
- `POST /rooms` -> conflict error for duplicate `room_number`
- `POST /rooms` -> `400 Bad Request` for invalid `Money` or `DateRange`
- `GET /health` -> `200 OK`

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `Money`, `DateRange`, `Room.register`, duplicate-check branch in use case | Pure pytest, strict TDD. |
| Integration | SQLAlchemy mapping, Alembic schema, DB rejection of duplicate `room_number` | pytest + MySQL testcontainer. |
| Contract | `GET /health`, `POST /rooms` success, invalid payloads, duplicate room number, no-auth access | FastAPI TestClient with test DB. |

No e2e suite is planned because `openspec/config.yaml` marks e2e unavailable.

## Migration / Rollout

The first Alembic migration creates `rooms` and `room_availability`, plus a unique constraint/index on `rooms.room_number`. Runtime URL comes from settings; local default remains `mysql+pymysql://inventory:secret@localhost:3306/inventory_service?charset=utf8mb4`. Rollout order: provision schema/user, run Alembic upgrade, start API container. No data migration required.

## Open Questions

None.
