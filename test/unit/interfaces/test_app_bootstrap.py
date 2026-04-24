from internal.interfaces.rest.app import create_app
from main import app


class StubRepository:
    def add(self, room) -> None:
        raise AssertionError("bootstrap test should not persist rooms")

    def get_by_room_number(self, room_number: str):
        raise AssertionError("bootstrap test should not query rooms")

    def get_by_id(self, room_id):
        raise AssertionError("bootstrap test should not query room ids")

    def save(self, room) -> None:
        raise AssertionError("bootstrap test should not save rooms")

    def search(self, **kwargs):
        raise AssertionError("bootstrap test should not search rooms")

    def list_all(self):
        raise AssertionError("bootstrap test should not list rooms")


def test_create_app_registers_room_routes_and_uses_provided_repository() -> None:
    repository = StubRepository()
    application = create_app(repository=repository)

    openapi_paths = application.openapi()["paths"]
    routes = {"/health", "/rooms", "/rooms/all", "/rooms/{room_id}/status"}

    assert set(openapi_paths) == routes
    assert set(openapi_paths["/health"]) == {"get"}
    assert set(openapi_paths["/rooms"]) == {"get", "post"}
    assert set(openapi_paths["/rooms/all"]) == {"get"}
    assert set(openapi_paths["/rooms/{room_id}/status"]) == {"patch"}
    assert application.state.room_repository is repository


def test_main_exposes_bootstrap_http_contract_without_rabbitmq_hooks() -> None:
    openapi_paths = app.openapi()["paths"]
    routes = {"/health", "/rooms", "/rooms/all", "/rooms/{room_id}/status"}

    assert set(openapi_paths) == routes
    assert set(openapi_paths["/rooms"]) == {"get", "post"}
    assert set(openapi_paths["/rooms/all"]) == {"get"}
    assert set(openapi_paths["/rooms/{room_id}/status"]) == {"patch"}
    assert app.router.on_startup == []
    assert app.router.on_shutdown == []
