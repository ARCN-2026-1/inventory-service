from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RoomModel(Base):
    __tablename__ = "rooms"

    room_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_number: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True
    )
    room_type: Mapped[str] = mapped_column(String(32), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    operational_status: Mapped[str] = mapped_column(String(32), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    availability: Mapped[RoomAvailabilityModel | None] = relationship(
        back_populates="room", cascade="all, delete-orphan", uselist=False
    )


class RoomAvailabilityModel(Base):
    __tablename__ = "room_availability"

    room_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rooms.room_id", ondelete="CASCADE"), primary_key=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    booking_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    room: Mapped[RoomModel] = relationship(back_populates="availability")
