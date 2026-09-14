"""Transport-neutral Flow read resolution using Langflow's canonical authorization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from langflow.services.authorization.actions import FlowAction
from langflow.services.authorization.fetch import authorized_or_owner_scoped
from langflow.services.authorization.guards import ensure_flow_permission
from langflow.services.database.models.flow.model import Flow

if TYPE_CHECKING:
    from uuid import UUID

    from sqlmodel.ext.asyncio.session import AsyncSession

    from langflow.services.database.models.user.model import User, UserRead


_FLOW_READ_UNAVAILABLE = "Flow not found"


class FlowReadUnavailableError(Exception):
    """Raised when a Flow is missing or the authenticated user may not read it."""


async def load_flow_for_authorization(
    session: AsyncSession,
    *,
    flow_id: UUID,
    user_id: UUID,
    for_update: bool = False,
) -> Flow | None:
    """Load a Flow using the existing owner-safe, share-aware fetch policy."""
    return await authorized_or_owner_scoped(
        session,
        Flow,
        id_column=Flow.id,
        resource_id=flow_id,
        owner_column=Flow.user_id,
        owner_id=user_id,
        for_update=for_update,
    )


async def resolve_authorized_flow_for_read(
    session: AsyncSession,
    *,
    flow_id: UUID,
    current_user: User | UserRead,
) -> Flow:
    """Return a Flow the authenticated user may read.

    Missing and forbidden Flows deliberately produce the same transport-neutral
    service error. The existing permission guard still owns policy, request
    authentication context, plugin enforcement, and authorization auditing.
    """
    flow = await load_flow_for_authorization(
        session,
        flow_id=flow_id,
        user_id=current_user.id,
    )
    if flow is None:
        raise FlowReadUnavailableError(_FLOW_READ_UNAVAILABLE)

    try:
        await ensure_flow_permission(
            current_user,
            FlowAction.READ,
            flow_id=flow_id,
            flow_user_id=flow.user_id,
            workspace_id=flow.workspace_id,
            folder_id=flow.folder_id,
        )
    except HTTPException as exc:
        # The established guard exposes transport-specific denials. Contain
        # that legacy boundary here so service consumers never receive an HTTP
        # exception and cannot distinguish a denied Flow from a missing one.
        raise FlowReadUnavailableError(_FLOW_READ_UNAVAILABLE) from exc

    return flow
