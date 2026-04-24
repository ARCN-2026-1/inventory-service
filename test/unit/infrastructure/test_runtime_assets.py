from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_env_example_documents_inventory_database_vars() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "MYSQL_DATABASE=inventory_service" in env_example
    assert "MYSQL_USER=inventory_app" in env_example
    assert "MYSQL_PASSWORD=change-me" in env_example
    assert "MYSQL_LOCAL_PORT=3306" in env_example
    assert "MYSQL_ROOT_PASSWORD=change-me-root" in env_example
    assert "RABBITMQ_HOST=localhost" in env_example
    assert "RABBITMQ_DEFAULT_USER=guest" in env_example
    assert "RABBITMQ_DEFAULT_PASS=guest" in env_example
    assert "RABBITMQ_PORT=5672" in env_example
    assert "INVENTORY_SERVICE_PORT=8000" in env_example
    assert "INVENTORY_SERVICE_RABBITMQ_EXCHANGE=inventory.direct" in env_example
    assert (
        "INVENTORY_SERVICE_RABBITMQ_REQUEST_QUEUE=inventory.request.queue"
        in env_example
    )
    assert (
        "INVENTORY_SERVICE_RABBITMQ_RESPONSE_QUEUE=inventory.response.queue"
        in env_example
    )


def test_compose_base_is_runtime_only_without_local_infra_services() -> None:
    compose_base = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "inventory-migration:" in compose_base
    assert "inventory-api:" in compose_base
    assert "inventory-worker:" in compose_base
    assert "mysql:" not in compose_base
    assert "rabbitmq:" not in compose_base
    assert "${MYSQL_HOST:?set MYSQL_HOST}" in compose_base
    assert "${RABBITMQ_HOST:?set RABBITMQ_HOST}" in compose_base


def test_compose_dev_overlay_includes_local_mysql_and_rabbitmq() -> None:
    compose_dev = (PROJECT_ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")

    assert "inventory-migration:" in compose_dev
    assert "inventory-api:" in compose_dev
    assert "inventory-worker:" in compose_dev
    assert "mysql:" in compose_dev
    assert "rabbitmq:" in compose_dev
    assert "MYSQL_HOST: mysql" in compose_dev
    assert "RABBITMQ_HOST: rabbitmq" in compose_dev


def test_env_local_and_deploy_files_document_distinct_runtime_contracts() -> None:
    env_local = (PROJECT_ROOT / ".env.local").read_text(encoding="utf-8")
    env_deploy = (PROJECT_ROOT / ".env.deploy").read_text(encoding="utf-8")

    assert "MYSQL_HOST=mysql" in env_local
    assert "RABBITMQ_HOST=rabbitmq" in env_local
    assert "INVENTORY_SERVICE_PORT=8000" in env_local
    assert "INVENTORY_SERVICE_RABBITMQ_EXCHANGE=inventory.direct" in env_local

    assert "MYSQL_HOST=" in env_deploy
    assert "RABBITMQ_HOST=" in env_deploy
    assert "INVENTORY_SERVICE_PORT=" in env_deploy
    assert "INVENTORY_SERVICE_RABBITMQ_EXCHANGE=inventory.direct" in env_deploy


def test_readme_includes_bootstrap_startup_steps() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "uv sync" in readme
    assert "docker compose --env-file .env.deploy -f docker-compose.yml up -d" in readme
    assert (
        "docker compose --env-file .env.local -f docker-compose.yml "
        "-f docker-compose.dev.yml up -d" in readme
    )
