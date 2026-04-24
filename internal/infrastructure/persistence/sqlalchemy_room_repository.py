from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, sessionmaker

from internal.domain.entities.room import Room
from internal.domain.entities.room_availability import RoomAvailability
from internal.domain.errors import DomainRuleViolation
from internal.domain.valueobjects.date_range import DateRange
from internal.domain.valueobjects.money import Money
from internal.domain.valueobjects.room_operational_status import RoomOperationalStatus
from internal.domain.valueobjects.room_type import RoomType
from internal.infrastructure.persistence.models import RoomAvailabilityModel, RoomModel


class SqlAlchemyRoomRepository:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def add(self, room: Room) -> None:
        with self._session_factory() as session:
            session.add(self._to_model(room))
            try:
                session.commit()
            except IntegrityError as error:
                session.rollback()
                raise DomainRuleViolation(
                    f"Room number {room.room_number} already exists"
                ) from error

    def get_by_room_number(self, room_number: str) -> Room | None:
        with self._session_factory() as session:
            model = (
                session.query(RoomModel)
                .options(joinedload(RoomModel.availability))
                .filter(RoomModel.room_number == room_number)
                .one_or_none()
            )
            return None if model is None else self._to_domain(model)

    def get_by_id(self, room_id: UUID) -> Room | None:
        with self._session_factory() as session:
            model = (
                session.query(RoomModel)
                .options(joinedload(RoomModel.availability))
                .filter(RoomModel.room_id == str(room_id))
                .one_or_none()
            )
            return None if model is None else self._to_domain(model)

    def search(
        self,
        *,
        check_in: date,
        check_out: date,
        room_type: str | None = None,
        max_price: Decimal | None = None,
        min_capacity: int | None = None,
    ) -> list[Room]:
        with self._session_factory() as session:
            query = (
                session.query(RoomModel)
                .join(RoomModel.availability)
                .options(joinedload(RoomModel.availability))
                .filter(
                    RoomAvailabilityModel.start_date <= check_in,
                    RoomAvailabilityModel.end_date >= check_out,
                    RoomAvailabilityModel.booking_id.is_(None),
                    RoomModel.operational_status
                    == RoomOperationalStatus.AVAILABLE.value,
                )
            )

            if room_type is not None:
                query = query.filter(RoomModel.room_type == room_type)
            if max_price is not None:
                query = query.filter(RoomModel.price_amount <= max_price)
            if min_capacity is not None:
                query = query.filter(RoomModel.capacity >= min_capacity)

            models = query.order_by(RoomModel.room_number.asc()).all()
            return [self._to_domain(model) for model in models]

    def save(self, room: Room) -> None:
        with self._session_factory() as session:
            model = (
                session.query(RoomModel)
                .options(joinedload(RoomModel.availability))
                .filter(RoomModel.room_id == str(room.room_id))
                .one()
            )
            model.room_number = room.room_number
            model.room_type = room.room_type.value
            model.capacity = room.capacity
            model.price_amount = room.base_price.amount
            model.price_currency = room.base_price.currency
            model.operational_status = room.operational_status.value
            model.registered_at = room.registered_at
            if room.availability is None:
                model.availability = None
            elif model.availability is None:
                model.availability = RoomAvailabilityModel(
                    room_id=str(room.room_id),
                    start_date=room.availability.date_range.start_date,
                    end_date=room.availability.date_range.end_date,
                    booking_id=(
                        None
                        if room.availability.booking_id is None
                        else str(room.availability.booking_id)
                    ),
                )
            else:
                model.availability.start_date = room.availability.date_range.start_date
                model.availability.end_date = room.availability.date_range.end_date
                model.availability.booking_id = (
                    None
                    if room.availability.booking_id is None
                    else str(room.availability.booking_id)
                )
            session.commit()

    def list_all(self) -> list[Room]:
        with self._session_factory() as session:
            models = (
                session.query(RoomModel)
                .options(joinedload(RoomModel.availability))
                .order_by(RoomModel.room_number.asc())
                .all()
            )
            return [self._to_domain(model) for model in models]

    def _to_model(self, room: Room) -> RoomModel:
        model = RoomModel(
            room_id=str(room.room_id),
            room_number=room.room_number,
            room_type=room.room_type.value,
            capacity=room.capacity,
            price_amount=room.base_price.amount,
            price_currency=room.base_price.currency,
            operational_status=room.operational_status.value,
            registered_at=room.registered_at,
        )
        if room.availability is not None:
            model.availability = RoomAvailabilityModel(
                room_id=str(room.room_id),
                start_date=room.availability.date_range.start_date,
                end_date=room.availability.date_range.end_date,
                booking_id=(
                    None
                    if room.availability.booking_id is None
                    else str(room.availability.booking_id)
                ),
            )
        return model

    def _to_domain(self, model: RoomModel) -> Room:
        availability = None
        if model.availability is not None:
            availability = RoomAvailability(
                date_range=DateRange(
                    start_date=model.availability.start_date,
                    end_date=model.availability.end_date,
                ),
                booking_id=(
                    None
                    if model.availability.booking_id is None
                    else UUID(model.availability.booking_id)
                ),
            )
        return Room(
            room_id=UUID(model.room_id),
            room_number=model.room_number,
            room_type=RoomType(model.room_type),
            capacity=model.capacity,
            base_price=Money(
                amount=Decimal(str(model.price_amount)),
                currency=model.price_currency,
            ),
            operational_status=RoomOperationalStatus(model.operational_status),
            registered_at=model.registered_at,
            availability=availability,
        )
