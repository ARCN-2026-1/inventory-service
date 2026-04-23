# booking-messaging Specification

## Purpose

Handles asynchronous communication with the `booking-service` via RabbitMQ to process distributed saga events for room reservations and releases.

## Requirements

### Requirement: Handle Booking Events

The system MUST listen to the `inventory.request.queue` on a direct exchange for `BookingCreatedEvent` messages.

#### Scenario: Successful reservation

- GIVEN an available room
- WHEN a `BookingCreatedEvent` with status `BOOKING_Ok` is received for that room
- THEN the system MUST mark the room as reserved with the `booking_id`
- AND publish an `InventoryResponse` with `reservationConfirmed=true`

#### Scenario: Insufficient inventory

- GIVEN a room that is already reserved or does not exist
- WHEN a `BookingCreatedEvent` with status `BOOKING_Ok` is received for that room
- THEN the system MUST NOT reserve the room
- AND publish an `InventoryResponse` with `reservationConfirmed=false`

#### Scenario: Booking failed notification

- GIVEN a previously reserved room for a booking
- WHEN a `BookingCreatedEvent` with status `BOOKING_FALED` is received
- THEN the system MUST release the room by clearing its `booking_id`
- AND publish an `InventoryResponse` with `reservationConfirmed=false`

### Requirement: Error Handling

The system MUST handle messaging and processing errors to prevent message loss.

#### Scenario: Transient errors

- GIVEN a connection issue or transient database error
- WHEN processing a `BookingCreatedEvent`
- THEN the system MUST NOT acknowledge (nack) the message to allow requeuing

#### Scenario: Invalid message format

- GIVEN a malformed payload or missing fields
- WHEN reading from the queue
- THEN the system SHOULD dead-letter or safely discard the message without crashing
