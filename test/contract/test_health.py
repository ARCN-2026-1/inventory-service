from fastapi.testclient import TestClient

from internal.interfaces.rest.app import create_app


class StubRepository:
    def add(self, room) -> None:
        raise AssertionError("health endpoint should not persist rooms")

    def get_by_room_number(self, room_number: str):
        raise AssertionError("health endpoint should not query rooms")


def test_health_returns_ok_without_auth() -> None:
    client = TestClient(create_app(repository=StubRepository()))

    response = client.get("/health")

    assert response.status_code == 200
