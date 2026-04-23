# Design: Update Room Status

## Technical Approach

Add a single aggregate mutation for operational status and reuse the existing repository `save()` path. The use case loads the room, validates the requested status, applies the change, and the REST layer returns `204` on success.

## Architecture Decisions

### Decision: Mutate the aggregate instead of adding a repository update method

| Option | Tradeoff | Decision |
|---|---|---|
| Add `update_status(...)` to the repository | Smaller SQL update, but bypasses domain behavior | No |
| Add `Room.update_operational_status(...)` and reuse `save()` | Keeps invariants and domain events inside the aggregate | Yes |

**Rationale**: This matches the existing reserve/release pattern and keeps status transitions as a domain concern.

### Decision: Emit a dedicated `RoomStatusChanged` event

| Option | Tradeoff | Decision |
|---|---|---|
| Mutate status without an event | Simpler now, but loses change history | No |
| Record `RoomStatusChanged` | Enables future consumers and keeps the aggregate consistent | Yes |

**Rationale**: The service already records domain events on state changes; status transitions should follow the same pattern.

### Decision: Map room-not-found to 404 in REST

| Option | Tradeoff | Decision |
|---|---|---|
| Reuse generic application error mapping | Simpler, but returns the wrong HTTP semantics | No |
| Explicitly map `RoomNotFoundError` to `404` | Correct API behavior for missing resources | Yes |

## Data Flow

```text
PATCH /rooms/{room_id}/status
  -> FastAPI endpoint
  -> UpdateRoomStatusUseCase.execute(...)
  -> repository.get_by_id(room_id)
  -> room.update_operational_status(...)
  -> repository.save(room)
  -> 204 No Content
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `internal/domain/events/room_events.py` | Modify | Add `RoomStatusChanged`. |
| `internal/domain/entities/room.py` | Modify | Add `update_operational_status(...)`. |
| `internal/application/commands/update_room_status.py` | Create | Command DTO. |
| `internal/application/usecases/update_room_status.py` | Create | Load, validate, mutate, save. |
| `internal/interfaces/rest/schemas.py` | Modify | Add request model. |
| `internal/interfaces/rest/app.py` | Modify | Add route and 404 mapping. |
| `test/unit/domain/test_room.py` | Modify | Add transition/event/idempotency tests. |
| `test/unit/application/test_update_room_status_use_case.py` | Create | Add use-case tests. |
| `test/contract/test_patch_room_status.py` | Create | Add HTTP contract tests. |
| `test/unit/interfaces/test_app_bootstrap.py` | Modify | Expose new route in OpenAPI. |

## Interfaces / Contracts

```python
@dataclass(frozen=True, slots=True)
class UpdateRoomStatusCommand:
    room_id: UUID
    new_status: str
    changed_at: datetime
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Domain transition and event payload | Extend `test/unit/domain/test_room.py`. |
| Unit | Use-case success, invalid status, missing room | New use-case tests with stubs. |
| Contract | `PATCH /rooms/{room_id}/status` response codes | FastAPI `TestClient` tests. |
| Unit | OpenAPI route exposure | Update bootstrap assertions. |

## Migration / Rollout

No migration required.

## Open Questions

- [ ] None.
