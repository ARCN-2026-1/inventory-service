from urllib.parse import quote_plus

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ALEMBIC_INI_DEFAULT_DATABASE_URL = (
    "mysql+pymysql://inventory:secret@localhost:3306/inventory_service?charset=utf8mb4"
)


class InventoryServiceSettings(BaseSettings):
    database_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "INVENTORY_SERVICE_DATABASE_URL",
            "database_url",
        ),
    )
    mysql_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("MYSQL_HOST", "INVENTORY_SERVICE_MYSQL_HOST"),
    )
    mysql_port: int = Field(
        default=3306,
        validation_alias=AliasChoices(
            "MYSQL_LOCAL_PORT",
            "MYSQL_PORT",
            "INVENTORY_SERVICE_MYSQL_LOCAL_PORT",
        ),
    )
    mysql_database: str = Field(
        default="inventory_service",
        validation_alias=AliasChoices(
            "MYSQL_DATABASE",
            "INVENTORY_SERVICE_MYSQL_DATABASE",
        ),
    )
    mysql_user: str = Field(
        default="inventory",
        validation_alias=AliasChoices("MYSQL_USER", "INVENTORY_SERVICE_MYSQL_USER"),
    )
    mysql_password: str = Field(
        default="secret",
        validation_alias=AliasChoices(
            "MYSQL_PASSWORD",
            "INVENTORY_SERVICE_MYSQL_PASSWORD",
        ),
    )
    rabbitmq_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "INVENTORY_SERVICE_RABBITMQ_URL",
            "rabbitmq_url",
        ),
    )
    rabbitmq_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices(
            "RABBITMQ_HOST",
            "INVENTORY_SERVICE_RABBITMQ_HOST",
        ),
    )
    rabbitmq_port: int = Field(
        default=5672,
        validation_alias=AliasChoices(
            "RABBITMQ_PORT",
            "INVENTORY_SERVICE_RABBITMQ_PORT",
        ),
    )
    rabbitmq_default_user: str = Field(
        default="guest",
        validation_alias=AliasChoices(
            "RABBITMQ_DEFAULT_USER",
            "INVENTORY_SERVICE_RABBITMQ_DEFAULT_USER",
        ),
    )
    rabbitmq_default_pass: str = Field(
        default="guest",
        validation_alias=AliasChoices(
            "RABBITMQ_DEFAULT_PASS",
            "INVENTORY_SERVICE_RABBITMQ_DEFAULT_PASS",
        ),
    )
    rabbitmq_exchange_inventory: str = Field(
        default="inventory.direct",
        validation_alias=AliasChoices(
            "INVENTORY_SERVICE_RABBITMQ_EXCHANGE",
            "RABBITMQ_EXCHANGE_INVENTORY",
            "rabbitmq_exchange_inventory",
        ),
    )
    rabbitmq_queue_inventory_request: str = Field(
        default="inventory.request.queue",
        validation_alias=AliasChoices(
            "INVENTORY_SERVICE_RABBITMQ_REQUEST_QUEUE",
            "RABBITMQ_QUEUE_INVENTORY_REQUEST",
            "rabbitmq_queue_inventory_request",
        ),
    )
    rabbitmq_queue_inventory_res: str = Field(
        default="inventory.response.queue",
        validation_alias=AliasChoices(
            "INVENTORY_SERVICE_RABBITMQ_RESPONSE_QUEUE",
            "RABBITMQ_QUEUE_INVENTORY_RES",
            "rabbitmq_queue_inventory_res",
        ),
    )
    rabbitmq_inventory_request_routing_key: str = Field(
        default="inventory.request",
        validation_alias=AliasChoices(
            "INVENTORY_SERVICE_RABBITMQ_REQUEST_ROUTING_KEY",
            "RABBITMQ_ROUTING_KEY_INVENTORY_REQUEST",
            "rabbitmq_inventory_request_routing_key",
        ),
    )
    rabbitmq_inventory_response_routing_key: str = Field(
        default="inventory.response.key",
        validation_alias=AliasChoices(
            "INVENTORY_SERVICE_RABBITMQ_RESPONSE_ROUTING_KEY",
            "RABBITMQ_ROUTING_KEY_INVENTORY_RESPONSE",
            "rabbitmq_inventory_response_routing_key",
        ),
    )

    model_config = SettingsConfigDict()

    @model_validator(mode="after")
    def _populate_urls(self) -> "InventoryServiceSettings":
        if not self.database_url:
            encoded_mysql_user = quote_plus(self.mysql_user)
            encoded_mysql_password = quote_plus(self.mysql_password)
            self.database_url = (
                f"mysql+pymysql://{encoded_mysql_user}:{encoded_mysql_password}@"
                f"{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
            )
        if not self.rabbitmq_url:
            encoded_rabbitmq_user = quote_plus(self.rabbitmq_default_user)
            encoded_rabbitmq_password = quote_plus(self.rabbitmq_default_pass)
            self.rabbitmq_url = (
                f"amqp://{encoded_rabbitmq_user}:{encoded_rabbitmq_password}@"
                f"{self.rabbitmq_host}:{self.rabbitmq_port}/%2F"
            )
        return self


def resolve_alembic_database_url(configured_url: str | None) -> str:
    if configured_url and configured_url != ALEMBIC_INI_DEFAULT_DATABASE_URL:
        return configured_url

    return InventoryServiceSettings().database_url
