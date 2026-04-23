# Proposal: update-room-status

## Intent

Allow operators to change a room’s operational status after registration so the inventory service can represent maintenance and out-of-service transitions without recreating the room.

## Scope

### In Scope
- Add `Room.update_operational_status(...)` and `RoomStatusChanged` domain event.
- Add `UpdateRoomStatusCommand` and `UpdateRoomStatusUseCase`.
- Add `PATCH /rooms/{room_id}/status` with `operational_status` request body.
- Map missing-room failures to `404` and invalid status values to `400`.

### Out of Scope
- Authentication/authorization for the endpoint.
- Optimistic locking or concurrent status conflict handling.
- RabbitMQ publishing for status-change events.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `inventory-management`: room operational status transitions become supported via `PATCH /rooms/{room_id}/status`.

## Approach

Add a slim aggregate mutation method and reuse `repository.save(room)` so the write model stays consistent with reserve/release flows. Validate the incoming status in the use case, raise `DomainRuleViolation` for invalid values, and return `204 No Content` on success.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `internal/domain/events/room_events.py` | Modified | Add `RoomStatusChanged`. |
| `internal/domain/entities/room.py` | Modified | Add operational-status transition method. |
| `internal/application/commands/update_room_status.py` | New | Command DTO for room/status updates. |
| `internal/application/usecases/update_room_status.py` | New | Load, validate, mutate, and save room status. |
| `internal/interfaces/rest/schemas.py` | Modified | Add request model for status updates. |
| `internal/interfaces/rest/app.py` | Modified | Add endpoint and `RoomNotFoundError` → `404` mapping. |
| `test/unit/domain/test_room.py` | Modified | Cover status transitions and event payloads. |
| `test/unit/application/test_update_room_status_use_case.py` | New | Cover success, invalid value, and missing-room paths. |
| `test/contract/test_patch_room_status.py` | New | Cover HTTP contract and response codes. |
| `test/unit/interfaces/test_app_bootstrap.py` | Modified | Assert new route appears in OpenAPI. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Event captures the wrong previous status | Medium | Snapshot old status before mutating the aggregate field. |
| Missing-room responses return the wrong HTTP code | Medium | Explicitly map `RoomNotFoundError` to `404` in REST error handling. |
| Endpoint becomes too permissive | Low | Keep validation inside the use case and reuse the existing enum type. |

## Rollback Plan

Revert the endpoint, command/use case, domain mutation, event, and spec delta in a single PR rollback. No migration is required.

## Dependencies

- None

## Success Criteria

- [ ] `PATCH /rooms/{room_id}/status` returns `204` for a valid transition.
- [ ] Invalid status values return `400`.
- [ ] Unknown room IDs return `404`.
- [ ] Repeating the same status is idempotent.
