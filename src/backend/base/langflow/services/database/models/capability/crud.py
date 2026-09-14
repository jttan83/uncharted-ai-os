from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlmodel import col, func, select

from langflow.services.database.models.user.model import User

from .constants import ASSESSMENT_BEARING_FIELDS, CapabilityStatus
from .errors import (
    CapabilityConflictError,
    CapabilityDomainError,
    CapabilityFlowNotAccessibleError,
    CapabilityHierarchyConflictError,
    CapabilityNotFoundError,
    CapabilityValidationError,
    ParentCapabilityNotFoundError,
)
from .flow_access import authorize_primary_flow_link, validate_capability_user_context
from .model import Capability
from .schema import CapabilityCreate, CapabilityUpdate
from .validation import has_substantive_assessment_data, validate_frequency_pair

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel.sql.expression import SelectOfScalar

    from langflow.services.database.models.user.model import UserRead


MAX_CAPABILITY_LIST_LIMIT = 200

__all__ = [
    "CapabilityConflictError",
    "CapabilityDomainError",
    "CapabilityFlowNotAccessibleError",
    "CapabilityHierarchyConflictError",
    "CapabilityNotFoundError",
    "CapabilityValidationError",
    "ParentCapabilityNotFoundError",
    "archive_capability",
    "create_capability",
    "get_capability",
    "list_capabilities",
    "restore_capability",
    "update_capability",
]

_CAPABILITY_NOT_FOUND = "Capability not found"
_PARENT_NOT_FOUND = "Parent Capability not found"
_SELF_PARENT_ERROR = "A Capability cannot parent itself"
_HIERARCHY_CYCLE_ERROR = "Capability hierarchy cycle detected"
_INCONSISTENT_HIERARCHY_ERROR = "Capability hierarchy is inconsistent"
_ARCHIVED_PARENT_ERROR = "An active Capability cannot have an archived parent"
_ACTIVE_CHILDREN_ERROR = "Capability cannot be archived while it has active children"
_EMPTY_UPDATE_ERROR = "Capability update must contain at least one field"
_INVALID_OFFSET_ERROR = "offset must be greater than or equal to zero"
_INVALID_LIMIT_ERROR = f"limit must be between 1 and {MAX_CAPABILITY_LIST_LIMIT}"

