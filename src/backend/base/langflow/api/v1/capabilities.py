"""Authenticated V0.1 API for owner-scoped business Capabilities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from langflow.api.utils import CurrentActiveUser, DbSession, DbSessionReadOnly
from langflow.services.authorization.flow_access import (
    FlowReadUnavailableError,
    resolve_authorized_flow_for_read,
)
from langflow.services.database.models.capability.crud import (
    create_capability,
    get_capability,
    list_capabilities,
    update_capability,
)
from langflow.services.database.models.capability.errors import (
    CapabilityConflictError,
    CapabilityFlowNotAccessibleError,
    CapabilityHierarchyConflictError,
    CapabilityNotFoundError,
    CapabilityValidationError,
    ParentCapabilityNotFoundError,
)
from langflow.services.database.models.capability.schema import (
    CapabilityCreate,
    CapabilityListResponse,
    CapabilityRead,
    CapabilitySummary,
    CapabilityUpdate,
    FlowLinkAvailability,
    FlowLinkAvailabilityStatus,
    FlowLinkSummary,
)

if TYPE_CHECKING:
    from sqlmodel import SQLModel
    from sqlmodel.ext.asyncio.session import AsyncSession

    from langflow.services.database.models.capability.model import Capability
    from langflow.services.database.models.user.model import User, UserRead


router = APIRouter(prefix="/capabilities", tags=["Capabilities"])

_CAPABILITY_ERROR_TYPES = (
    CapabilityNotFoundError,
    ParentCapabilityNotFoundError,
    CapabilityFlowNotAccessibleError,
    CapabilityHierarchyConflictError,
    CapabilityConflictError,
    CapabilityValidationError,
)


def _raise_capability_http_error(error: Exception) -> NoReturn:
    """Translate only expected Capability domain failures at the HTTP boundary."""
    if isinstance(error, CapabilityFlowNotAccessibleError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, CapabilityNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, CapabilityConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if isinstance(error, CapabilityValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    raise error


async def _project_primary_flow_link(
    session: AsyncSession,
    *,
    primary_flow_id: UUID | None,
    current_user: User | UserRead,
) -> FlowLinkAvailability:
    """Resolve the authorized response-only summary for a stored Flow link."""
    if primary_flow_id is None:
        return FlowLinkAvailability(status=FlowLinkAvailabilityStatus.NOT_LINKED, flow=None)

    try:
        with session.no_autoflush:
            flow = await resolve_authorized_flow_for_read(
                session,
                flow_id=primary_flow_id,
                current_user=current_user,
            )
    except FlowReadUnavailableError:
        return FlowLinkAvailability(status=FlowLinkAvailabilityStatus.UNAVAILABLE, flow=None)

    return FlowLinkAvailability(
        status=FlowLinkAvailabilityStatus.AVAILABLE,
        flow=FlowLinkSummary(id=flow.id, name=flow.name),
    )


def _response_values(capability: Capability, response_type: type[SQLModel]) -> dict:
    """Copy only fields declared by the explicit public response schema."""
    values = {
        field_name: getattr(capability, field_name)
        for field_name in response_type.model_fields
        if field_name != "primary_flow_link"
    }
    for field_name in ("assessed_at", "created_at", "updated_at"):
        value = values.get(field_name)
        if isinstance(value, datetime) and value.tzinfo is None:
            values[field_name] = value.replace(tzinfo=timezone.utc)
    return values


async def project_capability_for_response(
    session: AsyncSession,
    *,
    capability: Capability,
    current_user: User | UserRead,
) -> CapabilityRead:
    """Build a detailed response without mutating the persisted Capability."""
    primary_flow_link = await _project_primary_flow_link(
        session,
        primary_flow_id=capability.primary_flow_id,
        current_user=current_user,
    )
    return CapabilityRead(
        **_response_values(capability, CapabilityRead),
        primary_flow_link=primary_flow_link,
    )


def _project_capability_summary(
    *,
    capability: Capability,
    primary_flow_link: FlowLinkAvailability,
) -> CapabilitySummary:
    return CapabilitySummary(
        **_response_values(capability, CapabilitySummary),
        primary_flow_link=primary_flow_link,
    )


@router.get("", response_model=CapabilityListResponse)
async def read_capabilities(
    session: DbSessionReadOnly,
    current_user: CurrentActiveUser,
    include_archived: Annotated[bool, Query()] = False,  # noqa: FBT002 - FastAPI query default
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
) -> CapabilityListResponse:
    """Return an owner-scoped, deterministically ordered Capability page."""
    try:
        capabilities, total = await list_capabilities(
            session,
            owner_id=current_user.id,
            include_archived=include_archived,
            offset=offset,
            limit=limit,
        )
    except _CAPABILITY_ERROR_TYPES as error:
        _raise_capability_http_error(error)

    link_cache: dict[UUID | None, FlowLinkAvailability] = {}
    items: list[CapabilitySummary] = []
    for capability in capabilities:
        primary_flow_id = capability.primary_flow_id
        if primary_flow_id not in link_cache:
            link_cache[primary_flow_id] = await _project_primary_flow_link(
                session,
                primary_flow_id=primary_flow_id,
                current_user=current_user,
            )
        items.append(
            _project_capability_summary(
                capability=capability,
                primary_flow_link=link_cache[primary_flow_id],
            )
        )
    return CapabilityListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{capability_id}", response_model=CapabilityRead)
async def read_capability(
    capability_id: UUID,
    session: DbSessionReadOnly,
    current_user: CurrentActiveUser,
) -> CapabilityRead:
    """Return one Capability within the authenticated owner's map."""
    try:
        capability = await get_capability(
            session,
            capability_id=capability_id,
            owner_id=current_user.id,
        )
    except _CAPABILITY_ERROR_TYPES as error:
        _raise_capability_http_error(error)
    return await project_capability_for_response(
        session,
        capability=capability,
        current_user=current_user,
    )


@router.post("", response_model=CapabilityRead, status_code=status.HTTP_201_CREATED)
async def create_capability_route(
    payload: CapabilityCreate,
    session: DbSession,
    current_user: CurrentActiveUser,
) -> CapabilityRead:
    """Create a Capability owned by the authenticated user."""
    try:
        capability = await create_capability(
            session,
            owner_id=current_user.id,
            current_user=current_user,
            payload=payload,
        )
    except _CAPABILITY_ERROR_TYPES as error:
        _raise_capability_http_error(error)
    return await project_capability_for_response(
        session,
        capability=capability,
        current_user=current_user,
    )


@router.patch("/{capability_id}", response_model=CapabilityRead)
async def update_capability_route(
    capability_id: UUID,
    payload: CapabilityUpdate,
    session: DbSession,
    current_user: CurrentActiveUser,
) -> CapabilityRead:
    """Partially update, archive, or restore an owner-scoped Capability."""
    try:
        capability = await update_capability(
            session,
            capability_id=capability_id,
            owner_id=current_user.id,
            current_user=current_user,
            payload=payload,
        )
    except _CAPABILITY_ERROR_TYPES as error:
        _raise_capability_http_error(error)
    return await project_capability_for_response(
        session,
        capability=capability,
        current_user=current_user,
    )
