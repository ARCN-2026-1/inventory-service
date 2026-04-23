# Design: Search Rooms

## Technical Approach

Implement `GET /rooms` as a read flow that keeps the repo’s hexagonal split: REST parses query params, an application query use case validates the requested stay window, and `SqlAlchemyRoomRepository` executes a single filtered SQLAlchemy query over `rooms` + `room_availability`. This follows the proposal’s additive approach and the spec’s room search scope without introducing a separate read stack.

## Architecture Decisions

### Decision: Keep reads on the existing repository port

| Option | Tradeoff | Decision |
|---|---|---|
| Add `search(...)` to `RoomRepository` | Reuses existing port; returns full `Room` aggregates for a read use case | Yes |
| Create a dedicated query repository/read model | Cleaner CQRS split; more files and abstractions for a small service | No |

**Rationale**: The service is still small, the DB already contains every searchable column, and keeping one repository avoids unnecessary duplication while staying inside the bounded context.

### Decision: Validate stay window in application, filter in SQL

| Option | Tradeoff | Decision |
|---|---|---|
| Build `DateRange` in use case, run filters in SQLAlchemy | Preserves domain invariant and keeps query efficient | Yes |
| Load all rooms and filter in Python | Simpler code, poor scalability and wrong responsibility split | No |

**Rationale**: `DateRange` already enforces `check_out > check_in`, and SQL filtering avoids scanning non-matching rooms in memory.

## Data Flow

```text
Client
  -> GET /rooms?check_in&check_out&room_type&max_price&min_capacity
  -> FastAPI endpoint
  -> SearchRoomsUseCase.execute(SearchRoomsQuery)
  -> DateRange(check_in, check_out)
  -> RoomRepository.search(...)
  -> SQLAlchemy JOIN rooms + room_availability
  -> list[Room]
  -> map to RoomSummary response
  -> 200 OK
```

Repository query predicates:
- `room_availability.start_date <= check_in`
- `room_availability.end_date >= check_out`
- `room_availability.booking_id IS NULL`
- `rooms.operational_status = AVAILABLE`
- optional exact `room_type`, `price_amount <= max_price`, `capacity >= min_capacity`

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `internal/domain/repositories/room_repository.py` | Modify | Add `search(...)` port with domain-safe filter arguments. |
| `internal/application/queries/__init__.py` | Create | Package marker for read-side query objects/use cases. |
| `internal/application/queries/search_rooms_query.py` | Create | Immutable query DTO and response item DTOs. |
| `internal/application/queries/search_rooms_use_case.py` | Create | Build `DateRange`, call repository, map `Room` to summaries. |
| `internal/infrastructure/persistence/sqlalchemy_room_repository.py` | Modify | Implement the filtered SQLAlchemy search query with joined availability load. |
| `internal/interfaces/rest/schemas.py` | Modify | Add `SearchRoomsResponse` and `RoomSummary` response models. |
| `internal/interfaces/rest/app.py` | Modify | Add `GET /rooms` route while preserving existing `POST /rooms`. |
| `test/unit/application/test_search_rooms_use_case.py` | Create | Query validation and mapping coverage. |
| `test/integration/persistence/test_sqlalchemy_room_repository.py` | Modify | Prove SQL filters exclude booked, maintenance, and out-of-range rooms. |
| `test/contract/test_get_rooms.py` | Create | HTTP contract coverage for success and filter combinations. |
| `test/unit/interfaces/test_app_bootstrap.py` | Modify | Assert OpenAPI now exposes `GET /rooms` and `POST /rooms`. |

## Interfaces / Contracts

```python
@dataclass(frozen=True, slots=True)
class SearchRoomsQuery:
    check_in: date
    check_out: date
    room_type: str | None = None
    max_price: Decimal | None = None
    min_capacity: int | None = None

class RoomSummary(CamelCaseModel):
    room_id: str
    room_number: str
    room_type: str
    capacity: int
    price_amount: Decimal
    price_currency: str
```

REST contract:
- `GET /rooms` with required `check_in`, `check_out`
- optional `room_type`, `max_price`, `min_capacity`
- `200 OK` returns `list[RoomSummary]`
- invalid stay window (`check_out <= check_in`) returns `400` via `DomainRuleViolation`
- malformed scalar parsing stays on FastAPI default validation behavior

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `SearchRoomsUseCase` builds `DateRange`, forwards optional filters, maps domain rooms to response DTOs | Pure pytest with in-memory repository stub in `test/unit/application/`. |
| Integration | Repository SQL query semantics for overlap, booking exclusion, operational status, `max_price`, `min_capacity`, and `room_type` filters | Extend MySQL testcontainers coverage in `test/integration/persistence/`. |
| Contract | `GET /rooms` response shape, status code, and query parameter behavior | FastAPI `TestClient` tests in `test/contract/` using stub repository. |
| E2E | None | `openspec/config.yaml` marks e2e unavailable. |

## Migration / Rollout

No migration required. The change is additive and uses existing `rooms` and `room_availability` columns.

## Open Questions

None.
