## Implementation Progress

**Change**: bootstrap-inventory-service
**Mode**: Strict TDD

### Completed Tasks
- [x] 1.1 Create `pyproject.toml`, `main.py`, and package roots under `internal/{domain,application,infrastructure,interfaces}` mirroring the `customer-service` bootstrap without auth or RabbitMQ wiring.
- [x] 1.2 RED: add `test/unit/domain/test_money.py` and `test/unit/domain/test_date_range.py` covering positive-price and valid-date-range invariants.
- [x] 1.3 GREEN: implement `internal/domain/valueobjects/{money.py,date_range.py}` plus a shared domain exception for invariant violations.
- [x] 1.4 RED: add `test/unit/domain/test_room.py` for `Room.register`, optional availability creation, and room-registered event emission.
- [x] 1.5 GREEN/REFACTOR: implement `internal/domain/entities/{room.py,room_availability.py}`, `internal/domain/valueobjects/{room_type.py,room_operational_status.py}`, and `internal/domain/repositories/room_repository.py`.
- [x] 2.1 RED: add `test/unit/application/test_register_room_use_case.py` for successful registration and duplicate `room_number` rejection through repository lookup.
- [x] 2.2 GREEN: create `internal/application/commands/register_room.py` and `internal/application/usecases/register_room.py` to orchestrate aggregate creation and uniqueness checks.
- [x] 3.1 Create `internal/infrastructure/config/settings.py`, database session/bootstrap modules, `alembic.ini`, and `alembic/env.py` for MySQL `inventory_service` connectivity.
- [x] 3.2 RED: add `test/integration/persistence/test_sqlalchemy_room_repository.py` validating room persistence, availability mapping, and duplicate `room_number` failure after migrations run.
- [x] 3.3 GREEN: implement `internal/infrastructure/persistence/models.py` and `sqlalchemy_room_repository.py`, including `get_by_room_number` support.
- [x] 3.4 Create the initial `alembic/versions/*.py` migration for `rooms` and `room_availability`, enforcing a DB-level unique constraint/index on `rooms.room_number`.
- [x] 4.1 RED: add `test/contract/test_health.py` and `test/contract/test_post_rooms.py` for `GET /health`, `POST /rooms` success, invalid price, invalid dates, and no-auth access.
- [x] 4.2 GREEN: implement `internal/interfaces/rest/{schemas.py,app.py}` and finalize `main.py` wiring, exception mapping, and use-case dependency injection.
- [x] 5.1 Align local runtime assets such as `.env.example` and startup notes with the bootstrap paths/settings used by the app and Alembic.
- [x] 5.2 Run and fix `uv run pytest --cov=internal --cov-report=term-missing`, `uv run ruff check .`, `uv run black --check .`, and `uv run pyright`.

### Corrective Apply Pass (Verify Gaps)
- [x] Added contract proof that the bootstrap exposes only `GET /health` and `POST /rooms`, so `SearchRooms` remains unsupported.
- [x] Added contract proof that `PATCH /rooms/{room_id}/status` is unavailable, so `UpdateRoomStatus` remains unsupported.
- [x] Added explicit bootstrap proof that no RabbitMQ startup/shutdown hooks are wired in this initial slice.
- [x] Strengthened bootstrap unit assertions to verify route registration and injected repository wiring instead of only `FastAPI` types.
- [x] Updated `openspec/config.yaml` integration tooling metadata to match MySQL testcontainers.
- [x] Covered the blank-currency invariant branch in `Money`.

### Files Changed
| File | Action | What Was Done |
|------|--------|---------------|
| `pyproject.toml` | Created | Bootstrapped Python project dependencies, pytest/quality tool config, and added `cryptography` for MySQL auth in testcontainers. |
| `main.py` | Created | Exposed ASGI app via `create_app()`. |
| `internal/domain/errors.py` | Created | Added shared `DomainRuleViolation` exception. |
| `internal/domain/valueobjects/*.py` | Created | Implemented `Money`, `DateRange`, `RoomType`, and `RoomOperationalStatus` with invariants. |
| `internal/domain/entities/*.py` | Created | Implemented `Room`, `RoomAvailability`, and `RoomRegistered` event handling. |
| `internal/application/commands/register_room.py` | Created | Added command contract for room registration. |
| `internal/application/usecases/register_room.py` | Created | Implemented duplicate check and room registration orchestration. |
| `internal/infrastructure/config/settings.py` | Created | Added MySQL-first settings with `INVENTORY_SERVICE_` prefix. |
| `internal/infrastructure/persistence/*.py` | Created | Added SQLAlchemy base/models, session factory, and repository adapter. |
| `alembic.ini`, `alembic/env.py`, `alembic/versions/20260423_000001_create_rooms_tables.py` | Created | Bootstrapped Alembic and initial schema with unique `room_number`. |
| `internal/interfaces/rest/app.py` | Created | Added `/health` and `/rooms`, dependency injection, and error mapping without auth. |
| `internal/interfaces/rest/schemas.py` | Created | Added request/response DTOs with camelCase aliases. |
| `test/contract/test_unsupported_capabilities.py` | Created | Added runtime contract proof for unsupported search and room-status-update capabilities, plus OpenAPI proof that only bootstrap routes are exposed. |
| `test/unit/interfaces/test_app_bootstrap.py` | Modified | Replaced type-only assertions with behavioral checks for route registration, repository wiring, and absence of RabbitMQ lifecycle hooks. |
| `test/unit/domain/test_money.py` | Modified | Added blank-currency invariant coverage. |
| `test/**` | Created/Modified | Added unit, integration, and contract coverage for the bootstrap slice and verify-gap proofs. |
| `openspec/config.yaml` | Modified | Corrected integration testing metadata to the actual MySQL testcontainers toolchain. |
| `.env.example`, `README.md` | Created | Documented runtime configuration and local startup flow. |

### TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `test/unit/interfaces/test_app_bootstrap.py` | Unit | N/A (new) | ✅ Written | ✅ 2 passed | ✅ 2 cases | ➖ None needed |
| 1.2 | `test/unit/domain/test_money.py`, `test/unit/domain/test_date_range.py` | Unit | N/A (new) | ✅ Written | ✅ 6 passed | ✅ 6 cases | ➖ None needed |
| 1.3 | `test/unit/domain/test_money.py`, `test/unit/domain/test_date_range.py` | Unit | N/A (new) | ✅ Written | ✅ 6 passed | ✅ 6 cases | ✅ Currency normalization extracted into VO |
| 1.4 | `test/unit/domain/test_room.py` | Unit | N/A (new) | ✅ Written | ✅ 3 passed | ✅ 3 cases | ➖ None needed |
| 1.5 | `test/unit/domain/test_room.py` | Unit | N/A (new) | ✅ Written | ✅ 3 passed | ✅ 3 cases | ✅ Availability creation kept in aggregate factory |
| 2.1 | `test/unit/application/test_register_room_use_case.py` | Unit | N/A (new) | ✅ Written | ✅ 2 passed | ✅ 2 cases | ➖ None needed |
| 2.2 | `test/unit/application/test_register_room_use_case.py` | Unit | N/A (new) | ✅ Written | ✅ 2 passed | ✅ 2 cases | ✅ Enum conversion isolated in use case |
| 3.1 | `test/unit/infrastructure/test_settings_and_database.py` | Unit | N/A (new) | ✅ Written | ✅ 2 passed | ✅ 2 cases | ➖ None needed |
| 3.2 | `test/integration/persistence/test_sqlalchemy_room_repository.py` | Integration | N/A (new) | ✅ Written | ✅ 2 passed | ✅ 2 cases | ➖ None needed |
| 3.3 | `test/integration/persistence/test_sqlalchemy_room_repository.py` | Integration | N/A (new) | ✅ Written | ✅ 2 passed | ✅ 2 cases | ✅ Mapping helpers keep ORM translation isolated |
| 3.4 | `test/integration/persistence/test_sqlalchemy_room_repository.py` | Integration | N/A (new) | ✅ Written | ✅ 2 passed | ✅ 2 cases | ➖ None needed |
| 4.1 | `test/contract/test_health.py`, `test/contract/test_post_rooms.py` | Contract | N/A (new) | ✅ Written | ✅ 5 passed | ✅ 5 cases | ➖ None needed |
| 4.2 | `test/contract/test_health.py`, `test/contract/test_post_rooms.py` | Contract | ✅ 2/2 | ✅ Written | ✅ 5 passed | ✅ 5 cases | ✅ Error mapping centralized in app factory |
| 5.1 | `test/unit/infrastructure/test_runtime_assets.py` | Unit | N/A (new) | ✅ Written | ✅ 2 passed | ✅ 2 cases | ➖ None needed |
| 5.2 | `N/A — verification commands` | Verification | ✅ 24/24 | ➖ Command-driven verification task | ✅ pytest+ruff+black+pyright passed | ➖ Structural verification task | ➖ None needed |

### Corrective Pass TDD Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Verify gaps: unsupported capabilities | `test/contract/test_unsupported_capabilities.py` | Contract | ✅ 5/5 | ✅ Written | ✅ 3 passed | ✅ OpenAPI + GET `/rooms` + PATCH `/rooms/{id}/status` | ➖ None needed |
| Verify gaps: bootstrap assertions | `test/unit/interfaces/test_app_bootstrap.py` | Unit | ✅ 2/2 | ✅ Written | ✅ 2 passed | ✅ Route set + repository wiring + no startup/shutdown hooks | ➖ None needed |
| Verify gaps: blank currency invariant | `test/unit/domain/test_money.py` | Unit | ✅ 3/3 | ✅ Written | ✅ 4 passed | ✅ Positive amount + non-positive amount + blank currency | ➖ None needed |
| Verify gaps: re-verify checks | `uv run pytest --cov=internal --cov-report=term-missing`; `uv run ruff check .`; `uv run black --check .`; `uv run pyright` | Verification | ✅ 10/10 | ➖ Command-driven verification task | ✅ `pytest` passed with `TESTCONTAINERS_RYUK_DISABLED=true`; quality checks passed | ➖ Structural verification task | ➖ None needed |

### Test Summary
- **Total tests written**: 28
- **Total tests passing**: 28
- **Layers used**: Unit (18), Integration (2), Contract (8), E2E (0)
- **Approval tests**: None — no refactoring-only tasks
- **Pure functions created**: 1 (`_to_camel`)

### Deviations from Design
None — implementation matches design.

### Issues Found
- MySQL testcontainers exposed a `mysql://` URL and `caching_sha2_password` auth; resolved by normalizing to `mysql+pymysql://` and adding `cryptography`.
- Full-suite `pytest` initially failed because local testcontainers could not connect to Ryuk (`ConnectionRefusedError`); re-running with `TESTCONTAINERS_RYUK_DISABLED=true` produced a clean 28/28 pass and 99% coverage, so the blocker is environmental rather than application behavior.

### Remaining Tasks
- [x] None.

### Status
15/15 tasks complete. Ready for verify.
