from fastapi.testclient import TestClient

from internal.interfaces.rest.app import create_app


class StubRepository:
    def add(self, room) -> None:
        raise AssertionError("unsupported capability checks should not persist rooms")

    def get_by_room_number(self, room_number: str):
        raise AssertionError("unsupported capability checks should not query rooms")

    def get_by_id(self, room_id):
        del room_id
        return None

    def save(self, room) -> None:
        raise AssertionError("unsupported capability checks should not save rooms")

    def search(self, **kwargs):
        return []

    def list_all(self):
        return []


def test_openapi_contract_exposes_only_bootstrap_http_capabilities() -> None:
    client = TestClient(create_app(repository=StubRepository()))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert set(response.json()["paths"]) == {
        "/health",
        "/rooms",
        "/rooms/all",
        "/rooms/{room_id}",
        "/rooms/{room_id}/status",
    }
    assert set(response.json()["paths"]["/rooms"]) == {"get", "post"}
    assert set(response.json()["paths"]["/rooms/all"]) == {"get"}
    assert set(response.json()["paths"]["/rooms/{room_id}"]) == {"get"}
    assert set(response.json()["paths"]["/rooms/{room_id}/status"]) == {"patch"}


def test_update_room_status_returns_not_found_for_unknown_room() -> None:
    client = TestClient(create_app(repository=StubRepository()))

    response = client.patch(
        "/rooms/8cd01c40-b6f4-4fa2-bf4a-7d4df81540ce/status",
        json={"operationalStatus": "MAINTENANCE"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Room not found"}
