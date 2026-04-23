from uuid import UUID

from fastapi.testclient import TestClient

from internal.interfaces.rest.app import create_app


class InMemoryRoomRepository:
    def __init__(self) -> None:
        self.rooms_by_number: dict[str, object] = {}

    def add(self, room) -> None:
        self.rooms_by_number[room.room_number] = room

    def get_by_room_number(self, room_number: str):
        return self.rooms_by_number.get(room_number)


def test_post_rooms_registers_room_without_auth() -> None:
    client = TestClient(create_app(repository=InMemoryRoomRepository()))

    response = client.post(
        "/rooms",
        json={
            "roomNumber": "101",
            "roomType": "STANDARD",
            "capacity": 2,
            "priceAmount": "100.00",
            "priceCurrency": "USD",
            "operationalStatus": "AVAILABLE",
            "availabilityStart": "2026-04-24",
            "availabilityEnd": "2026-04-26",
        },
    )

    assert response.status_code == 201
    assert UUID(response.json()["roomId"])


def test_post_rooms_rejects_invalid_price() -> None:
    client = TestClient(create_app(repository=InMemoryRoomRepository()))

    response = client.post(
        "/rooms",
        json={
            "roomNumber": "102",
            "roomType": "STANDARD",
            "capacity": 2,
            "priceAmount": "0.00",
            "priceCurrency": "USD",
            "operationalStatus": "AVAILABLE",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Price amount must be greater than zero"}


def test_post_rooms_rejects_invalid_dates() -> None:
    client = TestClient(create_app(repository=InMemoryRoomRepository()))

    response = client.post(
        "/rooms",
        json={
            "roomNumber": "103",
            "roomType": "STANDARD",
            "capacity": 2,
            "priceAmount": "100.00",
            "priceCurrency": "USD",
            "operationalStatus": "AVAILABLE",
            "availabilityStart": "2026-04-26",
            "availabilityEnd": "2026-04-24",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Availability end date must be after start date"
    }


def test_post_rooms_rejects_duplicate_room_number() -> None:
    client = TestClient(create_app(repository=InMemoryRoomRepository()))
    payload = {
        "roomNumber": "104",
        "roomType": "DELUXE",
        "capacity": 2,
        "priceAmount": "130.00",
        "priceCurrency": "USD",
        "operationalStatus": "AVAILABLE",
    }

    first_response = client.post("/rooms", json=payload)
    second_response = client.post("/rooms", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "Room number 104 already exists"}
