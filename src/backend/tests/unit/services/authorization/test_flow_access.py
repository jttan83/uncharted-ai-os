"""Behavioral tests for transport-neutral Flow READ resolution."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from langflow.api.v1 import authz_route_dependencies, flows_helpers
from langflow.services.authorization import fetch as authz_fetch
from langflow.services.authorization import flow_access
from langflow.services.authorization.flow_access import FlowReadUnavailableError
from langflow.services.database.models.flow.model import Flow
from langflow.services.database.models.folder.model import Folder
from langflow.services.database.models.user.model import User

from ._common import (
    _StubAuthorizationService,
    install_audit_recorder,
    install_authz,
    install_settings,
)


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
    service: _FlowReadAuthorizationService,
    *,
    authz_enabled: bool,
) -> list[dict]:
    install_settings(monkeypatch, authz_enabled=authz_enabled)
    install_authz(monkeypatch, service)
    monkeypatch.setattr(authz_fetch, "get_authorization_service", lambda: service)
    return install_audit_recorder(monkeypatch)


async def _create_user(session, *, username: str) -> User:
    user = User(username=username, password="not-a-real-password", is_active=True)  # noqa: S106
    session.add(user)
    await session.flush()
    return user


async def _create_flow(session, *, owner: User, folder: Folder | None = None) -> Flow:
    flow = Flow(
        name=f"Flow {uuid4()}",
        data={"nodes": [], "edges": []},
        user_id=owner.id,
        folder_id=folder.id if folder is not None else None,
        workspace_id=folder.workspace_id if folder is not None else None,
    )
    session.add(flow)
    await session.flush()
    return flow


async def test_resolver_returns_an_owned_flow_and_preserves_owner_override(
    async_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _create_user(async_session, username=f"flow-owner-{uuid4()}")
    flow = await _create_flow(async_session, owner=owner)
    service = _FlowReadAuthorizationService(allow=False, supports_cross_user_fetch=False)
    audit_calls = _install_authorization(monkeypatch, service, authz_enabled=True)

    resolved = await flow_access.resolve_authorized_flow_for_read(
        async_session,
        flow_id=flow.id,
        current_user=owner,
    )

    assert resolved is flow
    assert service.calls == []
    assert [call["result"] for call in audit_calls] == ["owner_override"]


async def test_resolver_masks_missing_and_forbidden_flows_with_the_same_service_error(
    async_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requester = await _create_user(async_session, username=f"flow-requester-{uuid4()}")
    other_owner = await _create_user(async_session, username=f"other-flow-owner-{uuid4()}")
    forbidden_flow = await _create_flow(async_session, owner=other_owner)
    service = _FlowReadAuthorizationService(allow=False, supports_cross_user_fetch=True)
    _install_authorization(monkeypatch, service, authz_enabled=True)

    errors = []
    for flow_id in (uuid4(), forbidden_flow.id):
        with pytest.raises(FlowReadUnavailableError) as exc_info:
            await flow_access.resolve_authorized_flow_for_read(
                async_session,
                flow_id=flow_id,
                current_user=requester,
            )
        errors.append(exc_info.value)

    assert [str(error) for error in errors] == ["Flow not found", "Flow not found"]
    assert all(not isinstance(error, HTTPException) for error in errors)


async def test_resolver_allows_a_plugin_authorized_cross_user_flow_and_enforces_read(
    async_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requester = await _create_user(async_session, username=f"shared-flow-reader-{uuid4()}")
    other_owner = await _create_user(async_session, username=f"shared-flow-owner-{uuid4()}")
    workspace_id = uuid4()
    folder = Folder(
        name=f"Shared project {uuid4()}",
        user_id=other_owner.id,
        workspace_id=workspace_id,
    )
    async_session.add(folder)
    await async_session.flush()
    shared_flow = await _create_flow(async_session, owner=other_owner, folder=folder)
    service = _FlowReadAuthorizationService(allow=True, supports_cross_user_fetch=True)
    _install_authorization(monkeypatch, service, authz_enabled=True)

    resolved = await flow_access.resolve_authorized_flow_for_read(
        async_session,
        flow_id=shared_flow.id,
        current_user=requester,
    )

    assert resolved is shared_flow
    assert len(service.calls) == 1
    assert service.calls[0]["act"] == "read"
    assert service.calls[0]["obj"] == f"flow:{shared_flow.id}"
    assert service.calls[0]["domain"] == f"project:{folder.id}"
    assert service.calls[0]["context"]["flow_user_id"] == other_owner.id
    assert service.calls[0]["context"]["workspace_id"] == workspace_id
    assert service.calls[0]["context"]["folder_id"] == folder.id


async def test_resolver_passes_the_full_user_and_flow_scope_to_the_existing_guard(monkeypatch) -> None:
    requester = SimpleNamespace(id=uuid4(), is_superuser=True)
    flow = Flow(
        name="Scoped Flow",
        user_id=uuid4(),
        workspace_id=uuid4(),
        folder_id=uuid4(),
        data={"nodes": [], "edges": []},
    )
    load_flow = AsyncMock(return_value=flow)
    guard = AsyncMock()
    monkeypatch.setattr(flow_access, "load_flow_for_authorization", load_flow)
    monkeypatch.setattr(flow_access, "ensure_flow_permission", guard)

    assert (
        await flow_access.resolve_authorized_flow_for_read(
            object(),
            flow_id=flow.id,
            current_user=requester,
        )
        is flow
    )
    guard.assert_awaited_once_with(
        requester,
        flow_access.FlowAction.READ,
        flow_id=flow.id,
        flow_user_id=flow.user_id,
        workspace_id=flow.workspace_id,
        folder_id=flow.folder_id,
    )


async def test_resolver_translates_guard_http_denial_but_propagates_non_transport_failures(monkeypatch) -> None:
    requester = SimpleNamespace(id=uuid4(), is_superuser=False)
    flow = Flow(name="Private Flow", user_id=uuid4(), data={"nodes": [], "edges": []})
    monkeypatch.setattr(flow_access, "load_flow_for_authorization", AsyncMock(return_value=flow))
    monkeypatch.setattr(
        flow_access,
        "ensure_flow_permission",
        AsyncMock(side_effect=HTTPException(status_code=403, detail="Permission denied")),
    )

    with pytest.raises(FlowReadUnavailableError, match="Flow not found"):
        await flow_access.resolve_authorized_flow_for_read(
            object(),
            flow_id=flow.id,
            current_user=requester,
        )

    failure = RuntimeError("authorization infrastructure failed")
    monkeypatch.setattr(flow_access, "ensure_flow_permission", AsyncMock(side_effect=failure))
    with pytest.raises(RuntimeError, match="authorization infrastructure failed"):
        await flow_access.resolve_authorized_flow_for_read(
            object(),
            flow_id=flow.id,
            current_user=requester,
        )


async def test_fastapi_read_dependency_is_a_thin_success_and_404_adapter(monkeypatch) -> None:
    requester = SimpleNamespace(id=uuid4(), is_superuser=False)
    session = object()
    flow = Flow(name="Readable Flow", user_id=requester.id, data={"nodes": [], "edges": []})
    resolver = AsyncMock(return_value=flow)
    monkeypatch.setattr(authz_route_dependencies, "resolve_authorized_flow_for_read", resolver)

    assert (
        await authz_route_dependencies.get_authorized_flow_for_read(
            flow.id,
            requester,
            session,
        )
        is flow
    )
    resolver.assert_awaited_once_with(session, flow_id=flow.id, current_user=requester)

    resolver.reset_mock(side_effect=True)
    resolver.side_effect = FlowReadUnavailableError("Flow not found")
    with pytest.raises(HTTPException) as exc_info:
        await authz_route_dependencies.get_authorized_flow_for_read(
            flow.id,
            requester,
            session,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Flow not found"


async def test_existing_read_flow_helper_delegates_to_the_canonical_service_fetch(monkeypatch) -> None:
    session = object()
    flow = Flow(name="Readable Flow", user_id=uuid4(), data={"nodes": [], "edges": []})
    load_flow = AsyncMock(return_value=flow)
    monkeypatch.setattr(flow_access, "load_flow_for_authorization", load_flow)

    assert await flows_helpers._read_flow(session, flow.id, flow.user_id, for_update=True) is flow
    load_flow.assert_awaited_once_with(
        session,
        flow_id=flow.id,
        user_id=flow.user_id,
        for_update=True,
    )
