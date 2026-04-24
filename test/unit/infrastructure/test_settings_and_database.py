from pathlib import Path

import pytest

from alembic.config import Config
from internal.infrastructure.config.settings import (
    ALEMBIC_INI_DEFAULT_DATABASE_URL,
    InventoryServiceSettings,
    resolve_alembic_database_url,
)
from internal.infrastructure.persistence.database import create_session_factory

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_settings_expose_mysql_default_database_url() -> None:
    settings = InventoryServiceSettings()

    assert (
        settings.database_url
        == "mysql+pymysql://inventory:secret@localhost:3306/inventory_service?charset=utf8mb4"
    )


def test_settings_map_mysql_env_vars_into_database_url(monkeypatch) -> None:
    monkeypatch.setenv("MYSQL_DATABASE", "lexis_db")
    monkeypatch.setenv("MYSQL_USER", "admin_service")
    monkeypatch.setenv("MYSQL_PASSWORD", "password123")
    monkeypatch.setenv("MYSQL_LOCAL_PORT", "3307")

    settings = InventoryServiceSettings()

    assert (
        settings.database_url
        == "mysql+pymysql://admin_service:password123@localhost:3307/lexis_db?charset=utf8mb4"
    )


def test_settings_encode_mysql_credentials_when_reserved_chars_present(
    monkeypatch,
) -> None:
    monkeypatch.setenv("MYSQL_USER", "admin@inventory")
    monkeypatch.setenv("MYSQL_PASSWORD", "Gh4:#p@ss")

    settings = InventoryServiceSettings()

    assert (
        settings.database_url
        == "mysql+pymysql://admin%40inventory:Gh4%3A%23p%40ss@localhost:3306/inventory_service?charset=utf8mb4"
    )


def test_create_session_factory_binds_engine_to_database_url() -> None:
    session_factory = create_session_factory("sqlite://")

    assert str(session_factory.kw["bind"].url) == "sqlite://"


def test_settings_expose_rabbitmq_defaults() -> None:
    settings = InventoryServiceSettings()

    assert settings.rabbitmq_url == "amqp://guest:guest@localhost:5672/%2F"
    assert settings.rabbitmq_exchange_inventory == "inventory.direct"
    assert settings.rabbitmq_queue_inventory_request == "inventory.request.queue"
    assert settings.rabbitmq_queue_inventory_res == "inventory.response.queue"
    assert settings.rabbitmq_inventory_request_routing_key == "inventory.request"
    assert settings.rabbitmq_inventory_response_routing_key == "inventory.response.key"


def test_settings_map_rabbitmq_env_vars_into_url(monkeypatch) -> None:
    monkeypatch.setenv("RABBITMQ_DEFAULT_USER", "rabbit_admin")
    monkeypatch.setenv("RABBITMQ_DEFAULT_PASS", "password123")
    monkeypatch.setenv("RABBITMQ_PORT", "5673")

    settings = InventoryServiceSettings()

    assert settings.rabbitmq_url == "amqp://rabbit_admin:password123@localhost:5673/%2F"


def test_settings_map_rabbitmq_contract_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("INVENTORY_SERVICE_RABBITMQ_EXCHANGE", "inventory.events")
    monkeypatch.setenv(
        "INVENTORY_SERVICE_RABBITMQ_REQUEST_QUEUE",
        "inventory.request.runtime.queue",
    )
    monkeypatch.setenv(
        "INVENTORY_SERVICE_RABBITMQ_RESPONSE_QUEUE",
        "inventory.response.runtime.queue",
    )
    monkeypatch.setenv(
        "INVENTORY_SERVICE_RABBITMQ_REQUEST_ROUTING_KEY",
        "inventory.request.runtime",
    )
    monkeypatch.setenv(
        "INVENTORY_SERVICE_RABBITMQ_RESPONSE_ROUTING_KEY",
        "inventory.response.runtime",
    )

    settings = InventoryServiceSettings()

    assert settings.rabbitmq_exchange_inventory == "inventory.events"
    assert (
        settings.rabbitmq_queue_inventory_request == "inventory.request.runtime.queue"
    )
    assert settings.rabbitmq_queue_inventory_res == "inventory.response.runtime.queue"
    assert (
        settings.rabbitmq_inventory_request_routing_key == "inventory.request.runtime"
    )
    assert (
        settings.rabbitmq_inventory_response_routing_key == "inventory.response.runtime"
    )


def test_settings_encode_rabbitmq_credentials_when_reserved_chars_present(
    monkeypatch,
) -> None:
    monkeypatch.setenv("RABBITMQ_DEFAULT_USER", "rabbit@admin")
    monkeypatch.setenv("RABBITMQ_DEFAULT_PASS", "Gh4:#p@ss")

    settings = InventoryServiceSettings()

    assert (
        settings.rabbitmq_url
        == "amqp://rabbit%40admin:Gh4%3A%23p%40ss@localhost:5672/%2F"
    )


def test_resolve_alembic_database_url_uses_runtime_settings_when_ini_is_default(
    monkeypatch,
) -> None:
    monkeypatch.setenv("MYSQL_HOST", "mysql.prod.internal")
    monkeypatch.setenv("MYSQL_PORT", "3310")
    monkeypatch.setenv("MYSQL_DATABASE", "inventory_prod")
    monkeypatch.setenv("MYSQL_USER", "runtime_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "runtime_secret")

    resolved_url = resolve_alembic_database_url(ALEMBIC_INI_DEFAULT_DATABASE_URL)

    assert (
        resolved_url
        == "mysql+pymysql://runtime_user:runtime_secret@mysql.prod.internal:3310/inventory_prod?charset=utf8mb4"
    )


def test_resolve_alembic_database_url_preserves_explicit_override() -> None:
    explicit_url = "mysql+pymysql://custom_user:custom_pass@db.example:3306/custom_db"

    assert resolve_alembic_database_url(explicit_url) == explicit_url


def test_alembic_config_rejects_percent_encoded_url_without_escaping() -> None:
    config = Config()
    runtime_url = (
        "mysql+pymysql://runtime_user:Gh4%3A%23p%40ss@db.example:3306/"
        "inventory_prod?charset=utf8mb4"
    )

    with pytest.raises(ValueError, match="invalid interpolation syntax"):
        config.set_main_option("sqlalchemy.url", runtime_url)


def test_alembic_config_accepts_percent_encoded_url_when_escaped() -> None:
    config = Config()
    runtime_url = (
        "mysql+pymysql://runtime_user:Gh4%3A%23p%40ss@db.example:3306/"
        "inventory_prod?charset=utf8mb4"
    )

    config.set_main_option("sqlalchemy.url", runtime_url.replace("%", "%%"))

    assert config.get_main_option("sqlalchemy.url") == runtime_url


def test_alembic_env_uses_service_scoped_version_table_for_online_and_offline() -> None:
    env_content = (PROJECT_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

    assert 'ALEMBIC_VERSION_TABLE = "inventory_alembic_version"' in env_content
    assert env_content.count("version_table=ALEMBIC_VERSION_TABLE") == 2
