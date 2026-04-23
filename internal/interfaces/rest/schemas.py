from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelCaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)


class RegisterRoomRequest(CamelCaseModel):
    room_number: str = Field(description="Unique identifier for the room, typically alphanumeric.", examples=["101"])
    room_type: str = Field(description="Category or class of the room (e.g., STANDARD, SUITE, DELUXE).", examples=["STANDARD"])
    capacity: int = Field(description="Maximum number of occupants allowed in the room.", examples=[2])
    price_amount: Decimal = Field(description="Base price per night for the room.", examples=["100.00"])
    price_currency: str = Field(description="Three-letter ISO 4217 currency code.", examples=["USD"])
    operational_status: str = Field(description="Current operational status of the room (e.g., AVAILABLE, MAINTENANCE, OUT_OF_SERVICE).", examples=["AVAILABLE"])
    availability_start: date | None = Field(default=None, description="Start date from when the room is initially available for booking.", examples=["2026-04-24"])
    availability_end: date | None = Field(default=None, description="End date until when the room is initially available for booking.", examples=["2026-04-26"])


class RegisterRoomResponse(CamelCaseModel):
    room_id: str = Field(description="Universally Unique Identifier (UUID) assigned to the newly created room.", examples=["1fcdc9c0-26d9-4e9f-b80a-3dca3a2fe6c7"])


class UpdateRoomStatusRequest(CamelCaseModel):
    operational_status: str = Field(description="The new operational status to assign to the room.", examples=["MAINTENANCE"])


class RoomSummary(CamelCaseModel):
    room_id: str = Field(description="Universally Unique Identifier (UUID) of the room.", examples=["1fcdc9c0-26d9-4e9f-b80a-3dca3a2fe6c7"])
    room_number: str = Field(description="Unique identifier for the room.", examples=["101"])
    room_type: str = Field(description="Category or class of the room.", examples=["STANDARD"])
    capacity: int = Field(description="Maximum number of occupants allowed in the room.", examples=[2])
    price_amount: Decimal = Field(description="Base price per night for the room.", examples=["100.00"])
    price_currency: str = Field(description="Three-letter ISO 4217 currency code.", examples=["USD"])


class SearchRoomsResponse(CamelCaseModel):
    rooms: list[RoomSummary] = Field(description="List of rooms matching the search criteria.")


class ErrorResponse(CamelCaseModel):
    detail: str = Field(description="A human-readable explanation specific to the occurrence of the problem.", examples=["Room with number 101 already exists."])
