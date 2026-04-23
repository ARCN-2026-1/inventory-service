# Tasks: Bootstrap Inventory Service

## Phase 1: Domain Foundation

- [x] 1.1 Create `pyproject.toml`, `main.py`, and package roots under `internal/{domain,application,infrastructure,interfaces}` mirroring the `customer-service` bootstrap without auth or RabbitMQ wiring.
- [x] 1.2 RED: add `test/unit/domain/test_money.py` and `test/unit/domain/test_date_range.py` covering positive-price and valid-date-range invariants.
- [x] 1.3 GREEN: implement `internal/domain/valueobjects/{money.py,date_range.py}` plus a shared domain exception for invariant violations.
- [x] 1.4 RED: add `test/unit/domain/test_room.py` for `Room.register`, optional availability creation, and room-registered event emission.
- [x] 1.5 GREEN/REFACTOR: implement `internal/domain/entities/{room.py,room_availability.py}`, `internal/domain/valueobjects/{room_type.py,room_operational_status.py}`, and `internal/domain/repositories/room_repository.py`.

## Phase 2: Application Layer

- [x] 2.1 RED: add `test/unit/application/test_register_room_use_case.py` for successful registration and duplicate `room_number` rejection through repository lookup.
- [x] 2.2 GREEN: create `internal/application/commands/register_room.py` and `internal/application/usecases/register_room.py` to orchestrate aggregate creation and uniqueness checks.

## Phase 3: Infrastructure & Persistence

- [x] 3.1 Create `internal/infrastructure/config/settings.py`, database session/bootstrap modules, `alembic.ini`, and `alembic/env.py` for MySQL `inventory_service` connectivity.
- [x] 3.2 RED: add `test/integration/persistence/test_sqlalchemy_room_repository.py` validating room persistence, availability mapping, and duplicate `room_number` failure after migrations run.
- [x] 3.3 GREEN: implement `internal/infrastructure/persistence/models.py` and `sqlalchemy_room_repository.py`, including `get_by_room_number` support.
- [x] 3.4 Create the initial `alembic/versions/*.py` migration for `rooms` and `room_availability`, enforcing a DB-level unique constraint/index on `rooms.room_number`.

## Phase 4: Interfaces & Contracts

- [x] 4.1 RED: add `test/contract/test_health.py` and `test/contract/test_post_rooms.py` for `GET /health`, `POST /rooms` success, invalid price, invalid dates, and no-auth access.
- [x] 4.2 GREEN: implement `internal/interfaces/rest/{schemas.py,app.py}` and finalize `main.py` wiring, exception mapping, and use-case dependency injection.

## Phase 5: Verification & Cleanup

- [x] 5.1 Align local runtime assets such as `.env.example` and startup notes with the bootstrap paths/settings used by the app and Alembic.
- [x] 5.2 Run and fix `uv run pytest --cov=internal --cov-report=term-missing`, `uv run ruff check .`, `uv run black --check .`, and `uv run pyright`.
