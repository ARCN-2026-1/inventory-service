# Exploration: update-room-status

## Current State

The `Room` aggregate (`internal/domain/entities/room.py`) already carries an
`operational_status: RoomOperationalStatus` field (StrEnum: `AVAILABLE`,
`MAINTENANCE`, `OUT_OF_SERVICE`).  The field is set at registration time via
`Room.register()` and is persisted by `SqlAlchemyRoomRepository.save()` through
the existing `rooms.operational_status` column.

What is **absent today**:
- No aggregate method to mutate `operational_status` after registration.
- No `RoomStatusChanged` domain event class.
- No `UpdateRoomStatusCommand` or `UpdateRoomStatusUseCase`.
- No REST endpoint for the admin transition.
- No new application-layer error for "room not found" in this flow (although
  `RoomNotFoundError` already exists in `application/errors.py`).

The `search` query already filters on `operational_status == AVAILABLE`, so any
status change is immediately reflected in search results without extra work.

---

## Minimum Safe Contract

### Command
```python
@dataclass(frozen=True, slots=True)
class UpdateRoomStatusCommand:
    room_id: UUID
    new_status: str       # validated to RoomOperationalStatus in use-case
    changed_at: datetime  # UTC, injected by use-case or caller
```

### Domain method (on `Room`)
```python
def update_operational_status(
    self,
    *,
    new_status: RoomOperationalStatus,
    changed_at: datetime,
) -> None:
    if new_status == self.operational_status:
        return   # idempotent — no event, no error
    self.operational_status = new_status
    self._record_event(RoomStatusChanged(
        room_id=self.room_id,
        old_status=self.operational_status,   # capture before mutation
        new_status=new_status,
        changed_at=changed_at,
    ))
```

> **Important**: capture `old_status` BEFORE mutating, otherwise the event
> carries the wrong value.

### Domain event
```python
@dataclass(frozen=True, slots=True)
class RoomStatusChanged:
    room_id: UUID
    old_status: RoomOperationalStatus
    new_status: RoomOperationalStatus
    changed_at: datetime
```

### Use-case
- Load room by `room_id` → raise `RoomNotFoundError` if absent.
- Delegate `room.update_operational_status(...)`.
- Persist via `repository.save(room)`.
- Return nothing (204 response pattern).

### REST endpoint
```
PATCH /rooms/{room_id}/status
Body: { "operational_status": "MAINTENANCE" }
Response: 204 No Content
Errors: 400 (invalid status value), 404 (room not found)
```

---

## Domain Rules

| Rule | Behaviour |
|------|-----------|
| Same-status transition | Idempotent — no event, no persistence write needed |
| Invalid status value | `RoomOperationalStatus(value)` raises `ValueError`; use-case catches and re-raises as `DomainRuleViolation` |
| Room not found | `RoomNotFoundError` (already in `application/errors.py`) |
| Reserved room → MAINTENANCE | **Allowed** — status and availability are orthogonal concepts; a room can be under maintenance while a booking still exists |
| Concurrency | No optimistic-lock mechanism exists yet; out of scope for this change |

---

## Affected Areas

| Path | Why |
|------|-----|
| `internal/domain/events/room_events.py` | Add `RoomStatusChanged` event dataclass |
| `internal/domain/entities/room.py` | Add `update_operational_status()` method |
| `internal/application/commands/` | New `update_room_status.py` command |
| `internal/application/usecases/` | New `update_room_status.py` use-case |
| `internal/interfaces/rest/schemas.py` | New `UpdateRoomStatusRequest` Pydantic model |
| `internal/interfaces/rest/app.py` | New `PATCH /rooms/{room_id}/status` endpoint |
| `test/unit/domain/test_room.py` | Unit tests for `update_operational_status` |
| `test/unit/application/` | New `test_update_room_status_use_case.py` |
| `test/contract/` | New contract test for `PATCH /rooms/{room_id}/status` |

**No schema migration required** — `rooms.operational_status` column already
exists and `repository.save()` already persists it.

---

## Approaches

### 1. Aggregate method + use-case (recommended)
Add a slim domain method and a focused use-case; no new repository method needed
because `save()` already handles full-aggregate persistence.

- **Pros**: consistent with existing `reserve`/`release` pattern; minimal
  surface area; `save()` reuse avoids drift between methods.
- **Cons**: `save()` does a full-row overwrite (no partial update); acceptable
  for this scale.
- **Effort**: Low

### 2. Direct repository update (skip aggregate method)
Add `update_status(room_id, new_status)` to the repository Protocol and
implement it as a SQL `UPDATE rooms SET operational_status = ? WHERE room_id = ?`.

- **Pros**: more efficient DB query.
- **Cons**: bypasses the aggregate; domain events never fire; breaks DDD
  integrity; violates architecture boundaries skill.
- **Effort**: Low (but wrong)

---

## Recommendation

**Approach 1** — aggregate method + use-case, reusing `repository.save()`.

Rationale:
- Mirrors the `reserve`/`release` precedent already established in this
  codebase.
- Fires `RoomStatusChanged`, enabling future event-driven consumers (e.g.
  notifying booking-service if a reserved room goes OUT_OF_SERVICE).
- Zero migration risk.
- Idempotency is naturally expressed in the aggregate.

---

## Risks

- **`old_status` capture order**: must snapshot the current status before
  mutating the field (slots=True dataclass fields are mutable, so forgetting
  this is a silent bug).
- **slots=True constraint**: `Room` uses `@dataclass(slots=True)`, so we cannot
  add new attributes dynamically; this is fine because `update_operational_status`
  only mutates existing `operational_status` and appends to `_domain_events`.
- **No auth guard**: the endpoint is admin-only by intent (DDD source of truth);
  this change defers auth (as established by bootstrap convention). Document in
  spec.
- **Event publishing**: `RoomStatusChanged` is recorded in the aggregate but
  not published to RabbitMQ in this change. If needed later, it follows the
  same pattern as `inventory-booking-messaging`.

---

## Ready for Proposal

**Yes.**

The scope is clear: one aggregate method, one event, one command, one use-case,
one endpoint, and three test files. No migration. No auth. No messaging in this
slice.
