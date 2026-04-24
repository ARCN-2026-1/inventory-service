from __future__ import annotations

from internal.application.queries.search_rooms_query import RoomSummary
from internal.domain.entities.room import Room
from internal.domain.repositories.room_repository import RoomRepository


class GetAllRoomsUseCase:
    def __init__(self, repository: RoomRepository) -> None:
        self._repository = repository

    def execute(self) -> list[RoomSummary]:
        rooms = self._repository.list_all()
        return [self._to_summary(room) for room in rooms]

    def _to_summary(self, room: Room) -> RoomSummary:
        return RoomSummary(
            room_id=str(room.room_id),
            room_number=room.room_number,
            room_type=room.room_type.value,
            capacity=room.capacity,
            price_amount=room.base_price.amount,
            price_currency=room.base_price.currency,
        )
