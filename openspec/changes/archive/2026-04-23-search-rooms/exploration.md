# Exploration: search-rooms

## Current State

The service already has the foundational domain model fully in place:

- **`Room` aggregate** (`internal/domain/entities/room.py`): holds `room_type` (RoomType enum: STANDARD/DELUXE/SUITE), `capacity` (int), `base_price` (Money: amount+currency), `operational_status` (RoomOperationalStatus), and an optional `RoomAvailability` with a `DateRange(start_date, end_date)` and a nullable `booking_id`.
- **`RoomAvailability`** (`internal/domain/entities/room_availability.py`): frozen dataclass. `booking_id is None` ⇒ free; `booking_id is not None` ⇒ reserved.
- **`DateRange`** (`internal/domain/valueobjects/date_range.py`): enforces `end_date > start_date`.
- **`RoomRepository` protocol** (`internal/domain/repositories/room_repository.py`): currently exposes `add`, `get_by_room_number`, `get_by_id`, `save`. **No search/query method exists.**
- **`SqlAlchemyRoomRepository`** (`internal/infrastructure/persistence/sqlalchemy_room_repository.py`): uses SQLAlchemy ORM with `joinedload` on `RoomAvailabilityModel`. No filtering query implemented.
- **DB schema**: `rooms` table has `room_type`, `capacity`, `price_amount`, `price_currency`, `operational_status`. `room_availability` table has `start_date`, `end_date`, `booking_id`. All columns needed for the filters are already present in the DB.
- **REST layer** (`internal/interfaces/rest/app.py`): only exposes `POST /rooms` and `GET /health`.
- **Main spec** (`openspec/specs/inventory-management/spec.md`): explicitly marks `SearchRooms` as **out-of-scope** — meaning this change lifts that restriction.

The existing application layer commands/use-cases cover `RegisterRoom`, `ReserveRooms`, `ReleaseRooms`. There is **no query/use-case for searching rooms**.

---

## Minimum Safe Contract

The `SearchRooms` query must accept:
| Parameter | Type | Required | Semantics |
|---|---|---|---|
| `check_in` | `date` | ✅ | availability window start (inclusive) |
| `check_out` | `date` | ✅ | availability window end (inclusive); must be > check_in |
| `room_type` | `RoomType` enum | ❌ | exact match filter |
| `max_price` | `Decimal` | ❌ | `base_price.amount ≤ max_price` |
| `min_capacity` | `int` | ❌ | `capacity ≥ min_capacity` |

Response per room:
```json
{
  "roomId": "uuid",
  "roomNumber": "101",
  "roomType": "STANDARD",
  "capacity": 2,
  "priceAmount": "100.00",
  "priceCurrency": "USD"
}
```

**Availability semantics**: a room is "available for the requested window" if:
1. It has a `RoomAvailability` record whose `DateRange` **contains** the requested window (`start_date ≤ check_in AND end_date ≥ check_out`).
2. Its `booking_id` is `NULL` (not currently reserved).
3. Its `operational_status` is `AVAILABLE`.

---

## Affected Areas

- `internal/domain/repositories/room_repository.py` — must add `search` method to the `Protocol`
- `internal/application/queries/` — **new folder**: `search_rooms_query.py` (query DTO), `search_rooms_use_case.py`
- `internal/infrastructure/persistence/sqlalchemy_room_repository.py` — implement `search` with SQLAlchemy filter chain
- `internal/interfaces/rest/schemas.py` — add `SearchRoomsRequest` (query params) and `RoomSummary` / `SearchRoomsResponse`
- `internal/interfaces/rest/app.py` — add `GET /rooms` endpoint
- `openspec/specs/inventory-management/spec.md` — lift the explicit "SearchRooms out of scope" restriction

---

## Approaches

### 1. Query method on existing `RoomRepository` (recommended)
Add `search(query: SearchRoomsQuery) -> list[Room]` to the `RoomRepository` protocol and implement it in `SqlAlchemyRoomRepository`.

- **Pros**: consistent with existing pattern; no new infrastructure dependency; all needed columns are already in the DB; easy to unit-test via in-memory stub.
- **Cons**: `Room` aggregate is returned even though only read data is needed — minor overhead.
- **Effort**: Low

### 2. Dedicated `ReadModel` / separate query repository
Create a separate `RoomReadModel` dataclass and a `RoomQueryRepository` protocol returning flat DTOs, bypassing the domain aggregate.

- **Pros**: CQRS-clean; lighter reads (no `availability` join needed once we flatten); decouples read/write paths.
- **Cons**: Doubles the repository abstraction for a service this small; over-engineering at this stage.
- **Effort**: Medium

### 3. In-memory domain filtering (load all, filter in Python)
Load all rooms and filter in application layer.

- **Pros**: Zero infra change.
- **Cons**: Completely unscalable; N+1 on availability join; unacceptable for production.
- **Effort**: Low (but wrong)

---

## Recommendation

**Approach 1**: add `search` to `RoomRepository` protocol + implement in `SqlAlchemyRoomRepository`.

The DB already has every column needed for the filter. The query is a simple `JOIN rooms LEFT JOIN room_availability ON ... WHERE booking_id IS NULL AND start_date <= :check_in AND end_date >= :check_out AND ...`. Returning `list[Room]` is fine — the use-case maps it to a response DTO before returning, which is consistent with the existing pattern in `RegisterRoomUseCase`.

The application layer should live in `internal/application/queries/` to clearly separate read from write, even within the same repository abstraction.

---

## Risks

- **Currency mismatch on `max_price`**: rooms can theoretically be in different currencies. The filter should be documented as operating only on `price_amount`, assuming a single-currency environment (safe for now; can be made explicit in spec).
- **`operational_status` scope**: the filter should only return rooms with `operational_status = AVAILABLE`. If `MAINTENANCE` or other statuses are introduced, this needs updating.
- **Rooms without `RoomAvailability`**: rooms registered without an availability window will never appear in search results. This is correct behaviour — they are not bookable — but must be documented in the spec.
- **Spec must be updated**: the main spec currently explicitly bans `SearchRooms`. The change must update `openspec/specs/inventory-management/spec.md`.

---

## Ready for Proposal

**Yes.** The domain model and DB schema are already complete. The change is purely additive: one new query method on the repository, one new application query use-case, and one new REST endpoint `GET /rooms`. No migration is needed, no existing behavior is modified.
