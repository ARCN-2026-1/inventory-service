from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from internal.domain.entities.room import Room


class RoomRepository(Protocol):
    def add(self, room: Room) -> None: ...

    def get_by_room_number(self, room_number: str) -> Room | None: ...

    def get_by_id(self, room_id: UUID) -> Room | None: ...

    def search(
        self,
        *,
        check_in: date,
        check_out: date,
        room_type: str | None = None,
        max_price: Decimal | None = None,
        min_capacity: int | None = None,
    ) -> list[Room]: ...

    def save(self, room: Room) -> None: ...

    def list_all(self) -> list[Room]: ...
