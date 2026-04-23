# Proposal: Bootstrap Inventory Service

## Intent

Establish the base skeleton and initial domain capabilities for the `inventory-service`. This change introduces the necessary project structure mirroring `customer-service`, sets up the persistence layer with MySQL/Alembic, and delivers the first business capability: registering new rooms in the hotel. 

## Scope

### In Scope
- Project skeleton (FastAPI, SQLAlchemy, Alembic, Docker, pyproject.toml) mirroring the canonical structure.
- Core Domain Model: `Room` aggregate, `RoomAvailability` entity, and Value Objects (`RoomType`, `RoomOperationalStatus`, `Money`, `DateRange`).
- Use Case: `RegisterRoomUseCase` with its corresponding command.
- Persistence: `SqlAlchemyRoomRepository` and initial database migration for `rooms` and `room_availability` tables.
- REST API: `POST /rooms` endpoint (without authentication per confirmed decision) and `GET /health`.

### Out of Scope
- Authentication/Authorization (explicitly deferred, starting without auth).
- `SearchRooms` REST query.
- RabbitMQ integration (`BlockRoomAvailability`, `ReleaseRoomAvailability`).
- `UpdateRoomStatus` endpoint.

## Capabilities

### New Capabilities
- `inventory-management`: Core lifecycle and registry of physical rooms, their operational status, and base pricing.

### Modified Capabilities
- None

## Approach

We will implement a layered bootstrap following the hexagonal architecture pattern present in `customer-service`. We will focus only on the foundational domain slice (`RegisterRoom`) and project skeleton to ensure the base plumbing (FastAPI, dependency injection, SQLAlchemy, database connectivity) is solid and testable before adding complex RabbitMQ integrations and complex queries. The `Money` and `DateRange` value objects will be implemented to enforce domain invariants (like `start_date < end_date` and `amount > 0`).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `/` | New | Complete project structure and configuration files |
| `internal/domain/` | New | Core domain aggregate `Room` and related entities |
| `internal/application/` | New | `RegisterRoom` use case |
| `internal/infrastructure/` | New | MySQL DB setup, Alembic migrations, `SqlAlchemyRoomRepository` |
| `internal/interfaces/rest/` | New | `POST /rooms` endpoint |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Incomplete invariants in Value Objects | Medium | Implement comprehensive unit testing for `Money` and `DateRange` value objects covering edge cases. |
| Database schema conflicts with other services | Low | Ensure Alembic migrations are scoped strictly to the `inventory_service` schema and user. |

## Rollback Plan

Revert the PR containing the project bootstrap and drop the `inventory_service` database schema if already applied to the shared MySQL instance.

## Dependencies

- Shared MySQL instance must be provisioned with an `inventory` user and `inventory_service` schema.

## Success Criteria

- [ ] Project builds and runs via Docker (`docker-compose up`).
- [ ] `GET /health` returns 200 OK.
- [ ] `POST /rooms` successfully creates a room in the MySQL database without requiring auth.
- [ ] Unit tests for the `Room` aggregate and value objects pass.
