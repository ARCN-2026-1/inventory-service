from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RegisterRoomCommand:
    room_number: str
    room_type: str
    capacity: int
    price_amount: Decimal
    price_currency: str
    operational_status: str
    availability_start: date | None = None
    availability_end: date | None = None