MUTABLE_CAPABILITY_FIELDS = (
    "name",
    "functional_area",
    "description",
    "parent_capability_id",
    "status",
    "current_maturity",
    "target_maturity",
    "human_oversight",
    "oversight_notes",
    "frequency_value",
    "frequency_period",
    "baseline_human_effort_minutes_per_run",
    "business_value",
    "ai_feasibility",
    "ai_execution_risk",
    "assessment_notes",
    "inputs",
    "outputs",
    "tools",
    "primary_flow_id",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _owner_lock_statement(owner_id: UUID) -> SelectOfScalar:
    """Build the per-owner hierarchy serialization query.

    PostgreSQL emits ``FOR UPDATE``. SQLite intentionally omits that clause;
    its transaction-level write serialization remains the correctness floor.
    """
    return select(User.id).where(User.id == owner_id).with_for_update()


async def _lock_owner_for_hierarchy(session: AsyncSession, owner_id: UUID) -> None:
    (await session.exec(_owner_lock_statement(owner_id))).first()


async def _find_owner_capability(
    session: AsyncSession,
    *,
    capability_id: UUID,
    owner_id: UUID,
    for_update: bool = False,
) -> Capability | None:
    statement = select(Capability).where(
        Capability.id == capability_id,
        Capability.user_id == owner_id,
    )
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return (await session.exec(statement)).first()


async def get_capability(
    session: AsyncSession,
    *,
    capability_id: UUID,
    owner_id: UUID,
) -> Capability:
    """Return one Capability within the authoritative owner scope."""
    capability = await _find_owner_capability(
        session,
        capability_id=capability_id,
        owner_id=owner_id,
    )
    if capability is None:
        raise CapabilityNotFoundError(_CAPABILITY_NOT_FOUND)
    return capability


async def list_capabilities(
    session: AsyncSession,
    *,
    owner_id: UUID,
    include_archived: bool = False,
    offset: int = 0,
    limit: int = MAX_CAPABILITY_LIST_LIMIT,
) -> tuple[list[Capability], int]:
    """List an owner's Capabilities and the pre-pagination filtered total."""
    if offset < 0:
        raise CapabilityValidationError(_INVALID_OFFSET_ERROR)
    if not 1 <= limit <= MAX_CAPABILITY_LIST_LIMIT:
        raise CapabilityValidationError(_INVALID_LIMIT_ERROR)

    filters = [Capability.user_id == owner_id]
    if not include_archived:
        filters.append(Capability.status == CapabilityStatus.ACTIVE)

    total_statement = select(func.count()).select_from(Capability).where(*filters)
    total = int((await session.exec(total_statement)).first() or 0)
    list_statement = (
        select(Capability)
        .where(*filters)
        .order_by(
            col(Capability.functional_area),
            col(Capability.name),
            col(Capability.id),
        )
        .offset(offset)
        .limit(limit)
    )
    return list((await session.exec(list_statement)).all()), total


def _validate_effective_frequency(state: Mapping[str, Any]) -> None:
    try:
        validate_frequency_pair(state["frequency_period"], state["frequency_value"])
    except ValueError as exc:
        raise CapabilityValidationError(str(exc)) from exc


def _assessment_state(state: Mapping[str, Any]) -> dict[str, Any]:
    return {field_name: state[field_name] for field_name in ASSESSMENT_BEARING_FIELDS}


def _is_active(status: CapabilityStatus | str) -> bool:
    return status == CapabilityStatus.ACTIVE


def _is_archived(status: CapabilityStatus | str) -> bool:
    return status == CapabilityStatus.ARCHIVED


async def _validate_parent_chain(
    session: AsyncSession,
    *,
    owner_id: UUID,
    proposed_parent_id: UUID,
    child_id: UUID | None,
    child_status: CapabilityStatus | str,
) -> None:
    """Validate an owner-scoped parent and iteratively walk all ancestors."""
    ancestor_id: UUID | None = proposed_parent_id
    visited: set[UUID] = set()
    is_direct_parent = True

    while ancestor_id is not None:
        if child_id is not None and ancestor_id == child_id:
            if is_direct_parent:
                raise CapabilityValidationError(_SELF_PARENT_ERROR)
            raise CapabilityHierarchyConflictError(_HIERARCHY_CYCLE_ERROR)
        if ancestor_id in visited:
            raise CapabilityHierarchyConflictError(_HIERARCHY_CYCLE_ERROR)
        visited.add(ancestor_id)

        ancestor = await _find_owner_capability(
            session,
            capability_id=ancestor_id,
            owner_id=owner_id,
            for_update=True,
        )
        if ancestor is None:
            if is_direct_parent:
                raise ParentCapabilityNotFoundError(_PARENT_NOT_FOUND)
            raise CapabilityHierarchyConflictError(_INCONSISTENT_HIERARCHY_ERROR)
        if is_direct_parent and _is_active(child_status) and _is_archived(ancestor.status):
            raise CapabilityHierarchyConflictError(_ARCHIVED_PARENT_ERROR)

        ancestor_id = ancestor.parent_capability_id
        is_direct_parent = False


async def _ensure_no_active_children(
    session: AsyncSession,
    *,
    capability_id: UUID,
    owner_id: UUID,
) -> None:
    active_child = (
        await session.exec(
            select(Capability.id)
            .where(
                Capability.parent_capability_id == capability_id,
                Capability.user_id == owner_id,
                Capability.status == CapabilityStatus.ACTIVE,
            )
            .limit(1)
            .with_for_update()
        )
    ).first()
    if active_child is not None:
        raise CapabilityHierarchyConflictError(_ACTIVE_CHILDREN_ERROR)


async def create_capability(
    session: AsyncSession,
    *,
    owner_id: UUID,
    payload: CapabilityCreate,
    current_user: User | UserRead | None = None,
) -> Capability:
    """Create an owner-scoped Capability without committing the transaction."""
    validate_capability_user_context(owner_id=owner_id, current_user=current_user)
    create_values = payload.model_dump()
    _validate_effective_frequency(create_values)

    primary_flow_id = create_values["primary_flow_id"]
    if primary_flow_id is not None:
        create_values["primary_flow_id"] = await authorize_primary_flow_link(
            session,
            primary_flow_id=primary_flow_id,
            owner_id=owner_id,
            current_user=current_user,
        )

    parent_id = create_values["parent_capability_id"]
    if parent_id is not None:
        await _lock_owner_for_hierarchy(session, owner_id)
        await _validate_parent_chain(
            session,
            owner_id=owner_id,
            proposed_parent_id=parent_id,
            child_id=None,
            child_status=create_values["status"],
        )

    assessed_at = None
    assessed_by = None
    if has_substantive_assessment_data(_assessment_state(create_values)):
        assessed_at = _utc_now()
        assessed_by = owner_id

    capability = Capability(
        **create_values,
        user_id=owner_id,
        workspace_id=None,
        assessed_at=assessed_at,
        assessed_by=assessed_by,
    )
    session.add(capability)
    await session.flush()
    return capability


async def update_capability(
    session: AsyncSession,
    *,
    capability_id: UUID,
    owner_id: UUID,
    payload: CapabilityUpdate,
    current_user: User | UserRead | None = None,
) -> Capability:
    """Apply an owner-scoped PATCH without committing the transaction."""
    validate_capability_user_context(owner_id=owner_id, current_user=current_user)
    supplied_fields = payload.model_fields_set
    hierarchy_requested = bool(supplied_fields & {"parent_capability_id", "status"})
    if hierarchy_requested:
        await _lock_owner_for_hierarchy(session, owner_id)

    capability = await _find_owner_capability(
        session,
        capability_id=capability_id,
        owner_id=owner_id,
        for_update=hierarchy_requested,
    )
    if capability is None:
        raise CapabilityNotFoundError(_CAPABILITY_NOT_FOUND)
    if not supplied_fields:
        raise CapabilityValidationError(_EMPTY_UPDATE_ERROR)

    update_values = payload.model_dump(exclude_unset=True)
    if "primary_flow_id" in supplied_fields and update_values["primary_flow_id"] is not None:
        update_values["primary_flow_id"] = await authorize_primary_flow_link(
            session,
            primary_flow_id=update_values["primary_flow_id"],
            owner_id=owner_id,
            current_user=current_user,
        )

    effective_state = {field_name: getattr(capability, field_name) for field_name in MUTABLE_CAPABILITY_FIELDS}
    effective_state.update(update_values)
    _validate_effective_frequency(effective_state)

    changed_values = {
        field_name: value for field_name, value in update_values.items() if getattr(capability, field_name) != value
    }
    if not changed_values:
        return capability

    parent_changed = "parent_capability_id" in changed_values
    status_changed = "status" in changed_values
    effective_status = effective_state["status"]
    proposed_parent_id = effective_state["parent_capability_id"]
    restoring = status_changed and _is_archived(capability.status) and _is_active(effective_status)
    archiving = status_changed and _is_active(capability.status) and _is_archived(effective_status)

    if (parent_changed or restoring) and proposed_parent_id is not None:
        await _validate_parent_chain(
            session,
            owner_id=owner_id,
            proposed_parent_id=proposed_parent_id,
            child_id=capability.id,
            child_status=effective_status,
        )
    if archiving:
        await _ensure_no_active_children(
            session,
            capability_id=capability.id,
            owner_id=owner_id,
        )

    previous_assessment = {field_name: getattr(capability, field_name) for field_name in ASSESSMENT_BEARING_FIELDS}
    effective_assessment = _assessment_state(effective_state)
    assessment_changed = previous_assessment != effective_assessment

    mutation_time = _utc_now()
    for field_name, value in changed_values.items():
        setattr(capability, field_name, value)

    if assessment_changed:
        if has_substantive_assessment_data(effective_assessment):
            capability.assessed_at = mutation_time
            capability.assessed_by = owner_id
        else:
            capability.assessed_at = None
            capability.assessed_by = None

    capability.updated_at = mutation_time
    session.add(capability)
    await session.flush()
    return capability


async def archive_capability(
    session: AsyncSession,
    *,
    capability_id: UUID,
    owner_id: UUID,
) -> Capability:
    """Archive an owner-scoped Capability through the normal update rules."""
    return await update_capability(
        session,
        capability_id=capability_id,
        owner_id=owner_id,
        payload=CapabilityUpdate(status=CapabilityStatus.ARCHIVED),
    )


async def restore_capability(
    session: AsyncSession,
    *,
    capability_id: UUID,
    owner_id: UUID,
) -> Capability:
    """Restore an owner-scoped Capability through the normal update rules."""
    return await update_capability(
        session,
        capability_id=capability_id,
        owner_id=owner_id,
        payload=CapabilityUpdate(status=CapabilityStatus.ACTIVE),
    )
