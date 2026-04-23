# Search Rooms Specification

## Purpose
Defines the route contract, filter semantics, and out-of-scope assumptions for the `search-rooms` capability in the `inventory-service`.

## Route Contract
### Requirement: Expose GET /rooms Endpoint
The system MUST provide a `GET /rooms` endpoint to search for available rooms.

#### Scenario: Basic Search Request
- GIVEN the `GET /rooms` endpoint is active
- WHEN a client sends a request without filters
- THEN the system MUST return a 200 OK response with a list of all available rooms

#### Scenario: Filtered Search Request
- GIVEN the `GET /rooms` endpoint is active
- WHEN a client sends a request with valid query parameters (e.g., `?room_type=SUITE`)
- THEN the system MUST return a 200 OK response with a list of rooms matching the filters

## Filter Semantics
### Requirement: Support Core Filters
The system SHALL support filtering rooms by `room_type`, `min_capacity`, and `max_price`.

#### Scenario: Maximum Price Filter
- GIVEN multiple rooms exist with varying prices
- WHEN a search request includes `?max_price=200`
- THEN the system MUST return only rooms priced at 200 or less

#### Scenario: Minimum Capacity Filter
- GIVEN multiple rooms exist with varying capacities
- WHEN a search request includes `?min_capacity=2`
- THEN the system MUST return only rooms with a capacity of 2 or more

## Out-of-Scope Assumptions
### Requirement: Ignore Unavailable Rooms
The system SHALL NOT return rooms that are currently booked or under maintenance.

#### Scenario: Excluding Booked Rooms
- GIVEN a room is marked as booked for the current date
- WHEN a client searches for rooms
- THEN the system MUST omit the booked room from the results

### Requirement: Ignore Advanced Booking Logic
The search endpoint SHALL NOT handle booking transactions or complex availability checks beyond basic status filtering.

#### Scenario: Out of Scope Verification
- GIVEN a client attempts to book via the search endpoint
- WHEN the request is received
- THEN the system MUST reject it or ignore the booking parameters, returning only search results
