# Inventory Service Documentation

## 1. Responsibilities
The **Inventory Service** is responsible for managing the hotel's room inventory. Its primary duties include:
- **Room Management**: Registering new rooms and updating their operational status (e.g., available, maintenance, out of service).
- **Availability Search**: Providing an API to query available rooms based on check-in/check-out dates, room type, capacity, and price constraints.
- **Reservation Management**: Integrating with the Booking system via asynchronous events to reserve specific rooms when a booking is created, and releasing those rooms if the booking process fails.

This service follows Domain-Driven Design (DDD) principles, segregating the domain logic from infrastructure and interface layers.

## 2. API Endpoints
The REST API is built with FastAPI. For detailed interactive OpenAPI documentation, run the service and navigate to the `/docs` path in your browser.

- **`GET /health`**: Health check endpoint to verify the service is running.
- **`POST /rooms`**: Registers a new room with details such as room number, type, capacity, price, and initial availability dates.
- **`GET /rooms`**: Searches for available rooms within a specified date range. Supports query parameters for `room_type`, `max_price`, and `min_capacity`.
- **`PATCH /rooms/{room_id}/status`**: Updates the operational status of a specific room.

## 3. Asynchronous Messaging (RabbitMQ)
The service listens and responds to RabbitMQ events to coordinate with other services (like the Booking Service).

### Queues and Routing
- **Exchange**: `inventory.direct`
- **Request Queue**: `inventory.request.queue` (Listens to routing key `inventory.request`)
- **Response Queue**: `inventory.response.queue` (Sends to routing key `inventory.response.key`)

### Events Handled
The service runs an event consumer (`run_inventory_reservation_consumer.py`) that consumes `BookingCreatedMessage` events. Depending on the `eventType`, it takes different actions:
- `BOOKING_Ok`: Triggers the **Reserve Rooms** use case. It attempts to lock/reserve the requested rooms for the booking.
- `BOOKING_FAILED` / `BOOKING_FALED`: Triggers the **Release Rooms** use case. It releases previously reserved rooms back into the available inventory pool.

After processing, it publishes an `InventoryResponseMessage` back to the response queue.

## 4. Message Contracts

### Input: `BookingCreatedMessage`
Payload expected from the request queue:
```json
{
  "eventId": "uuid",
  "eventType": "BOOKING_Ok", 
  "timestamp": "2026-04-23T12:00:00Z",
  "bookingId": "uuid",
  "customerId": "uuid",
  "startDate": "2026-04-24",
  "endDate": "2026-04-26",
  "roomIds": ["uuid1", "uuid2"]
}
```
*(Note: `eventType` can also be `BOOKING_FAILED` or `BOOKING_FALED`)*

### Output: `InventoryResponseMessage`
Payload sent to the response queue:
```json
{
  "eventId": "uuid",
  "eventType": "BOOKING_Ok",
  "timestamp": "2026-04-23T12:00:05Z",
  "bookingId": "uuid",
  "status": "CONFIRMED",
  "reservationConfirmed": true,
  "failedRooms": [
    {
      "roomId": "uuid",
      "reason": "Already booked"
    }
  ]
}
```
*Note: If `reservationConfirmed` is `false`, the `status` will be `FAILED` and `failedRooms` will contain details about the unreserved rooms if any.*
