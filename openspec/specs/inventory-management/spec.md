# Inventory Management Specification

## Purpose
Core lifecycle and registry of physical rooms, their operational status, and base pricing. This specification covers the foundational domain slice for registering new rooms in the hotel, including the initial `Room` aggregate.

## Requirements

### Requirement: Service Health Check
The system MUST provide a health check endpoint to verify service operational status.

#### Scenario: Verify service health
- GIVEN the inventory service is running
- WHEN a client requests the health status via `GET /health`
- THEN the system MUST return a 200 OK status

### Requirement: Register Room
The system MUST allow registering a new physical room with its base configuration and pricing. Authentication MUST NOT be required for this operation in the initial implementation.

#### Scenario: Successfully register a new room
- GIVEN a valid room configuration (valid `RoomType`, `RoomOperationalStatus`, and `Money` amount > 0)
- WHEN a client submits the room details via `POST /rooms`
- THEN the system MUST create the new room in the registry
- AND the system MUST return the generated room ID with a 201 Created status

#### Scenario: Reject registration with invalid price
- GIVEN a room configuration with a negative or zero base price
- WHEN a client submits the room details via `POST /rooms`
- THEN the system MUST reject the registration
- AND the system MUST return a 400 Bad Request error indicating invalid price

#### Scenario: Reject registration with invalid date range
- GIVEN a room configuration where the availability date range is invalid (e.g., end date is before start date)
- WHEN a client submits the room details via `POST /rooms`
- THEN the system MUST reject the registration
- AND the system MUST return a 400 Bad Request error indicating invalid dates

### Requirement: Search Rooms
The system MUST allow searching available rooms for a requested stay window through `GET /rooms`. The search SHALL require `check_in` and `check_out`, and MAY accept `room_type`, `max_price`, and `min_capacity` filters.

#### Scenario: Search available rooms for a valid stay window
- GIVEN rooms exist with availability ranges covering the requested stay window
- WHEN a client requests `GET /rooms` with valid `check_in` and `check_out`
- THEN the system MUST return a 200 OK response
- AND the system MUST include only rooms whose availability contains the requested window

#### Scenario: Exclude unavailable rooms from search results
- GIVEN some rooms are booked, under maintenance, or do not cover the requested stay window
- WHEN a client requests `GET /rooms` for that stay window
- THEN the system MUST exclude rooms with non-null `booking_id`
- AND the system MUST exclude rooms whose `operational_status` is not `AVAILABLE`
- AND the system MUST exclude rooms whose availability does not contain the requested stay window

#### Scenario: Apply optional room filters during search
- GIVEN multiple available rooms exist for the requested stay window
- WHEN a client requests `GET /rooms` with any combination of `room_type`, `max_price`, and `min_capacity`
- THEN the system MUST return only rooms matching every provided filter

#### Scenario: Reject invalid stay windows during search
- GIVEN a client provides a stay window where `check_out` is not after `check_in`
- WHEN the client requests `GET /rooms`
- THEN the system MUST reject the request
- AND the system MUST return a 400 Bad Request response indicating invalid dates

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

### Requirement: Out of Scope Items (Explicit)
The system MUST NOT require authentication or authorization for any endpoints in this initial version.
