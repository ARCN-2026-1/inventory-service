# Tasks: Search Rooms

## Phase 1: Domain and Query Foundation

- [x] 1.1 Update `internal/domain/repositories/room_repository.py` to declare `search(...)` with `check_in`, `check_out`, `room_type`, `max_price`, and `min_capacity`.
- [x] 1.2 Create `internal/application/queries/__init__.py` and `internal/application/queries/search_rooms_query.py` with immutable `SearchRoomsQuery` and `RoomSummary` DTOs.
- [x] 1.3 RED: create `test/unit/application/test_search_rooms_use_case.py` for stay-window validation, optional filter forwarding, and room-to-summary mapping.
- [x] 1.4 GREEN: implement `internal/application/queries/search_rooms_use_case.py` to build `DateRange`, call `RoomRepository.search(...)`, and return summaries.
- [x] 1.5 REFACTOR: clean imports and helper mapping in `internal/application/queries/` without changing tested behavior.

## Phase 2: Infrastructure Search Query

- [x] 2.1 RED: extend `test/integration/persistence/test_sqlalchemy_room_repository.py` for overlap coverage, `booking_id IS NULL`, `AVAILABLE` status, `room_type`, `max_price`, and `min_capacity`.
- [x] 2.2 GREEN: implement `search(...)` in `internal/infrastructure/persistence/sqlalchemy_room_repository.py` with one SQLAlchemy query joining `rooms` and `room_availability`.
- [x] 2.3 REFACTOR: keep repository mapping/loading consistent with existing persistence helpers while preserving filter semantics.

## Phase 3: REST Contract and Wiring

- [x] 3.1 RED: create `test/contract/test_get_rooms.py` for `GET /rooms` success, filter combinations, and ignoring booking-style params; update `test/unit/interfaces/test_app_bootstrap.py` to assert both `GET /rooms` and `POST /rooms` exist.
- [x] 3.2 Update `internal/interfaces/rest/schemas.py` with `RoomSummary` and `SearchRoomsResponse` models matching the response contract.
- [x] 3.3 GREEN: modify `internal/interfaces/rest/app.py` to add `GET /rooms`, parse query params, invoke `SearchRoomsUseCase`, and translate invalid stay windows to `400`.
- [x] 3.4 REFACTOR: preserve existing `POST /rooms` wiring and remove duplication in REST dependency/setup code.

## Phase 4: Verification

- [x] 4.1 Run `uv run pytest test/unit/application/test_search_rooms_use_case.py test/unit/interfaces/test_app_bootstrap.py test/contract/test_get_rooms.py` to verify route contract and use case scenarios.
- [x] 4.2 Run `uv run pytest test/integration/persistence/test_sqlalchemy_room_repository.py` to verify repository filtering against booked, maintenance, price, capacity, and type cases.
- [x] 4.3 Run `uv run pytest --cov=internal --cov-report=term-missing` and confirm all spec scenarios for basic search, filtered search, unavailable-room exclusion, and out-of-scope booking behavior are covered.
