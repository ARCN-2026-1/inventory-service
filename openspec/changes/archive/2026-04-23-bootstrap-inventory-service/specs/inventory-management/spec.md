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

### Requirement: Out of Scope Items (Explicit)
The system MUST NOT require authentication or authorization for any endpoints in this initial version.
The system MUST NOT support searching rooms (`SearchRooms` query).
The system MUST NOT integrate with RabbitMQ for availability blocking or releasing.
The system MUST NOT support updating a room's operational status.
