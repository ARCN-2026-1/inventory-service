# inventory-service

Inventory bounded context for hotel-ddd using FastAPI, SQLAlchemy, MySQL and RabbitMQ.

## Documentation

- [Service Overview](docs/service_overview.md)

## Structure

- `docker-compose.yml` — deploy/runtime base (`inventory-migration`, `inventory-api`, `inventory-worker`)
- `docker-compose.dev.yml` — local overlay with MySQL + RabbitMQ
- `.env.local` — local dev profile for compose base + dev overlay
- `.env.deploy` — deploy profile for external infra
- `.env.example` — safe template for both profiles

## Local setup (without Docker)

```bash
uv sync
uv run alembic upgrade head
uv run fastapi dev main.py
```

## Docker convention

### Deploy / runtime base (external infra)

`docker-compose.yml` is runtime-oriented and does **not** provision local MySQL/RabbitMQ.

Run with deploy env profile:

```bash
docker compose --env-file .env.deploy -f docker-compose.yml up -d
```

### Local development (runtime + local infra)

Use compose layering:

- `docker-compose.yml` (runtime services)
- `docker-compose.dev.yml` (mysql/rabbitmq + local overrides)

Start:

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Stop:

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml down
```

## Runtime env contract

Runtime services (`inventory-migration`, `inventory-api`, `inventory-worker`) resolve these vars explicitly:

- MySQL: `MYSQL_HOST`, `MYSQL_LOCAL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`
- RabbitMQ connection: `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS`
- Optional URLs: `INVENTORY_SERVICE_DATABASE_URL`, `INVENTORY_SERVICE_RABBITMQ_URL`
- RabbitMQ topology contract:
  - `INVENTORY_SERVICE_RABBITMQ_EXCHANGE`
  - `INVENTORY_SERVICE_RABBITMQ_REQUEST_QUEUE`
  - `INVENTORY_SERVICE_RABBITMQ_RESPONSE_QUEUE`
  - `INVENTORY_SERVICE_RABBITMQ_REQUEST_ROUTING_KEY`
  - `INVENTORY_SERVICE_RABBITMQ_RESPONSE_ROUTING_KEY`

## Available endpoints

- `GET /health`
- `POST /rooms`
