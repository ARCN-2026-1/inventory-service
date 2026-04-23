from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SearchRoomsQuery:
    check_in: date
    check_out: date
    room_type: str | None = None
    max_price: Decimal | None = None
    min_capacity: int | None = None


@dataclass(frozen=True, slots=True)
class RoomSummary:
    room_id: str
    room_number: str
    room_type: str
    capacity: int
    price_amount: Decimal
    price_currency: str
