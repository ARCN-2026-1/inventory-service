from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    rabbitmq_exchange_inventory: str = "inventory.direct"
    rabbitmq_queue_inventory_request: str = "inventory.request.queue"
    rabbitmq_queue_inventory_res: str = "inventory.response.queue"
    rabbitmq_inventory_request_routing_key: str = "inventory.request"
    rabbitmq_inventory_response_routing_key: str = "inventory.response.key"

    model_config = SettingsConfigDict()

    @model_validator(mode="after")
    def _populate_urls(self) -> "InventoryServiceSettings":
        if not self.database_url:
            self.database_url = (
                f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@"
                f"{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
            )
        if not self.rabbitmq_url:
            self.rabbitmq_url = (
                f"amqp://{self.rabbitmq_default_user}:{self.rabbitmq_default_pass}@"
                f"{self.rabbitmq_host}:{self.rabbitmq_port}/%2F"
            )
        return self
