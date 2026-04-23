from __future__ import annotations

from internal.application.queries.search_rooms_query import (
    RoomSummary,
    SearchRoomsQuery,
)
from internal.domain.entities.room import Room
from internal.domain.repositories.room_repository import RoomRepository
from internal.domain.valueobjects.date_range import DateRange


class SearchRoomsUseCase:
    def __init__(self, repository: RoomRepository) -> None:
        self._repository = repository

    def execute(self, query: SearchRoomsQuery) -> list[RoomSummary]:
        stay_window = DateRange(start_date=query.check_in, end_date=query.check_out)
        rooms = self._repository.search(
            check_in=stay_window.start_date,
            check_out=stay_window.end_date,
            room_type=query.room_type,
            max_price=query.max_price,
            min_capacity=query.min_capacity,
        )
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
