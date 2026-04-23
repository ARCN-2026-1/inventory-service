from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateRoomStatusCommand:
    room_id: UUID
    new_status: str
    changed_at: datetime
