from internal.infrastructure.config.settings import InventoryServiceSettings
from internal.infrastructure.persistence.database import create_session_factory


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
