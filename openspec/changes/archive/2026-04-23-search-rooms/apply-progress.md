## Implementation Progress

**Change**: search-rooms
**Mode**: Strict TDD

### Completed Tasks
- [x] 1.1 Update `internal/domain/repositories/room_repository.py` to declare `search(...)` with `check_in`, `check_out`, `room_type`, `max_price`, and `min_capacity`.
- [x] 1.2 Create `internal/application/queries/__init__.py` and `internal/application/queries/search_rooms_query.py` with immutable `SearchRoomsQuery` and `RoomSummary` DTOs.
- [x] 1.3 RED: create `test/unit/application/test_search_rooms_use_case.py` for stay-window validation, optional filter forwarding, and room-to-summary mapping.
- [x] 1.4 GREEN: implement `internal/application/queries/search_rooms_use_case.py` to build `DateRange`, call `RoomRepository.search(...)`, and return summaries.
- [x] 1.5 REFACTOR: clean imports and helper mapping in `internal/application/queries/` without changing tested behavior.
- [x] 2.1 RED: extend `test/integration/persistence/test_sqlalchemy_room_repository.py` for overlap coverage, `booking_id IS NULL`, `AVAILABLE` status, `room_type`, `max_price`, and `min_capacity`.
- [x] 2.2 GREEN: implement `search(...)` in `internal/infrastructure/persistence/sqlalchemy_room_repository.py` with one SQLAlchemy query joining `rooms` and `room_availability`.
- [x] 2.3 REFACTOR: keep repository mapping/loading consistent with existing persistence helpers while preserving filter semantics.
- [x] 3.1 RED: create `test/contract/test_get_rooms.py` for `GET /rooms` success, filter combinations, and ignoring booking-style params; update `test/unit/interfaces/test_app_bootstrap.py` to assert both `GET /rooms` and `POST /rooms` exist.
- [x] 3.2 Update `internal/interfaces/rest/schemas.py` with `RoomSummary` and `SearchRoomsResponse` models matching the response contract.
- [x] 3.3 GREEN: modify `internal/interfaces/rest/app.py` to add `GET /rooms`, parse query params, invoke `SearchRoomsUseCase`, and translate invalid stay windows to `400`.
- [x] 3.4 REFACTOR: preserve existing `POST /rooms` wiring and remove duplication in REST dependency/setup code.
- [x] 4.1 Run `uv run pytest test/unit/application/test_search_rooms_use_case.py test/unit/interfaces/test_app_bootstrap.py test/contract/test_get_rooms.py` to verify route contract and use case scenarios.
- [x] 4.2 Run `uv run pytest test/integration/persistence/test_sqlalchemy_room_repository.py` to verify repository filtering against booked, maintenance, price, capacity, and type cases.
- [x] 4.3 Run `uv run pytest --cov=internal --cov-report=term-missing` and confirm all spec scenarios for basic search, filtered search, unavailable-room exclusion, and out-of-scope booking behavior are covered.

### Corrective Apply Pass (verify alignment)
- [x] Aligned `GET /rooms` query parameters with the design and delta spec: `check_in` / `check_out`.
- [x] Updated the base inventory spec to promote room search from out-of-scope into a first-class requirement.
- [x] Repaired repository test doubles so `pyright` accepts the expanded `RoomRepository` protocol after adding `search(...)`.
- [x] Cleaned import/order/format issues so `ruff` and `black --check` pass.

### Files Changed
| File | Action | What Was Done |
|------|--------|---------------|
| `internal/domain/repositories/room_repository.py` | Modified | Added `search(...)` protocol contract and normalized imports. |
| `internal/application/queries/{__init__.py,search_rooms_query.py,search_rooms_use_case.py}` | Created | Added query DTOs and use case for room search. |
| `internal/infrastructure/persistence/sqlalchemy_room_repository.py` | Modified | Added SQLAlchemy search query with availability, booking, status, price, capacity, and type filters. |
| `internal/interfaces/rest/{app.py,schemas.py}` | Modified | Added `GET /rooms` response contract and aligned query params to `check_in` / `check_out`. |
| `test/unit/application/test_search_rooms_use_case.py` | Created | Added stay-window validation, filter forwarding, and summary mapping coverage. |
| `test/integration/persistence/test_sqlalchemy_room_repository.py` | Modified | Added repository search semantics coverage. |
| `test/contract/test_get_rooms.py` | Created | Added REST contract proof for search endpoint and query behavior. |
| `test/unit/interfaces/test_app_bootstrap.py` | Modified | Verified OpenAPI exposes both `GET /rooms` and `POST /rooms`. |
| `test/unit/application/test_{register_room_use_case,release_rooms_use_case,reserve_rooms_use_case}.py` | Modified | Added `search(...)` stubs so repository doubles remain protocol-compatible. |
| `test/integration/messaging/test_rabbitmq_inventory_reservation_consumer.py` | Modified | Added `search(...)` no-op to keep protocol compatibility under pyright. |
| `openspec/specs/inventory-management/spec.md` | Modified | Lifted `SearchRooms` out-of-scope restriction and merged search scenarios into the base spec. |

### TDD / Verification Evidence
- `uv run pytest test/unit/application/test_search_rooms_use_case.py test/unit/interfaces/test_app_bootstrap.py test/contract/test_get_rooms.py` → 8 passed
- `uv run pytest test/integration/persistence/test_sqlalchemy_room_repository.py` → 6 passed
- `uv run pytest --cov=internal --cov-report=term-missing` → 64 passed, 98% total coverage
- `uv run ruff check . && uv run black --check . && uv run pyright` → passed

### Deviations from Design
None after the corrective pass. The endpoint contract now matches the documented `check_in` / `check_out` interface.

### Issues Found
- Initial implementation exposed `start_date` / `end_date` instead of `check_in` / `check_out`; corrected during verify.
- Adding `search(...)` to the repository protocol required updating older in-memory/no-op test doubles for type safety.

### Remaining Tasks
- [x] None.

### Status
15/15 tasks complete. Ready for archive.
