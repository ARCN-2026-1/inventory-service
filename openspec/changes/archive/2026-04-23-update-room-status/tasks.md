# Tasks: Update Room Status

## Phase 1: Domain and Contract Foundation

- [x] 1.1 RED: add `test/unit/domain/test_room.py` cases for `update_operational_status()` idempotency, event payload, and old-status capture.
- [x] 1.2 RED: add `test/unit/application/test_update_room_status_use_case.py` for success, invalid status, and missing-room paths.
- [x] 1.3 RED: add `test/contract/test_patch_room_status.py` and update `test/unit/interfaces/test_app_bootstrap.py` for the new route.

## Phase 2: Core Implementation

- [x] 2.1 GREEN: add `RoomStatusChanged` to `internal/domain/events/room_events.py` and `Room.update_operational_status()` in `internal/domain/entities/room.py`.
- [x] 2.2 GREEN: create `internal/application/commands/update_room_status.py` and `internal/application/usecases/update_room_status.py`.
- [x] 2.3 REFACTOR: map `RoomNotFoundError` to `404` in `internal/interfaces/rest/app.py` and keep existing error handling intact.

## Phase 3: REST Wiring

- [x] 3.1 GREEN: add `UpdateRoomStatusRequest` to `internal/interfaces/rest/schemas.py`.
- [x] 3.2 GREEN: add `PATCH /rooms/{room_id}/status` to `internal/interfaces/rest/app.py` returning `204 No Content`.

## Phase 4: Verification

- [x] 4.1 Run `uv run pytest test/unit/domain/test_room.py test/unit/application/test_update_room_status_use_case.py test/unit/interfaces/test_app_bootstrap.py test/contract/test_patch_room_status.py`.
- [x] 4.2 Run `uv run pytest --cov=internal --cov-report=term-missing`.
- [x] 4.3 Run `uv run ruff check . && uv run black --check . && uv run pyright`.
