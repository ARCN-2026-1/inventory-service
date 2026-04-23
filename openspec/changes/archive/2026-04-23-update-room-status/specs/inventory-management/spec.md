# Delta for inventory-management

## ADDED Requirements

### Requirement: Update Room Operational Status

The system MUST allow updating a room's operational status through `PATCH /rooms/{room_id}/status`. The request SHALL accept an `operational_status` value and the system MUST return `204 No Content` on success.

#### Scenario: Successfully update room status

- GIVEN an existing room
- WHEN a client sends `PATCH /rooms/{room_id}/status` with a valid `operational_status`
- THEN the system MUST update the room's operational status
- AND the system MUST return `204 No Content`

#### Scenario: Reject an invalid status value

- GIVEN a client sends a status value that is not part of the room status enum
- WHEN the client requests `PATCH /rooms/{room_id}/status`
- THEN the system MUST reject the request
- AND the system MUST return `400 Bad Request`

#### Scenario: Reject updates for an unknown room

- GIVEN a room ID that does not exist
- WHEN a client requests `PATCH /rooms/{room_id}/status`
- THEN the system MUST return `404 Not Found`

#### Scenario: Treat same-status updates as idempotent

- GIVEN the room already has the requested operational status
- WHEN a client requests `PATCH /rooms/{room_id}/status`
- THEN the system MUST return `204 No Content`
- AND the system MUST NOT create a duplicate state change

## MODIFIED Requirements

### Requirement: Out of Scope Items (Explicit)

The system MUST NOT require authentication or authorization for any endpoints in this initial version.
The system MUST NOT support searching rooms (`SearchRooms` query).
(Previously: The system MUST NOT support updating a room's operational status.)
