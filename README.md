# inventory-service

Bootstrap inventory service for hotel-ddd with FastAPI, SQLAlchemy, MySQL, and Alembic.

## Documentation

For a comprehensive overview of the service's responsibilities, event-driven architecture, API endpoints, and message contracts, please see the [Service Overview](docs/service_overview.md).

## Local setup

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Configure environment variables from `.env.example`.

3. Run migrations:

   ```bash
   uv run alembic upgrade head
   ```

4. Start the API locally:

   ```bash
   uv run fastapi dev main.py
   ```

## Available endpoints

- `GET /health`
- `POST /rooms`
