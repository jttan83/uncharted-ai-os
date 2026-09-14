"""Capability-specific adapter for authorized Langflow Flow references."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langflow.services.authorization.flow_access import (
    FlowReadUnavailableError,
    resolve_authorized_flow_for_read,
)

from .errors import CapabilityFlowNotAccessibleError, CapabilityValidationError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlmodel.ext.asyncio.session import AsyncSession

    from langflow.services.database.models.user.model import User, UserRead


_FLOW_NOT_ACCESSIBLE = "Primary Flow is not accessible"
_CURRENT_USER_REQUIRED = "Authenticated user context is required for a non-null primary Flow link"
_OWNER_CONTEXT_MISMATCH = "Authenticated user context does not match the Capability owner"


def validate_capability_user_context(
    *,
    owner_id: UUID,
    current_user: User | UserRead | None,
    required: bool = False,
) -> User | UserRead | None:
    """Validate the authenticated user context used by Capability operations."""
    if current_user is None:
        if required:
            raise CapabilityValidationError(_CURRENT_USER_REQUIRED)
        return None
    if current_user.id != owner_id:
        raise CapabilityValidationError(_OWNER_CONTEXT_MISMATCH)
    return current_user


async def authorize_primary_flow_link(
    session: AsyncSession,
    *,
    primary_flow_id: UUID,
    owner_id: UUID,
    current_user: User | UserRead | None,
) -> UUID:
    """Authorize a non-null Flow link and return only its stable identifier."""
    authenticated_user = validate_capability_user_context(
        owner_id=owner_id,
        current_user=current_user,
        required=True,
    )
    if authenticated_user is None:  # pragma: no cover - enforced by required=True
        raise CapabilityValidationError(_CURRENT_USER_REQUIRED)

    try:
        with session.no_autoflush:
            flow = await resolve_authorized_flow_for_read(
                session,
                flow_id=primary_flow_id,
                current_user=authenticated_user,
            )
    except FlowReadUnavailableError as exc:
        raise CapabilityFlowNotAccessibleError(_FLOW_NOT_ACCESSIBLE) from exc
    return flow.id


async def resolve_visible_primary_flow_id(
    session: AsyncSession,
    *,
    primary_flow_id: UUID | None,
    current_user: User | UserRead,
) -> UUID | None:
    """Return the currently readable Flow ID without changing stored state."""
    if primary_flow_id is None:
        return None

    try:
        with session.no_autoflush:
            flow = await resolve_authorized_flow_for_read(
                session,
                flow_id=primary_flow_id,
                current_user=current_user,
            )
    except FlowReadUnavailableError:
        return None
    return flow.id
