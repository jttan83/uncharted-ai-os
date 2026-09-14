from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from langflow.services.database.models.capability import crud as capability_crud
from langflow.services.database.models.capability.constants import (
    CapabilityMaturity,
    CapabilityStatus,
    FrequencyPeriod,
    HumanOversight,
)
from langflow.services.database.models.capability.crud import (
    CapabilityHierarchyConflictError,
    CapabilityNotFoundError,
    CapabilityValidationError,
    ParentCapabilityNotFoundError,
    archive_capability,
    create_capability,
    get_capability,
    list_capabilities,
    restore_capability,
    update_capability,
)
from langflow.services.database.models.capability.model import Capability
from langflow.services.database.models.capability.schema import CapabilityCreate, CapabilityUpdate
from langflow.services.database.models.flow.model import Flow
from langflow.services.database.models.user.model import User
from sqlalchemy.dialects import postgresql, sqlite
from sqlmodel import func, select

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession


async def _create_user(session: AsyncSession, *, username: str | None = None) -> User:
    user = User(
        username=username or f"capability-owner-{uuid4()}",
        password="not-a-real-password",  # noqa: S106
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _create(
    session: AsyncSession,
    owner: User,
    *,
    name: str = "Capability",
    functional_area: str = "Operations",
    **values: Any,
) -> Capability:
    return await create_capability(
        session,
        owner_id=owner.id,
        payload=CapabilityCreate(
            name=name,
            functional_area=functional_area,
            **values,
        ),
    )


async def _seed(
    session: AsyncSession,
    owner: User,
    *,
    name: str = "Capability",
    functional_area: str = "Operations",
    **values: Any,
) -> Capability:
    capability = Capability(
        name=name,
        functional_area=functional_area,
        user_id=owner.id,
        **values,
    )
    session.add(capability)
    await session.flush()
    return capability


def _assert_aware_utc(value: datetime) -> None:
    assert value.tzinfo is not None
    assert value.utcoffset() == timedelta(0)


async def test_get_is_owner_scoped_and_masks_another_owner_as_missing(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    other_owner = await _create_user(async_session)
    capability = await _create(async_session, owner)

    assert await get_capability(async_session, capability_id=capability.id, owner_id=owner.id) is capability

    errors = []
    for capability_id in (capability.id, uuid4()):
        with pytest.raises(CapabilityNotFoundError) as exc_info:
            await get_capability(async_session, capability_id=capability_id, owner_id=other_owner.id)
        errors.append(str(exc_info.value))
    assert errors == ["Capability not found", "Capability not found"]


async def test_list_is_owner_scoped_filters_archived_and_returns_total_before_pagination(
    async_session: AsyncSession,
) -> None:
    owner = await _create_user(async_session)
    other_owner = await _create_user(async_session)
    first_id = UUID("00000000-0000-0000-0000-000000000001")
    second_id = UUID("00000000-0000-0000-0000-000000000002")
    await _seed(async_session, owner, id=second_id, name="Same", functional_area="Clients")
    await _seed(async_session, owner, id=first_id, name="Same", functional_area="Clients")
    zulu = await _seed(async_session, owner, name="Zulu", functional_area="Clients")
    alpha = await _seed(async_session, owner, name="Alpha", functional_area="Research")
    archived = await _seed(
        async_session,
        owner,
        name="Archived",
        functional_area="Clients",
        status=CapabilityStatus.ARCHIVED,
    )
    await _seed(async_session, other_owner, name="Foreign", functional_area="Clients")

    page, total = await list_capabilities(async_session, owner_id=owner.id, offset=1, limit=2)
    assert total == 4
    assert [item.id for item in page] == [second_id, zulu.id]
    assert [item.name for item in page] == ["Same", "Zulu"]

    all_rows, all_total = await list_capabilities(async_session, owner_id=owner.id, include_archived=True)
    assert all_total == 5
    assert [item.id for item in all_rows] == [archived.id, first_id, second_id, zulu.id, alpha.id]
    assert [item.name for item in all_rows] == ["Archived", "Same", "Same", "Zulu", "Alpha"]
    assert all(item.user_id == owner.id for item in all_rows)


@pytest.mark.parametrize(
    ("offset", "limit"),
    [(-1, 1), (0, 0), (0, 201)],
)
async def test_list_rejects_unsafe_pagination(async_session: AsyncSession, offset: int, limit: int) -> None:
    owner = await _create_user(async_session)

    with pytest.raises(CapabilityValidationError):
        await list_capabilities(async_session, owner_id=owner.id, offset=offset, limit=limit)


async def test_create_assigns_server_fields_and_default_unassessed_state(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    before = datetime.now(timezone.utc)

    capability = await _create(async_session, owner)

    assert capability.user_id == owner.id
    assert capability.workspace_id is None
    assert capability.status == CapabilityStatus.ACTIVE
    assert capability.current_maturity == CapabilityMaturity.NOT_ASSESSED
    assert capability.inputs == []
    assert capability.outputs == []
    assert capability.tools == []
    assert capability.assessed_at is None
    assert capability.assessed_by is None
    assert capability.created_at >= before
    assert capability.updated_at >= before
    _assert_aware_utc(capability.created_at)
    _assert_aware_utc(capability.updated_at)


async def test_create_stamps_substantive_assessment(
    async_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await _create_user(async_session)
    assessment_time = datetime(2030, 1, 2, 3, 4, tzinfo=timezone.utc)
    monkeypatch.setattr(capability_crud, "_utc_now", lambda: assessment_time)

    capability = await _create(async_session, owner, business_value=4)

    assert capability.assessed_at == assessment_time
    assert capability.assessed_by == owner.id
    _assert_aware_utc(capability.assessed_at)


async def test_create_validates_owner_scoped_parent_without_using_functional_area(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    parent = await _create(async_session, owner, functional_area="Clients")

    child = await _create(
        async_session,
        owner,
        name="Child",
        functional_area="Research",
        parent_capability_id=parent.id,
    )

    assert child.parent_capability_id == parent.id


async def test_create_masks_other_owner_parent_as_missing(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    other_owner = await _create_user(async_session)
    foreign_parent = await _create(async_session, other_owner)

    errors = []
    for parent_id in (foreign_parent.id, uuid4()):
        with pytest.raises(ParentCapabilityNotFoundError) as exc_info:
            await _create(async_session, owner, parent_capability_id=parent_id)
        errors.append(str(exc_info.value))
    assert errors == ["Parent Capability not found", "Parent Capability not found"]


async def test_active_create_under_archived_parent_fails_but_archived_create_succeeds(
    async_session: AsyncSession,
) -> None:
    owner = await _create_user(async_session)
    parent = await _create(async_session, owner, status=CapabilityStatus.ARCHIVED)

    with pytest.raises(CapabilityHierarchyConflictError, match="archived parent"):
        await _create(async_session, owner, name="Active child", parent_capability_id=parent.id)

    child = await _create(
        async_session,
        owner,
        name="Archived child",
        parent_capability_id=parent.id,
        status=CapabilityStatus.ARCHIVED,
    )
    assert child.parent_capability_id == parent.id
    assert child.status == CapabilityStatus.ARCHIVED


async def test_create_allows_null_flow_link_and_requires_context_for_non_null_flow_link(
    async_session: AsyncSession,
) -> None:
    owner = await _create_user(async_session)

    assert (await _create(async_session, owner, primary_flow_id=None)).primary_flow_id is None
    with pytest.raises(CapabilityValidationError, match="Authenticated user context is required"):
        await _create(async_session, owner, name="Linked", primary_flow_id=uuid4())


async def test_update_reparents_and_explicit_null_clears_parent(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    first_parent = await _create(async_session, owner, name="First parent")
    second_parent = await _create(async_session, owner, name="Second parent")
    child = await _create(async_session, owner, name="Child", parent_capability_id=first_parent.id)

    await update_capability(
        async_session,
        capability_id=child.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(parent_capability_id=second_parent.id),
    )
    assert child.parent_capability_id == second_parent.id

    await update_capability(
        async_session,
        capability_id=child.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(parent_capability_id=None),
    )
    assert child.parent_capability_id is None


async def test_update_rejects_self_parent_as_validation_error(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    capability = await _create(async_session, owner)

    with pytest.raises(CapabilityValidationError, match="cannot parent itself"):
        await update_capability(
            async_session,
            capability_id=capability.id,
            owner_id=owner.id,
            payload=CapabilityUpdate(parent_capability_id=capability.id),
        )


async def test_update_rejects_deep_cycle(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    root = await _create(async_session, owner, name="Root")
    child = await _create(async_session, owner, name="Child", parent_capability_id=root.id)
    grandchild = await _create(async_session, owner, name="Grandchild", parent_capability_id=child.id)

    with pytest.raises(CapabilityHierarchyConflictError, match="cycle"):
        await update_capability(
            async_session,
            capability_id=root.id,
            owner_id=owner.id,
            payload=CapabilityUpdate(parent_capability_id=grandchild.id),
        )


async def test_deep_valid_hierarchy_has_no_artificial_depth_limit(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    parent_id = None
    for index in range(150):
        ancestor = Capability(
            name=f"Ancestor {index:03d}",
            functional_area="Operations",
            user_id=owner.id,
            parent_capability_id=parent_id,
        )
        async_session.add(ancestor)
        parent_id = ancestor.id
    await async_session.flush()

    leaf = await _create(async_session, owner, name="Deep leaf", parent_capability_id=parent_id)
    assert leaf.parent_capability_id == parent_id


async def test_update_masks_other_owner_parent_as_missing(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    other_owner = await _create_user(async_session)
    child = await _create(async_session, owner)
    foreign_parent = await _create(async_session, other_owner)

    with pytest.raises(ParentCapabilityNotFoundError, match="Parent Capability not found"):
        await update_capability(
            async_session,
            capability_id=child.id,
            owner_id=owner.id,
            payload=CapabilityUpdate(parent_capability_id=foreign_parent.id),
        )


async def test_active_reparent_and_restore_under_archived_parent_are_rejected(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    archived_parent = await _create(async_session, owner, name="Parent", status=CapabilityStatus.ARCHIVED)
    active_child = await _create(async_session, owner, name="Active child")
    archived_child = await _create(
        async_session,
        owner,
        name="Archived child",
        status=CapabilityStatus.ARCHIVED,
        parent_capability_id=archived_parent.id,
    )

    with pytest.raises(CapabilityHierarchyConflictError, match="archived parent"):
        await update_capability(
            async_session,
            capability_id=active_child.id,
            owner_id=owner.id,
            payload=CapabilityUpdate(parent_capability_id=archived_parent.id),
        )
    with pytest.raises(CapabilityHierarchyConflictError, match="archived parent"):
        await restore_capability(async_session, capability_id=archived_child.id, owner_id=owner.id)


async def test_archive_leaf_and_restore_with_active_parent_succeed(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    parent = await _create(async_session, owner, name="Parent")
    child = await _create(async_session, owner, name="Child", parent_capability_id=parent.id)

    assert (await archive_capability(async_session, capability_id=child.id, owner_id=owner.id)).status == (
        CapabilityStatus.ARCHIVED
    )
    assert child.parent_capability_id == parent.id
    assert (await restore_capability(async_session, capability_id=child.id, owner_id=owner.id)).status == (
        CapabilityStatus.ACTIVE
    )
    assert child.parent_capability_id == parent.id


async def test_archive_with_active_direct_child_fails_without_cascade_or_link_changes(
    async_session: AsyncSession,
) -> None:
    owner = await _create_user(async_session)
    parent = await _create(async_session, owner, name="Parent")
    child = await _create(async_session, owner, name="Child", parent_capability_id=parent.id)

    with pytest.raises(CapabilityHierarchyConflictError, match="active children"):
        await archive_capability(async_session, capability_id=parent.id, owner_id=owner.id)

    assert parent.status == CapabilityStatus.ACTIVE
    assert child.status == CapabilityStatus.ACTIVE
    assert child.parent_capability_id == parent.id


async def test_archived_child_does_not_block_parent_archive_and_archive_does_not_cascade(
    async_session: AsyncSession,
) -> None:
    owner = await _create_user(async_session)
    parent = await _create(async_session, owner, name="Parent")
    child = await _create(
        async_session,
        owner,
        name="Child",
        parent_capability_id=parent.id,
        status=CapabilityStatus.ARCHIVED,
    )
    child_updated_at = child.updated_at

    await archive_capability(async_session, capability_id=parent.id, owner_id=owner.id)

    assert parent.status == CapabilityStatus.ARCHIVED
    assert child.status == CapabilityStatus.ARCHIVED
    assert child.parent_capability_id == parent.id
    assert child.updated_at == child_updated_at


async def test_patch_omission_preserves_fields_and_explicit_null_clears_nullable_field(
    async_session: AsyncSession,
) -> None:
    owner = await _create_user(async_session)
    capability = await _create(
        async_session,
        owner,
        description="Original description",
        oversight_notes="Keep this",
    )

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(description=None),
    )

    assert capability.description is None
    assert capability.oversight_notes == "Keep this"


async def test_empty_patch_is_rejected_by_crud(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    capability = await _create(async_session, owner)

    with pytest.raises(CapabilityValidationError, match="at least one field"):
        await update_capability(
            async_session,
            capability_id=capability.id,
            owner_id=owner.id,
            payload=CapabilityUpdate(),
        )


async def test_update_is_owner_scoped_and_does_not_mutate_another_owners_row(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    other_owner = await _create_user(async_session)
    capability = await _create(async_session, owner, name="Private capability")

    with pytest.raises(CapabilityNotFoundError, match="Capability not found"):
        await update_capability(
            async_session,
            capability_id=capability.id,
            owner_id=other_owner.id,
            payload=CapabilityUpdate(name="Unauthorized change"),
        )

    assert capability.name == "Private capability"


async def test_frequency_patch_merges_with_stored_effective_state(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    capability = await _create(
        async_session,
        owner,
        frequency_period=FrequencyPeriod.WEEK,
        frequency_value=2,
    )

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(frequency_value=3),
    )
    assert capability.frequency_period == FrequencyPeriod.WEEK
    assert capability.frequency_value == 3

    with pytest.raises(CapabilityValidationError, match="must be null"):
        await update_capability(
            async_session,
            capability_id=capability.id,
            owner_id=owner.id,
            payload=CapabilityUpdate(frequency_period=FrequencyPeriod.AD_HOC),
        )

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(frequency_period=FrequencyPeriod.AD_HOC, frequency_value=None),
    )
    assert capability.frequency_period == FrequencyPeriod.AD_HOC
    assert capability.frequency_value is None

    with pytest.raises(CapabilityValidationError, match="is required"):
        await update_capability(
            async_session,
            capability_id=capability.id,
            owner_id=owner.id,
            payload=CapabilityUpdate(frequency_period=FrequencyPeriod.WEEK),
        )


async def test_normalized_text_and_array_no_ops_preserve_updated_at(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    capability = await _create(
        async_session,
        owner,
        name="Existing name",
        inputs=["Client brief", "Discovery notes"],
    )
    original_updated_at = capability.updated_at

    returned = await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(
            name="  Existing name  ",
            inputs=[" Client brief ", "Discovery notes", "Client brief"],
        ),
    )

    assert returned is capability
    assert capability.updated_at == original_updated_at
    assert capability not in async_session.dirty


async def test_actual_update_sets_utc_updated_at(async_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await _create_user(async_session)
    capability = await _create(async_session, owner)
    mutation_time = datetime(2031, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(capability_crud, "_utc_now", lambda: mutation_time)

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(name="Changed"),
    )

    assert capability.updated_at == mutation_time
    _assert_aware_utc(capability.updated_at)


async def test_non_assessment_update_preserves_existing_provenance(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    capability = await _create(async_session, owner, business_value=3)
    original_assessed_at = capability.assessed_at
    original_assessed_by = capability.assessed_by

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(name="Renamed"),
    )

    assert capability.assessed_at == original_assessed_at
    assert capability.assessed_by == original_assessed_by


async def test_new_and_changed_assessment_data_stamps_provenance(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    capability = await _create(async_session, owner)
    first_stamp = datetime(2032, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(capability_crud, "_utc_now", lambda: first_stamp)

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(current_maturity=CapabilityMaturity.MANUAL),
    )
    assert capability.assessed_at == first_stamp
    assert capability.assessed_by == owner.id

    second_stamp = datetime(2032, 2, 2, tzinfo=timezone.utc)
    monkeypatch.setattr(capability_crud, "_utc_now", lambda: second_stamp)
    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(current_maturity=CapabilityMaturity.AI_ASSISTED),
    )
    assert capability.assessed_at == second_stamp
    assert capability.assessed_by == owner.id


async def test_no_op_assessment_patch_does_not_restamp(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    capability = await _create(async_session, owner, current_maturity=CapabilityMaturity.MANUAL)
    assessed_at = capability.assessed_at
    updated_at = capability.updated_at

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(current_maturity=CapabilityMaturity.MANUAL),
    )

    assert capability.assessed_at == assessed_at
    assert capability.assessed_by == owner.id
    assert capability.updated_at == updated_at


async def test_reset_to_unassessed_clears_provenance(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    capability = await _create(
        async_session,
        owner,
        current_maturity=CapabilityMaturity.AI_ASSISTED,
        target_maturity=CapabilityMaturity.AI_EXECUTABLE,
        human_oversight=HumanOversight.REVIEW_RECOMMENDED,
        oversight_notes="Review important claims",
        business_value=4,
        ai_feasibility=4,
        ai_execution_risk=3,
        assessment_notes="Initial evidence",
    )

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(
            current_maturity=CapabilityMaturity.NOT_ASSESSED,
            target_maturity=None,
            human_oversight=None,
            oversight_notes=None,
            business_value=None,
            ai_feasibility=None,
            ai_execution_risk=None,
            assessment_notes=None,
        ),
    )

    assert capability.assessed_at is None
    assert capability.assessed_by is None


async def test_work_economics_only_update_does_not_stamp_assessment(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    capability = await _create(async_session, owner)

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(baseline_human_effort_minutes_per_run=180),
    )

    assert capability.assessed_at is None
    assert capability.assessed_by is None


async def test_flow_link_patch_boundary_preserves_omitted_link_allows_clear_and_requires_context_for_non_null(
    async_session: AsyncSession,
) -> None:
    owner = await _create_user(async_session)
    flow = Flow(name="Existing flow", user_id=owner.id, data={"nodes": [], "edges": []})
    async_session.add(flow)
    await async_session.flush()
    capability = await _seed(async_session, owner, primary_flow_id=flow.id)

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(description="Unrelated change"),
    )
    assert capability.primary_flow_id == flow.id

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(primary_flow_id=None),
    )
    assert capability.primary_flow_id is None

    with pytest.raises(CapabilityValidationError, match="Authenticated user context is required"):
        await update_capability(
            async_session,
            capability_id=capability.id,
            owner_id=owner.id,
            payload=CapabilityUpdate(primary_flow_id=uuid4()),
        )


async def test_create_is_flushed_but_caller_rollback_removes_it(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    await async_session.commit()

    capability = await _create(async_session, owner)
    assert (
        await async_session.exec(select(func.count()).select_from(Capability).where(Capability.id == capability.id))
    ).one() == 1

    await async_session.rollback()
    assert (
        await async_session.exec(select(func.count()).select_from(Capability).where(Capability.id == capability.id))
    ).one() == 0


async def test_update_is_flushed_but_caller_rollback_restores_previous_value(async_session: AsyncSession) -> None:
    owner = await _create_user(async_session)
    capability = await _create(async_session, owner, name="Before")
    capability_id = capability.id
    await async_session.commit()

    await update_capability(
        async_session,
        capability_id=capability_id,
        owner_id=owner.id,
        payload=CapabilityUpdate(name="After"),
    )
    assert (await async_session.exec(select(Capability.name).where(Capability.id == capability_id))).one() == "After"

    await async_session.rollback()
    assert (await async_session.exec(select(Capability.name).where(Capability.id == capability_id))).one() == "Before"


def test_owner_lock_compiles_for_postgresql_but_not_as_a_fake_sqlite_row_lock() -> None:
    statement = capability_crud._owner_lock_statement(uuid4())

    assert "FOR UPDATE" in str(statement.compile(dialect=postgresql.dialect())).upper()
    assert "FOR UPDATE" not in str(statement.compile(dialect=sqlite.dialect())).upper()


async def test_parent_create_uses_owner_serialization_path(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    parent = await _create(async_session, owner, name="Parent")
    lock_spy = AsyncMock(wraps=capability_crud._lock_owner_for_hierarchy)
    monkeypatch.setattr(capability_crud, "_lock_owner_for_hierarchy", lock_spy)

    await _create(async_session, owner, name="Child", parent_capability_id=parent.id)

    lock_spy.assert_awaited_once_with(async_session, owner.id)


def test_crud_defines_no_hard_delete_helper() -> None:
    assert not hasattr(capability_crud, "delete_capability")
