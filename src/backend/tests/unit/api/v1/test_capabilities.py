"""API and security tests for the owner-scoped Capability resource."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import status
from langflow.api.v1 import capabilities as capabilities_api
from langflow.services.auth.utils import get_password_hash
from langflow.services.authorization import fetch as authz_fetch
from langflow.services.authorization.flow_access import FlowReadUnavailableError
from langflow.services.database.models.capability.constants import CapabilityStatus
from langflow.services.database.models.capability.model import Capability
from langflow.services.database.models.capability.schema import CapabilityRead, CapabilitySummary
from langflow.services.database.models.flow.model import Flow
from langflow.services.database.models.user.model import User
from langflow.services.deps import session_scope
from sqlmodel import func, select

from tests.unit.services.authorization._common import (
    _StubAuthorizationService,
    install_audit_recorder,
    install_authz,
    install_settings,
)

if TYPE_CHECKING:
    from httpx import AsyncClient

CAPABILITIES_PATH = "/api/v1/capabilities"


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


async def _create_user_and_headers(client: AsyncClient, *, username: str) -> tuple[UUID, dict[str, str]]:
    password = "test-password"  # noqa: S105
    async with session_scope() as session:
        user = User(
            username=username,
            password=get_password_hash(password),
            is_active=True,
            is_superuser=False,
        )
        session.add(user)
        await session.flush()
        user_id = user.id

    response = await client.post("/api/v1/login", data={"username": username, "password": password})
    assert response.status_code == status.HTTP_200_OK
    return user_id, {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_flow(*, owner_id: UUID, name: str) -> UUID:
    async with session_scope() as session:
        flow = Flow(
            name=name,
            data={"nodes": [], "edges": []},
            user_id=owner_id,
        )
        session.add(flow)
        await session.flush()
        return flow.id


async def _seed_capability(
    *,
    owner_id: UUID,
    name: str = "Seeded Capability",
    functional_area: str = "Operations",
    primary_flow_id: UUID | None = None,
    status_value: CapabilityStatus = CapabilityStatus.ACTIVE,
    workspace_id: UUID | None = None,
) -> tuple[UUID, datetime]:
    async with session_scope() as session:
        capability = Capability(
            name=name,
            functional_area=functional_area,
            user_id=owner_id,
            workspace_id=workspace_id,
            status=status_value,
            primary_flow_id=primary_flow_id,
        )
        session.add(capability)
        await session.flush()
        return capability.id, capability.updated_at


async def _read_capability(capability_id: UUID) -> Capability:
    async with session_scope() as session:
        capability = await session.get(Capability, capability_id)
        assert capability is not None
        session.expunge(capability)
        return capability


async def _capability_count(*, owner_id: UUID, name_prefix: str | None = None) -> int:
    async with session_scope() as session:
        statement = select(func.count()).select_from(Capability).where(Capability.user_id == owner_id)
        if name_prefix is not None:
            statement = statement.where(Capability.name.startswith(name_prefix))
        return int((await session.exec(statement)).one())


async def test_all_routes_require_authentication_and_delete_is_absent(client: AsyncClient) -> None:
    capability_id = uuid4()
    requests = (
        await client.get(CAPABILITIES_PATH),
        await client.get(f"{CAPABILITIES_PATH}/{capability_id}"),
        await client.post(CAPABILITIES_PATH, json={"name": "Proposal", "functional_area": "Clients"}),
        await client.patch(f"{CAPABILITIES_PATH}/{capability_id}", json={"name": "Proposal"}),
    )

    assert [response.status_code for response in requests] == [status.HTTP_403_FORBIDDEN] * 4


async def test_create_get_and_no_link_response_contract(
    client: AsyncClient,
    logged_in_headers: dict[str, str],
    active_user,
) -> None:
    response = await client.post(
        CAPABILITIES_PATH,
        headers=logged_in_headers,
        json={"name": " Proposal Builder ", "functional_area": " Clients "},
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert set(body) == set(CapabilityRead.model_fields)
    assert body["name"] == "Proposal Builder"
    assert body["functional_area"] == "Clients"
    assert body["user_id"] == str(active_user.id)
    assert body["workspace_id"] is None
    assert body["status"] == "active"
    assert body["current_maturity"] == "not_assessed"
    assert body["inputs"] == body["outputs"] == body["tools"] == []
    assert body["assessed_at"] is None
    assert body["assessed_by"] is None
    assert body["primary_flow_id"] is None
    assert body["primary_flow_link"] == {"status": "not_linked", "flow": None}

    read_response = await client.get(f"{CAPABILITIES_PATH}/{body['id']}", headers=logged_in_headers)
    assert read_response.status_code == status.HTTP_200_OK
    assert read_response.json() == body

    forbidden_server_field = await client.post(
        CAPABILITIES_PATH,
        headers=logged_in_headers,
        json={
            "name": "Injected owner",
            "functional_area": "Clients",
            "user_id": str(uuid4()),
            "workspace_id": str(uuid4()),
        },
    )
    assert forbidden_server_field.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    delete_response = await client.delete(f"{CAPABILITIES_PATH}/{body['id']}", headers=logged_in_headers)
    assert delete_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


async def test_owner_isolation_and_list_contract(
    client: AsyncClient,
    logged_in_headers: dict[str, str],
    active_user,
) -> None:
    other_id, other_headers = await _create_user_and_headers(client, username=f"capability-other-{uuid4()}")
    other_response = await client.post(
        CAPABILITIES_PATH,
        headers=other_headers,
        json={"name": "Foreign", "functional_area": "Clients"},
    )
    assert other_response.status_code == status.HTTP_201_CREATED
    foreign_id = other_response.json()["id"]

    create_payloads = (
        {"name": "Zulu", "functional_area": "Clients"},
        {"name": "Alpha", "functional_area": "Research"},
        {"name": "Archived", "functional_area": "Clients", "status": "archived"},
    )
    created = []
    for payload in create_payloads:
        response = await client.post(CAPABILITIES_PATH, headers=logged_in_headers, json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        created.append(response.json())

    first_page = await client.get(
        CAPABILITIES_PATH,
        headers=logged_in_headers,
        params={"offset": 1, "limit": 1},
    )
    assert first_page.status_code == status.HTTP_200_OK
    assert first_page.json()["total"] == 2
    assert first_page.json()["offset"] == 1
    assert first_page.json()["limit"] == 1
    assert [item["name"] for item in first_page.json()["items"]] == ["Alpha"]
    assert set(first_page.json()["items"][0]) == set(CapabilitySummary.model_fields)

    all_response = await client.get(
        CAPABILITIES_PATH,
        headers=logged_in_headers,
        params={"include_archived": True},
    )
    assert all_response.status_code == status.HTTP_200_OK
    assert all_response.json()["total"] == 3
    assert [item["name"] for item in all_response.json()["items"]] == ["Archived", "Zulu", "Alpha"]
    assert all(item["name"] != "Foreign" for item in all_response.json()["items"])

    missing_id = uuid4()
    foreign_get = await client.get(f"{CAPABILITIES_PATH}/{foreign_id}", headers=logged_in_headers)
    missing_get = await client.get(f"{CAPABILITIES_PATH}/{missing_id}", headers=logged_in_headers)
    assert (foreign_get.status_code, foreign_get.json()) == (missing_get.status_code, missing_get.json())
    assert foreign_get.status_code == status.HTTP_404_NOT_FOUND

    foreign_patch = await client.patch(
        f"{CAPABILITIES_PATH}/{foreign_id}",
        headers=logged_in_headers,
        json={"name": "Must not change"},
    )
    missing_patch = await client.patch(
        f"{CAPABILITIES_PATH}/{missing_id}",
        headers=logged_in_headers,
        json={"name": "Must not change"},
    )
    assert (foreign_patch.status_code, foreign_patch.json()) == (missing_patch.status_code, missing_patch.json())
    assert foreign_patch.status_code == status.HTTP_404_NOT_FOUND
    assert (await _read_capability(UUID(foreign_id))).user_id == other_id

    foreign_parent = await client.post(
        CAPABILITIES_PATH,
        headers=logged_in_headers,
        json={
            "name": "Cross-owner child",
            "functional_area": "Clients",
            "parent_capability_id": foreign_id,
        },
    )
    assert foreign_parent.status_code == status.HTTP_404_NOT_FOUND
    assert foreign_parent.json() == {"detail": "Parent Capability not found"}

    invalid_page = await client.get(CAPABILITIES_PATH, headers=logged_in_headers, params={"limit": 201})
    assert invalid_page.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert all(UUID(item["user_id"]) == active_user.id for item in created)


async def test_api_maps_hierarchy_frequency_patch_and_assessment_rules(
    client: AsyncClient,
    logged_in_headers: dict[str, str],
) -> None:
    archived_parent = (
        await client.post(
            CAPABILITIES_PATH,
            headers=logged_in_headers,
            json={"name": "Archived parent", "functional_area": "Clients", "status": "archived"},
        )
    ).json()
    rejected_child = await client.post(
        CAPABILITIES_PATH,
        headers=logged_in_headers,
        json={
            "name": "Active child",
            "functional_area": "Research",
            "parent_capability_id": archived_parent["id"],
        },
    )
    assert rejected_child.status_code == status.HTTP_409_CONFLICT

    parent = (
        await client.post(
            CAPABILITIES_PATH,
            headers=logged_in_headers,
            json={"name": "Parent", "functional_area": "Clients"},
        )
    ).json()
    child = (
        await client.post(
            CAPABILITIES_PATH,
            headers=logged_in_headers,
            json={
                "name": "Child",
                "functional_area": "Research",
                "parent_capability_id": parent["id"],
                "frequency_period": "week",
                "frequency_value": 2,
                "business_value": 4,
            },
        )
    ).json()
    assert child["assessed_at"] is not None
    original_assessed_at = child["assessed_at"]

    archive_blocked = await client.patch(
        f"{CAPABILITIES_PATH}/{parent['id']}",
        headers=logged_in_headers,
        json={"status": "archived"},
    )
    assert archive_blocked.status_code == status.HTTP_409_CONFLICT

    cycle = await client.patch(
        f"{CAPABILITIES_PATH}/{parent['id']}",
        headers=logged_in_headers,
        json={"parent_capability_id": child["id"]},
    )
    assert cycle.status_code == status.HTTP_409_CONFLICT

    frequency_update = await client.patch(
        f"{CAPABILITIES_PATH}/{child['id']}",
        headers=logged_in_headers,
        json={"frequency_value": 2.5},
    )
    assert frequency_update.status_code == status.HTTP_200_OK
    assert frequency_update.json()["frequency_period"] == "week"
    assert frequency_update.json()["frequency_value"] == 2.5
    assert frequency_update.json()["assessed_at"] == original_assessed_at

    incoherent_frequency = await client.patch(
        f"{CAPABILITIES_PATH}/{child['id']}",
        headers=logged_in_headers,
        json={"frequency_period": "ad_hoc"},
    )
    assert incoherent_frequency.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    empty_update = await client.patch(
        f"{CAPABILITIES_PATH}/{child['id']}",
        headers=logged_in_headers,
        json={},
    )
    assert empty_update.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    before_noop = frequency_update.json()["updated_at"]
    no_op = await client.patch(
        f"{CAPABILITIES_PATH}/{child['id']}",
        headers=logged_in_headers,
        json={"name": " Child "},
    )
    assert no_op.status_code == status.HTTP_200_OK
    assert no_op.json()["updated_at"] == before_noop

    cleared_assessment = await client.patch(
        f"{CAPABILITIES_PATH}/{child['id']}",
        headers=logged_in_headers,
        json={"business_value": None},
    )
    assert cleared_assessment.status_code == status.HTTP_200_OK
    assert cleared_assessment.json()["assessed_at"] is None
    assert cleared_assessment.json()["assessed_by"] is None

    archived_child = await client.patch(
        f"{CAPABILITIES_PATH}/{child['id']}",
        headers=logged_in_headers,
        json={"status": "archived"},
    )
    assert archived_child.status_code == status.HTTP_200_OK
    archived_parent_response = await client.patch(
        f"{CAPABILITIES_PATH}/{parent['id']}",
        headers=logged_in_headers,
        json={"status": "archived"},
    )
    assert archived_parent_response.status_code == status.HTTP_200_OK
    restore_under_archived = await client.patch(
        f"{CAPABILITIES_PATH}/{child['id']}",
        headers=logged_in_headers,
        json={"status": "active"},
    )
    assert restore_under_archived.status_code == status.HTTP_409_CONFLICT


async def test_flow_write_authorization_masks_failures_and_preserves_rejected_update(
    client: AsyncClient,
    logged_in_headers: dict[str, str],
    active_user,
) -> None:
    other_id, _ = await _create_user_and_headers(client, username=f"private-flow-owner-{uuid4()}")
    owned_flow_id = await _seed_flow(owner_id=active_user.id, name="Owned Proposal Flow")
    inaccessible_flow_id = await _seed_flow(owner_id=other_id, name="Do Not Leak This Name")

    linked = await client.post(
        CAPABILITIES_PATH,
        headers=logged_in_headers,
        json={
            "name": "Linked Proposal",
            "functional_area": "Clients",
            "primary_flow_id": str(owned_flow_id),
        },
    )
    assert linked.status_code == status.HTTP_201_CREATED
    assert linked.json()["primary_flow_id"] == str(owned_flow_id)
    assert linked.json()["primary_flow_link"] == {
        "status": "available",
        "flow": {"id": str(owned_flow_id), "name": "Owned Proposal Flow"},
    }
    assert set(linked.json()["primary_flow_link"]["flow"]) == {"id", "name"}
    readable_get = await client.get(f"{CAPABILITIES_PATH}/{linked.json()['id']}", headers=logged_in_headers)
    assert readable_get.status_code == status.HTTP_200_OK
    assert readable_get.json()["primary_flow_link"] == linked.json()["primary_flow_link"]

    rejected_responses = []
    for index, flow_id in enumerate((uuid4(), inaccessible_flow_id)):
        response = await client.post(
            CAPABILITIES_PATH,
            headers=logged_in_headers,
            json={
                "name": f"Rejected Flow {index}",
                "functional_area": "Clients",
                "primary_flow_id": str(flow_id),
            },
        )
        rejected_responses.append((response.status_code, response.json()))
    assert rejected_responses[0] == rejected_responses[1]
    assert rejected_responses[0] == (
        status.HTTP_404_NOT_FOUND,
        {"detail": "Primary Flow is not accessible"},
    )
    assert await _capability_count(owner_id=active_user.id, name_prefix="Rejected Flow") == 0

    linked_body = linked.json()
    rejected_patch_responses = []
    for flow_id in (uuid4(), inaccessible_flow_id):
        rejected_patch = await client.patch(
            f"{CAPABILITIES_PATH}/{linked_body['id']}",
            headers=logged_in_headers,
            json={"name": "Must not persist", "business_value": 5, "primary_flow_id": str(flow_id)},
        )
        rejected_patch_responses.append((rejected_patch.status_code, rejected_patch.json()))
    assert rejected_patch_responses[0] == rejected_patch_responses[1]
    assert rejected_patch_responses[0] == (
        status.HTTP_404_NOT_FOUND,
        {"detail": "Primary Flow is not accessible"},
    )
    after_rejection = await _read_capability(UUID(linked_body["id"]))
    assert after_rejection.name == "Linked Proposal"
    assert after_rejection.business_value is None
    assert after_rejection.primary_flow_id == owned_flow_id
    response_updated_at = datetime.fromisoformat(linked_body["updated_at"].replace("Z", "+00:00"))
    assert after_rejection.updated_at == response_updated_at.replace(tzinfo=None)
    assert after_rejection.assessed_at is None
    assert after_rejection.assessed_by is None

    unlinked = await client.post(
        CAPABILITIES_PATH,
        headers=logged_in_headers,
        json={"name": "Link on update", "functional_area": "Clients"},
    )
    update_to_owned = await client.patch(
        f"{CAPABILITIES_PATH}/{unlinked.json()['id']}",
        headers=logged_in_headers,
        json={"primary_flow_id": str(owned_flow_id)},
    )
    assert update_to_owned.status_code == status.HTTP_200_OK
    assert update_to_owned.json()["primary_flow_link"]["status"] == "available"

    same_link = await client.patch(
        f"{CAPABILITIES_PATH}/{linked_body['id']}",
        headers=logged_in_headers,
        json={"primary_flow_id": str(owned_flow_id)},
    )
    assert same_link.status_code == status.HTTP_200_OK
    assert same_link.json()["updated_at"] == linked_body["updated_at"]


async def test_inaccessible_stored_link_is_reported_without_metadata_or_storage_mutation(
    client: AsyncClient,
    logged_in_headers: dict[str, str],
    active_user,
) -> None:
    other_id, _ = await _create_user_and_headers(client, username=f"redacted-flow-owner-{uuid4()}")
    flow_name = "Secret Revoked Flow Name"
    stored_flow_id = await _seed_flow(owner_id=other_id, name=flow_name)
    capability_id, original_updated_at = await _seed_capability(
        owner_id=active_user.id,
        name="Stored inaccessible link",
        primary_flow_id=stored_flow_id,
    )

    get_response = await client.get(f"{CAPABILITIES_PATH}/{capability_id}", headers=logged_in_headers)
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json()["primary_flow_id"] == str(stored_flow_id)
    assert get_response.json()["primary_flow_link"] == {"status": "unavailable", "flow": None}
    assert flow_name not in get_response.text

    list_response = await client.get(CAPABILITIES_PATH, headers=logged_in_headers)
    assert list_response.status_code == status.HTTP_200_OK
    item = next(item for item in list_response.json()["items"] if item["id"] == str(capability_id))
    assert item["primary_flow_id"] == str(stored_flow_id)
    assert item["primary_flow_link"] == {"status": "unavailable", "flow": None}
    assert flow_name not in list_response.text

    stored = await _read_capability(capability_id)
    assert stored.primary_flow_id == stored_flow_id
    assert stored.updated_at == original_updated_at.replace(tzinfo=None)
    assert stored.assessed_at is None
    assert stored.assessed_by is None

    unrelated_patch = await client.patch(
        f"{CAPABILITIES_PATH}/{capability_id}",
        headers=logged_in_headers,
        json={"description": "Permission loss does not block other work"},
    )
    assert unrelated_patch.status_code == status.HTTP_200_OK
    assert unrelated_patch.json()["primary_flow_id"] == str(stored_flow_id)
    assert unrelated_patch.json()["primary_flow_link"] == {"status": "unavailable", "flow": None}

    same_inaccessible = await client.patch(
        f"{CAPABILITIES_PATH}/{capability_id}",
        headers=logged_in_headers,
        json={"primary_flow_id": str(stored_flow_id)},
    )
    assert same_inaccessible.status_code == status.HTTP_404_NOT_FOUND
    assert (await _read_capability(capability_id)).primary_flow_id == stored_flow_id

    clear_response = await client.patch(
        f"{CAPABILITIES_PATH}/{capability_id}",
        headers=logged_in_headers,
        json={"primary_flow_id": None},
    )
    assert clear_response.status_code == status.HTTP_200_OK
    assert clear_response.json()["primary_flow_id"] is None
    assert clear_response.json()["primary_flow_link"] == {"status": "not_linked", "flow": None}


async def test_shared_readable_non_owned_flow_is_linkable_but_does_not_share_capabilities(
    client: AsyncClient,
    logged_in_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow_owner_id, flow_owner_headers = await _create_user_and_headers(
        client,
        username=f"shared-flow-owner-{uuid4()}",
    )
    shared_flow_id = await _seed_flow(owner_id=flow_owner_id, name="Shared Research Flow")
    service = _install_authorization(monkeypatch, allow=True, supports_cross_user_fetch=True)

    response = await client.post(
        CAPABILITIES_PATH,
        headers=logged_in_headers,
        json={
            "name": "Market Research",
            "functional_area": "Research",
            "primary_flow_id": str(shared_flow_id),
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["primary_flow_link"] == {
        "status": "available",
        "flow": {"id": str(shared_flow_id), "name": "Shared Research Flow"},
    }
    assert service.calls
    assert all(call["act"] == "read" for call in service.calls)

    unlinked = await client.post(
        CAPABILITIES_PATH,
        headers=logged_in_headers,
        json={"name": "Shared link update", "functional_area": "Research"},
    )
    shared_update = await client.patch(
        f"{CAPABILITIES_PATH}/{unlinked.json()['id']}",
        headers=logged_in_headers,
        json={"primary_flow_id": str(shared_flow_id)},
    )
    assert shared_update.status_code == status.HTTP_200_OK
    assert shared_update.json()["primary_flow_link"] == response.json()["primary_flow_link"]

    flow_owner_capability = await client.post(
        CAPABILITIES_PATH,
        headers=flow_owner_headers,
        json={
            "name": "Owner-only capability",
            "functional_area": "Research",
            "primary_flow_id": str(shared_flow_id),
        },
    )
    assert flow_owner_capability.status_code == status.HTTP_201_CREATED
    forbidden = await client.get(
        f"{CAPABILITIES_PATH}/{flow_owner_capability.json()['id']}",
        headers=logged_in_headers,
    )
    assert forbidden.status_code == status.HTTP_404_NOT_FOUND


async def test_projection_is_non_mutating_catches_only_expected_unavailability(
    async_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(username=f"projection-user-{uuid4()}", password="not-a-real-password", is_active=True)  # noqa: S106
    linked_id = uuid4()
    capability = Capability(
        name="Projection subject",
        functional_area="Operations",
        user_id=user.id,
        primary_flow_id=linked_id,
    )
    original_updated_at = capability.updated_at

    resolver = AsyncMock(side_effect=FlowReadUnavailableError("Flow not found"))
    flush = AsyncMock()
    commit = AsyncMock()
    rollback = AsyncMock()
    monkeypatch.setattr(capabilities_api, "resolve_authorized_flow_for_read", resolver)
    monkeypatch.setattr(async_session, "flush", flush)
    monkeypatch.setattr(async_session, "commit", commit)
    monkeypatch.setattr(async_session, "rollback", rollback)

    response = await capabilities_api.project_capability_for_response(
        async_session,
        capability=capability,
        current_user=user,
    )

    assert response.primary_flow_id == linked_id
    assert response.primary_flow_link.status.value == "unavailable"
    assert response.primary_flow_link.flow is None
    assert capability.primary_flow_id == linked_id
    assert capability.updated_at == original_updated_at
    assert capability.assessed_at is None
    assert capability.assessed_by is None
    assert capability not in async_session.dirty
    flush.assert_not_awaited()
    commit.assert_not_awaited()
    rollback.assert_not_awaited()

    resolver.side_effect = RuntimeError("authorization infrastructure failed")
    with pytest.raises(RuntimeError, match="authorization infrastructure failed"):
        await capabilities_api.project_capability_for_response(
            async_session,
            capability=capability,
            current_user=user,
        )


async def test_list_resolves_each_distinct_flow_only_once(
    async_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(username=f"list-projection-user-{uuid4()}", password="not-a-real-password", is_active=True)  # noqa: S106
    flow = Flow(name="Shared primary", data={}, user_id=user.id)
    async_session.add_all([user, flow])
    await async_session.flush()
    first = Capability(name="First", functional_area="Clients", user_id=user.id, primary_flow_id=flow.id)
    second = Capability(name="Second", functional_area="Clients", user_id=user.id, primary_flow_id=flow.id)
    async_session.add_all([first, second])
    await async_session.flush()
    resolver = AsyncMock(return_value=flow)
    monkeypatch.setattr(capabilities_api, "resolve_authorized_flow_for_read", resolver)

    response = await capabilities_api.read_capabilities(
        session=async_session,
        current_user=user,
        include_archived=False,
        offset=0,
        limit=200,
    )

    assert [item.primary_flow_link.flow.name for item in response.items] == ["Shared primary", "Shared primary"]
    resolver.assert_awaited_once_with(async_session, flow_id=flow.id, current_user=user)
