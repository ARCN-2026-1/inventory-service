from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, Path, Query, Request, Response, status
from fastapi.responses import JSONResponse

from internal.application.commands.register_room import RegisterRoomCommand
from internal.application.commands.update_room_status import UpdateRoomStatusCommand
from internal.application.errors import (
    ApplicationError,
    DuplicateRoomNumberError,
    RoomNotFoundError,
)
from internal.application.queries.get_all_rooms_use_case import GetAllRoomsUseCase
from internal.application.queries.search_rooms_query import SearchRoomsQuery
from internal.application.queries.search_rooms_use_case import SearchRoomsUseCase
from internal.application.usecases.register_room import RegisterRoomUseCase
from internal.application.usecases.update_room_status import UpdateRoomStatusUseCase
from internal.domain.errors import DomainRuleViolation
from internal.infrastructure.config.settings import InventoryServiceSettings
from internal.infrastructure.persistence.database import create_session_factory
from internal.infrastructure.persistence.sqlalchemy_room_repository import (
    SqlAlchemyRoomRepository,
)
from internal.interfaces.rest.schemas import (
    ErrorResponse,
    RegisterRoomRequest,
    RegisterRoomResponse,
    RoomSummary,
    SearchRoomsResponse,
    UpdateRoomStatusRequest,
)

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=logging.INFO)


def _handle_error(error: ApplicationError | DomainRuleViolation) -> JSONResponse:
    if isinstance(error, DuplicateRoomNumberError):
        return JSONResponse(status_code=409, content={"detail": str(error)})
    if isinstance(error, RoomNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(error)})
    if isinstance(error, DomainRuleViolation):
        return JSONResponse(status_code=400, content={"detail": str(error)})
    return JSONResponse(status_code=400, content={"detail": str(error)})


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request, error: ApplicationError
    ) -> JSONResponse:
        logger.warning(
            "Inventory request failed method=%s path=%s error_type=%s",
            request.method,
            request.url.path,
            error.__class__.__name__,
        )
        return _handle_error(error)

    @app.exception_handler(DomainRuleViolation)
    async def domain_rule_violation_handler(
        request: Request, error: DomainRuleViolation
    ) -> JSONResponse:
        logger.warning(
            "Inventory domain rule violation method=%s path=%s error_type=%s",
            request.method,
            request.url.path,
            error.__class__.__name__,
        )
        return _handle_error(error)


def create_app(
    *,
    repository: object | None = None,
    settings: InventoryServiceSettings | None = None,
) -> FastAPI:
    _configure_logging()
    resolved_repository = repository
    if resolved_repository is None:
        resolved_settings = settings or InventoryServiceSettings()
        session_factory = create_session_factory(resolved_settings.database_url)
        resolved_repository = SqlAlchemyRoomRepository(session_factory)

    app = FastAPI(title="Hotel DDD Inventory Service API", version="0.1.0")
    _register_exception_handlers(app)
    app.state.room_repository = resolved_repository

    @app.get(
        "/health",
        status_code=status.HTTP_200_OK,
        tags=["Health"],
        summary="Check service health",
        response_description="Service is up and running.",
        responses={200: {"description": "Service is healthy"}},
    )
    def health() -> Response:
        """
        Health check endpoint to verify that the service is running correctly.
        """
        return Response(status_code=status.HTTP_200_OK)

    @app.get(
        "/rooms/all",
        status_code=status.HTTP_200_OK,
        response_model=SearchRoomsResponse,
        response_model_by_alias=True,
        tags=["Rooms"],
        summary="Get all rooms without filters",
        response_description="A list of all rooms in the inventory.",
        responses={400: {"model": ErrorResponse}},
    )
    def get_all_rooms() -> SearchRoomsResponse:
        """
        Retrieves a list of all rooms in the inventory system,
        without any availability filters.
        """
        rooms = GetAllRoomsUseCase(app.state.room_repository).execute()
        return SearchRoomsResponse(
            rooms=[
                RoomSummary(
                    room_id=room.room_id,
                    room_number=room.room_number,
                    room_type=room.room_type,
                    capacity=room.capacity,
                    price_amount=room.price_amount,
                    price_currency=room.price_currency,
                )
                for room in rooms
            ]
        )

    @app.post(
        "/rooms",
        status_code=status.HTTP_201_CREATED,
        response_model=RegisterRoomResponse,
        response_model_by_alias=True,
        tags=["Rooms"],
        summary="Register a new room",
        response_description="The newly registered room's ID.",
        responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    )
    def register_room(payload: RegisterRoomRequest) -> RegisterRoomResponse:
        """
        Registers a new room in the inventory system.

        Requires room details such as room number, type, capacity, and pricing.
        Fails with a 409 Conflict if a room with the same number already exists.
        """
        room_id = RegisterRoomUseCase(app.state.room_repository).execute(
            RegisterRoomCommand(
                room_number=payload.room_number,
                room_type=payload.room_type,
                capacity=payload.capacity,
                price_amount=payload.price_amount,
                price_currency=payload.price_currency,
                operational_status=payload.operational_status,
                availability_start=payload.availability_start,
                availability_end=payload.availability_end,
            )
        )
        return RegisterRoomResponse(room_id=str(room_id))

    @app.get(
        "/rooms",
        status_code=status.HTTP_200_OK,
        response_model=SearchRoomsResponse,
        response_model_by_alias=True,
        tags=["Rooms"],
        summary="Search for available rooms",
        response_description="A list of rooms matching the search criteria.",
        responses={400: {"model": ErrorResponse}},
    )
    def search_rooms(
        check_in: Annotated[
            date,
            Query(description="The check-in date for the search period."),
        ],
        check_out: Annotated[
            date,
            Query(description="The check-out date for the search period."),
        ],
        room_type: Annotated[
            str | None,
            Query(description="Filter by a specific room type (e.g., STANDARD)."),
        ] = None,
        max_price: Annotated[
            Decimal | None,
            Query(description="Maximum price per night."),
        ] = None,
        min_capacity: Annotated[
            int | None,
            Query(description="Minimum number of occupants the room must accommodate."),
        ] = None,
    ) -> SearchRoomsResponse:
        """
        Retrieves a list of rooms that are available between the specified
        check-in and check-out dates.

        Optional filters include room type, maximum price, and minimum capacity.
        """
        rooms = SearchRoomsUseCase(app.state.room_repository).execute(
            SearchRoomsQuery(
                check_in=check_in,
                check_out=check_out,
                room_type=room_type,
                max_price=max_price,
                min_capacity=min_capacity,
            )
        )
        return SearchRoomsResponse(
            rooms=[
                RoomSummary(
                    room_id=room.room_id,
                    room_number=room.room_number,
                    room_type=room.room_type,
                    capacity=room.capacity,
                    price_amount=room.price_amount,
                    price_currency=room.price_currency,
                )
                for room in rooms
            ]
        )

    @app.patch(
        "/rooms/{room_id}/status",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["Rooms"],
        summary="Update room operational status",
        response_description=(
            "Successfully updated the room status (no content returned)."
        ),
        responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    def update_room_status(
        payload: UpdateRoomStatusRequest,
        room_id: Annotated[
            UUID,
            Path(description="The UUID of the room to update."),
        ],
    ) -> Response:
        """
        Updates the operational status of an existing room.

        For example, you can mark an AVAILABLE room as MAINTENANCE or OUT_OF_SERVICE.
        """
        UpdateRoomStatusUseCase(app.state.room_repository).execute(
            UpdateRoomStatusCommand(
                room_id=room_id,
                new_status=payload.operational_status,
                changed_at=datetime.now(timezone.utc),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app
