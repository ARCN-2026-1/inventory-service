# Proposal: search-rooms

## Intent

Implement a room search capability to allow users to find available rooms for a specific date range, optionally filtering by capacity, price, and room type. This addresses a core business requirement currently marked as out-of-scope.

## Scope

### In Scope
- Add `search` method to `RoomRepository` protocol and `SqlAlchemyRoomRepository`.
- Create a new application query `search_rooms_query` and corresponding use case.
- Implement REST endpoint `GET /rooms` with query parameters (`check_in`, `check_out`, `room_type`, `max_price`, `min_capacity`).
- Filter logic: must overlap with `RoomAvailability` window, have `booking_id IS NULL`, and `operational_status = AVAILABLE`.

### Out of Scope
- Multi-currency support (price filtering assumes a single base currency).
- Pagination or advanced sorting logic (defer to future iterations).

## Capabilities

### New Capabilities
- `room-search`: Querying and filtering available hotel rooms based on check-in/out dates, price, capacity, and type.

### Modified Capabilities
- `inventory-management`: Update spec to remove the explicit restriction on `SearchRooms` being out-of-scope.

## Approach

Purely additive change in the application layer. Add a `search` method to the repository interface that translates REST query parameters into a SQLAlchemy query against existing tables (`rooms`, `room_availability`). Create a dedicated read-model/query handler (`search_rooms_use_case.py`) to decouple from write-side aggregate logic.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `internal/domain/repositories/room_repository.py` | Modified | Add `search` method to protocol |
| `internal/infrastructure/persistence/sqlalchemy_room_repository.py` | Modified | Implement `search` method |
| `internal/application/queries/` | New | Add `search_rooms_query.py` and `search_rooms_use_case.py` |
| `internal/interfaces/rest/schemas.py` | Modified | Add Request/Response schemas for search |
| `internal/interfaces/rest/app.py` | Modified | Add `GET /rooms` endpoint |
| `openspec/specs/inventory-management/spec.md` | Modified | Lift `SearchRooms` out-of-scope restriction |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Currency mismatch on `max_price` | Low | Document that search assumes the default single-currency environment for now. |
| Missing `RoomAvailability` records | Low | Query logic will explicitly require an active, unbooked `RoomAvailability` record. |

## Rollback Plan

Revert the PR containing the new endpoint and query logic. Since there are no database migrations, this is a safe code-level rollback.

## Dependencies

- None

## Success Criteria

- [ ] `GET /rooms` returns a list of available rooms matching the date range.
- [ ] Rooms with a non-null `booking_id` in the overlapping date range are excluded.
- [ ] Rooms with `operational_status != AVAILABLE` are excluded.
- [ ] Optional filters (`room_type`, `max_price`, `min_capacity`) correctly narrow down results.