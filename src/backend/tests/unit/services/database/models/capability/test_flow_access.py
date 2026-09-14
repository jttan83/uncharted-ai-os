"""Security tests for Capability references to authorized Langflow Flows."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from langflow.services.authorization import fetch as authz_fetch
from langflow.services.authorization import flow_access as canonical_flow_access
from langflow.services.authorization.flow_access import FlowReadUnavailableError
from langflow.services.database.models.capability import crud as capability_crud
from langflow.services.database.models.capability import flow_access as capability_flow_access
from langflow.services.database.models.capability.crud import (
    CapabilityFlowNotAccessibleError,
    CapabilityNotFoundError,
    CapabilityValidationError,
    create_capability,
    update_capability,
)
from langflow.services.database.models.capability.flow_access import resolve_visible_primary_flow_id
from langflow.services.database.models.capability.model import Capability
from langflow.services.database.models.capability.schema import CapabilityCreate, CapabilityUpdate
from langflow.services.database.models.flow.model import Flow
from langflow.services.database.models.folder.model import Folder
from langflow.services.database.models.user.model import User
from sqlmodel import func, select

from tests.unit.services.authorization._common import (
    _StubAuthorizationService,
    install_audit_recorder,
    install_authz,
    install_settings,
)

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession


class _FlowReadAuthorizationService(_StubAuthorizationService):
    def __init__(self, *, allow: bool, supports_cross_user_fetch: bool) -> None:
        super().__init__(allow=allow)
        self._supports_cross_user_fetch = supports_cross_user_fetch

    async def supports_cross_user_fetch(self) -> bool:
        return self._supports_cross_user_fetch

    async def is_enabled(self) -> bool:
        return self._supports_cross_user_fetch


def _install_authorization(
    monkeypatch: pytest.MonkeyPatch,
    *,
    allow: bool,
    supports_cross_user_fetch: bool,
) -> _FlowReadAuthorizationService:
    service = _FlowReadAuthorizationService(
        allow=allow,
        supports_cross_user_fetch=supports_cross_user_fetch,
    )
    install_settings(monkeypatch, authz_enabled=True)
    install_authz(monkeypatch, service)
    monkeypatch.setattr(authz_fetch, "get_authorization_service", lambda: service)
    install_audit_recorder(monkeypatch)
    return service


async def _create_user(session: AsyncSession, *, username: str | None = None) -> User:
    user = User(
        username=username or f"capability-flow-user-{uuid4()}",
        password="not-a-real-password",  # noqa: S106
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_flow(
    session: AsyncSession,
    *,
    owner: User,
    folder: Folder | None = None,
    name: str = "Authorized Flow",
) -> Flow:
    flow = Flow(
        name=name,
        data={"nodes": [], "edges": []},
        user_id=owner.id,
        folder_id=folder.id if folder is not None else None,
        workspace_id=folder.workspace_id if folder is not None else None,
    )
    session.add(flow)
    await session.flush()
    return flow


async def _create_capability(
    session: AsyncSession,
    *,
    owner: User,
    current_user: User | None = None,
    name: str = "Proposal Builder",
    **values: Any,
) -> Capability:
    return await create_capability(
        session,
        owner_id=owner.id,
        current_user=current_user,
        payload=CapabilityCreate(name=name, functional_area="Clients", **values),
    )


async def _seed_capability(
    session: AsyncSession,
    *,
    owner: User,
    primary_flow_id: UUID | None = None,
    **values: Any,
) -> Capability:
    capability = Capability(
        name="Proposal Builder",
        functional_area="Clients",
        user_id=owner.id,
        primary_flow_id=primary_flow_id,
        **values,
    )
    session.add(capability)
    await session.flush()
    return capability


async def _capability_count(session: AsyncSession, owner_id: UUID) -> int:
    statement = select(func.count()).select_from(Capability).where(Capability.user_id == owner_id)
    return int((await session.exec(statement)).one())


async def test_ordinary_create_and_update_without_non_null_link_need_no_user_context_or_resolver(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    resolver = AsyncMock()
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)

    capability = await _create_capability(async_session, owner=owner)
    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(description="Client-facing proposal"),
    )
    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        payload=CapabilityUpdate(primary_flow_id=None),
    )

    assert capability.description == "Client-facing proposal"
    assert capability.primary_flow_id is None
    resolver.assert_not_awaited()


async def test_non_null_link_requires_authenticated_user_context(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    capability = await _create_capability(async_session, owner=owner)
    resolver = AsyncMock()
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)

    with pytest.raises(CapabilityValidationError, match="Authenticated user context is required"):
        await _create_capability(async_session, owner=owner, primary_flow_id=uuid4())
    with pytest.raises(CapabilityValidationError, match="Authenticated user context is required"):
        await update_capability(
            async_session,
            capability_id=capability.id,
            owner_id=owner.id,
            payload=CapabilityUpdate(primary_flow_id=uuid4()),
        )

    resolver.assert_not_awaited()


@pytest.mark.parametrize("link_value", [pytest.param("omitted", id="omitted"), pytest.param(None, id="null")])
async def test_mismatched_user_context_is_rejected_before_lookup_or_flow_authorization(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    link_value: str | None,
) -> None:
    owner = await _create_user(async_session)
    other_user = await _create_user(async_session)
    capability = await _create_capability(async_session, owner=owner)
    original_name = capability.name
    resolver = AsyncMock()
    find_capability = AsyncMock(wraps=capability_crud._find_owner_capability)
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)
    monkeypatch.setattr(capability_crud, "_find_owner_capability", find_capability)

    payload = CapabilityUpdate(name="Must not change")
    if link_value is None:
        payload = CapabilityUpdate(name="Must not change", primary_flow_id=None)
    with pytest.raises(CapabilityValidationError, match="does not match the Capability owner"):
        await update_capability(
            async_session,
            capability_id=capability.id,
            owner_id=owner.id,
            current_user=other_user,
            payload=payload,
        )

    assert capability.name == original_name
    find_capability.assert_not_awaited()
    resolver.assert_not_awaited()


async def test_mismatched_user_context_rejects_create_before_flow_authorization(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    other_user = await _create_user(async_session)
    resolver = AsyncMock()
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)

    with pytest.raises(CapabilityValidationError, match="does not match the Capability owner"):
        await _create_capability(
            async_session,
            owner=owner,
            current_user=other_user,
            primary_flow_id=uuid4(),
        )

    assert await _capability_count(async_session, owner.id) == 0
    resolver.assert_not_awaited()


async def test_create_links_an_owned_readable_flow_using_the_canonical_resolver(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    flow = await _create_flow(async_session, owner=owner)
    service = _install_authorization(monkeypatch, allow=False, supports_cross_user_fetch=False)

    capability = await _create_capability(
        async_session,
        owner=owner,
        current_user=owner,
        primary_flow_id=flow.id,
    )

    assert capability.primary_flow_id == flow.id
    assert service.calls == []  # Existing owner override authorizes without plugin enforcement.
    assert not hasattr(capability, "primary_flow_name")
    assert not hasattr(capability, "primary_flow_data")


async def test_create_links_a_plugin_authorized_shared_non_owned_flow_with_read_only(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requester = await _create_user(async_session)
    flow_owner = await _create_user(async_session)
    folder = Folder(name="Shared project", user_id=flow_owner.id, workspace_id=uuid4())
    async_session.add(folder)
    await async_session.flush()
    shared_flow = await _create_flow(async_session, owner=flow_owner, folder=folder, name="Shared Flow")
    service = _install_authorization(monkeypatch, allow=True, supports_cross_user_fetch=True)

    capability = await _create_capability(
        async_session,
        owner=requester,
        current_user=requester,
        primary_flow_id=shared_flow.id,
    )

    assert capability.user_id == requester.id
    assert capability.primary_flow_id == shared_flow.id
    assert len(service.calls) == 1
    assert service.calls[0]["act"] == "read"
    assert service.calls[0]["obj"] == f"flow:{shared_flow.id}"
    assert service.calls[0]["domain"] == f"project:{folder.id}"
    assert service.calls[0]["context"]["flow_user_id"] == flow_owner.id


async def test_missing_and_inaccessible_flow_create_are_masked_and_persist_nothing(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requester = await _create_user(async_session)
    flow_owner = await _create_user(async_session)
    inaccessible_flow = await _create_flow(async_session, owner=flow_owner)
    _install_authorization(monkeypatch, allow=False, supports_cross_user_fetch=True)

    errors = []
    for index, flow_id in enumerate((uuid4(), inaccessible_flow.id)):
        with pytest.raises(CapabilityFlowNotAccessibleError) as exc_info:
            await _create_capability(
                async_session,
                owner=requester,
                current_user=requester,
                name=f"Rejected {index}",
                primary_flow_id=flow_id,
            )
        errors.append(exc_info.value)

    assert [str(error) for error in errors] == ["Primary Flow is not accessible"] * 2
    assert await _capability_count(async_session, requester.id) == 0
    assert not any(isinstance(item, Capability) for item in async_session.new)


async def test_authenticated_user_object_is_passed_through_unchanged(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    flow = await _create_flow(async_session, owner=owner)
    resolver = AsyncMock(return_value=flow)
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)

    await _create_capability(
        async_session,
        owner=owner,
        current_user=owner,
        primary_flow_id=flow.id,
    )

    resolver.assert_awaited_once()
    assert resolver.await_args.kwargs["current_user"] is owner


async def test_update_links_owned_and_shared_readable_flows(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requester = await _create_user(async_session)
    flow_owner = await _create_user(async_session)
    owned_flow = await _create_flow(async_session, owner=requester, name="Owned Flow")
    shared_flow = await _create_flow(async_session, owner=flow_owner, name="Shared Flow")
    capability = await _create_capability(async_session, owner=requester)
    service = _install_authorization(monkeypatch, allow=True, supports_cross_user_fetch=True)

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=requester.id,
        current_user=requester,
        payload=CapabilityUpdate(primary_flow_id=owned_flow.id),
    )
    assert capability.primary_flow_id == owned_flow.id

    await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=requester.id,
        current_user=requester,
        payload=CapabilityUpdate(primary_flow_id=shared_flow.id),
    )
    assert capability.primary_flow_id == shared_flow.id
    assert [call["act"] for call in service.calls] == ["read"]
    assert all(call["act"] != "execute" for call in service.calls)


async def test_rejected_flow_update_masks_missing_and_inaccessible_and_preserves_entire_capability(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requester = await _create_user(async_session)
    flow_owner = await _create_user(async_session)
    old_flow = await _create_flow(async_session, owner=requester, name="Old Flow")
    inaccessible_flow = await _create_flow(async_session, owner=flow_owner, name="Private Flow")
    capability = await _seed_capability(
        async_session,
        owner=requester,
        primary_flow_id=old_flow.id,
        business_value=3,
        assessed_by=requester.id,
    )
    original = {
        "name": capability.name,
        "primary_flow_id": capability.primary_flow_id,
        "updated_at": capability.updated_at,
        "assessed_at": capability.assessed_at,
        "assessed_by": capability.assessed_by,
        "business_value": capability.business_value,
    }
    _install_authorization(monkeypatch, allow=False, supports_cross_user_fetch=True)

    errors = []
    for flow_id in (uuid4(), inaccessible_flow.id):
        with pytest.raises(CapabilityFlowNotAccessibleError) as exc_info:
            await update_capability(
                async_session,
                capability_id=capability.id,
                owner_id=requester.id,
                current_user=requester,
                payload=CapabilityUpdate(
                    name="Unauthorized mutation",
                    business_value=5,
                    primary_flow_id=flow_id,
                ),
            )
        errors.append(str(exc_info.value))

    assert errors == ["Primary Flow is not accessible"] * 2
    assert {field: getattr(capability, field) for field in original} == original
    assert capability not in async_session.dirty


async def test_omitted_link_survives_permission_loss_and_explicit_null_clears_without_authorization(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    flow = await _create_flow(async_session, owner=owner)
    capability = await _seed_capability(async_session, owner=owner, primary_flow_id=flow.id)
    resolver = AsyncMock(side_effect=FlowReadUnavailableError("Flow not found"))
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)

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
    resolver.assert_not_awaited()


async def test_explicit_same_readable_flow_is_authorized_before_no_op_without_flush(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    flow = await _create_flow(async_session, owner=owner)
    capability = await _seed_capability(async_session, owner=owner, primary_flow_id=flow.id)
    original_updated_at = capability.updated_at
    original_assessed_at = capability.assessed_at
    original_assessed_by = capability.assessed_by
    resolver = AsyncMock(return_value=flow)
    flush = AsyncMock(wraps=async_session.flush)
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)
    monkeypatch.setattr(async_session, "flush", flush)

    returned = await update_capability(
        async_session,
        capability_id=capability.id,
        owner_id=owner.id,
        current_user=owner,
        payload=CapabilityUpdate(primary_flow_id=flow.id),
    )

    assert returned is capability
    resolver.assert_awaited_once()
    flush.assert_not_awaited()
    assert capability.updated_at == original_updated_at
    assert capability.assessed_at == original_assessed_at
    assert capability.assessed_by == original_assessed_by
    assert capability not in async_session.dirty


async def test_explicit_same_inaccessible_flow_is_rejected_without_mutation(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    flow = await _create_flow(async_session, owner=owner)
    capability = await _seed_capability(async_session, owner=owner, primary_flow_id=flow.id)
    original_updated_at = capability.updated_at
    resolver = AsyncMock(side_effect=FlowReadUnavailableError("Flow not found"))
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)

    with pytest.raises(CapabilityFlowNotAccessibleError, match="Primary Flow is not accessible"):
        await update_capability(
            async_session,
            capability_id=capability.id,
            owner_id=owner.id,
            current_user=owner,
            payload=CapabilityUpdate(primary_flow_id=flow.id),
        )

    resolver.assert_awaited_once()
    assert capability.primary_flow_id == flow.id
    assert capability.updated_at == original_updated_at
    assert capability not in async_session.dirty


async def test_flow_readability_does_not_grant_access_to_another_users_capability(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capability_owner = await _create_user(async_session)
    shared_reader = await _create_user(async_session)
    shared_flow = await _create_flow(async_session, owner=capability_owner)
    capability = await _seed_capability(
        async_session,
        owner=capability_owner,
        primary_flow_id=shared_flow.id,
    )
    _install_authorization(monkeypatch, allow=True, supports_cross_user_fetch=True)
    assert (
        await canonical_flow_access.resolve_authorized_flow_for_read(
            async_session,
            flow_id=shared_flow.id,
            current_user=shared_reader,
        )
        is shared_flow
    )
    resolver = AsyncMock(wraps=capability_flow_access.resolve_authorized_flow_for_read)
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)

    with pytest.raises(CapabilityNotFoundError, match="Capability not found"):
        await update_capability(
            async_session,
            capability_id=capability.id,
            owner_id=shared_reader.id,
            current_user=shared_reader,
            payload=CapabilityUpdate(primary_flow_id=shared_flow.id),
        )

    resolver.assert_not_awaited()
    assert capability.user_id == capability_owner.id


async def test_visible_link_returns_owned_and_shared_readable_ids_using_read_permission(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requester = await _create_user(async_session)
    flow_owner = await _create_user(async_session)
    owned_flow = await _create_flow(async_session, owner=requester, name="Owned")
    shared_flow = await _create_flow(async_session, owner=flow_owner, name="Shared")
    service = _install_authorization(monkeypatch, allow=True, supports_cross_user_fetch=True)

    assert (
        await resolve_visible_primary_flow_id(
            async_session,
            primary_flow_id=owned_flow.id,
            current_user=requester,
        )
        == owned_flow.id
    )
    assert (
        await resolve_visible_primary_flow_id(
            async_session,
            primary_flow_id=shared_flow.id,
            current_user=requester,
        )
        == shared_flow.id
    )
    assert [call["act"] for call in service.calls] == ["read"]


async def test_visible_link_masks_missing_and_inaccessible_ids(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requester = await _create_user(async_session)
    flow_owner = await _create_user(async_session)
    inaccessible_flow = await _create_flow(async_session, owner=flow_owner)
    _install_authorization(monkeypatch, allow=False, supports_cross_user_fetch=True)

    assert (
        await resolve_visible_primary_flow_id(
            async_session,
            primary_flow_id=uuid4(),
            current_user=requester,
        )
        is None
    )
    assert (
        await resolve_visible_primary_flow_id(
            async_session,
            primary_flow_id=inaccessible_flow.id,
            current_user=requester,
        )
        is None
    )


async def test_null_visible_link_returns_without_resolver_call(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    resolver = AsyncMock()
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)

    assert (
        await resolve_visible_primary_flow_id(
            async_session,
            primary_flow_id=None,
            current_user=owner,
        )
        is None
    )
    resolver.assert_not_awaited()


async def test_visible_link_does_not_mutate_dirty_or_flush_capability(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    flow = await _create_flow(async_session, owner=owner)
    capability = await _seed_capability(
        async_session,
        owner=owner,
        primary_flow_id=flow.id,
        assessed_by=owner.id,
    )
    original = (
        capability.primary_flow_id,
        capability.updated_at,
        capability.assessed_at,
        capability.assessed_by,
    )
    resolver = AsyncMock(return_value=flow)
    flush = AsyncMock(wraps=async_session.flush)
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)
    monkeypatch.setattr(async_session, "flush", flush)

    visible = await resolve_visible_primary_flow_id(
        async_session,
        primary_flow_id=capability.primary_flow_id,
        current_user=owner,
    )

    assert isinstance(visible, UUID)
    assert visible == flow.id
    assert (
        capability.primary_flow_id,
        capability.updated_at,
        capability.assessed_at,
        capability.assessed_by,
    ) == original
    assert capability not in async_session.dirty
    flush.assert_not_awaited()


async def test_unexpected_authorization_failures_propagate_without_capability_mutation(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session)
    flow = await _create_flow(async_session, owner=owner)
    capability = await _seed_capability(async_session, owner=owner, primary_flow_id=flow.id)
    original_name = capability.name
    original_updated_at = capability.updated_at
    failure = RuntimeError("authorization infrastructure failed")
    resolver = AsyncMock(side_effect=failure)
    monkeypatch.setattr(capability_flow_access, "resolve_authorized_flow_for_read", resolver)

    with pytest.raises(RuntimeError, match="authorization infrastructure failed"):
        await _create_capability(
            async_session,
            owner=owner,
            current_user=owner,
            name="Rejected create",
            primary_flow_id=flow.id,
        )
    with pytest.raises(RuntimeError, match="authorization infrastructure failed"):
        await update_capability(
            async_session,
            capability_id=capability.id,
            owner_id=owner.id,
            current_user=owner,
            payload=CapabilityUpdate(name="Rejected update", primary_flow_id=flow.id),
        )
    with pytest.raises(RuntimeError, match="authorization infrastructure failed"):
        await resolve_visible_primary_flow_id(
            async_session,
            primary_flow_id=flow.id,
            current_user=owner,
        )

    assert capability.name == original_name
    assert capability.primary_flow_id == flow.id
    assert capability.updated_at == original_updated_at
    assert capability not in async_session.dirty
    assert await _capability_count(async_session, owner.id) == 1


def test_capability_flow_access_boundary_has_no_direct_fastapi_dependency() -> None:
    assert "fastapi" not in inspect.getsource(capability_flow_access).lower()
    assert "fastapi" not in inspect.getsource(capability_crud).lower()
    assert not hasattr(capability_crud, "CapabilityFlowLinkValidationRequiredError")
