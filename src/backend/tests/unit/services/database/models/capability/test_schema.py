from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

import pytest
from langflow.services.database.models.capability import (
    CapabilityCreate,
    CapabilityListResponse,
    CapabilityMaturity,
    CapabilityRead,
    CapabilityStatus,
    CapabilitySummary,
    CapabilityUpdate,
    FlowLinkAvailability,
    FlowLinkAvailabilityStatus,
    FlowLinkSummary,
    FrequencyPeriod,
    HumanOversight,
)
from pydantic import ValidationError


def _minimal_create_payload(**overrides):
    return {"name": "Proposal Builder", "functional_area": "Clients", **overrides}


def _summary_payload(**overrides):
    return {
        "id": uuid4(),
        "name": "Proposal Builder",
        "functional_area": "Clients",
        "parent_capability_id": None,
        "status": CapabilityStatus.ACTIVE,
        "current_maturity": CapabilityMaturity.NOT_ASSESSED,
        "target_maturity": None,
        "business_value": None,
        "ai_feasibility": None,
        "ai_execution_risk": None,
        "primary_flow_id": None,
        "primary_flow_link": {"status": FlowLinkAvailabilityStatus.NOT_LINKED, "flow": None},
        **overrides,
    }


def test_create_defaults_and_independent_collection_defaults():
    first = CapabilityCreate(**_minimal_create_payload())
    second = CapabilityCreate(**_minimal_create_payload())

    assert first.description is None
    assert first.parent_capability_id is None
    assert first.status is CapabilityStatus.ACTIVE
    assert first.current_maturity is CapabilityMaturity.NOT_ASSESSED
    assert first.target_maturity is None
    assert first.human_oversight is None
    assert first.oversight_notes is None
    assert first.frequency_value is None
    assert first.frequency_period is None
    assert first.baseline_human_effort_minutes_per_run is None
    assert first.business_value is None
    assert first.ai_feasibility is None
    assert first.ai_execution_risk is None
    assert first.assessment_notes is None
    assert first.inputs == []
    assert first.outputs == []
    assert first.tools == []
    assert first.primary_flow_id is None
    assert first.inputs is not second.inputs


def test_create_normalizes_all_text_fields():
    capability = CapabilityCreate(
        **_minimal_create_payload(
            name="  Proposal Builder  ",
            functional_area="  Clients  ",
            description="  Produces a proposal.  ",
            oversight_notes="   ",
            assessment_notes="  Based on repeated delivery.  ",
        )
    )

    assert capability.name == "Proposal Builder"
    assert capability.functional_area == "Clients"
    assert capability.description == "Produces a proposal."
    assert capability.oversight_notes is None
    assert capability.assessment_notes == "Based on repeated delivery."


@pytest.mark.parametrize("field_name", ["description", "oversight_notes", "assessment_notes"])
def test_create_converts_every_blank_optional_text_field_to_null(field_name):
    capability = CapabilityCreate(**_minimal_create_payload(**{field_name: "   "}))
    assert getattr(capability, field_name) is None


@pytest.mark.parametrize(
    ("field_name", "valid_length", "invalid_length"),
    [
        ("name", 120, 121),
        ("functional_area", 120, 121),
        ("description", 2_000, 2_001),
        ("oversight_notes", 2_000, 2_001),
        ("assessment_notes", 5_000, 5_001),
    ],
)
def test_create_enforces_every_text_maximum(field_name, valid_length, invalid_length):
    valid = CapabilityCreate(**_minimal_create_payload(**{field_name: "x" * valid_length}))
    assert len(getattr(valid, field_name)) == valid_length

    with pytest.raises(ValidationError):
        CapabilityCreate(**_minimal_create_payload(**{field_name: "x" * invalid_length}))


@pytest.mark.parametrize("field_name", ["name", "functional_area"])
def test_create_rejects_blank_required_text(field_name):
    with pytest.raises(ValidationError):
        CapabilityCreate(**_minimal_create_payload(**{field_name: "   "}))


@pytest.mark.parametrize(
    ("enum_type", "expected_values"),
    [
        (CapabilityStatus, {"active", "archived"}),
        (
            CapabilityMaturity,
            {"not_assessed", "manual", "ai_assisted", "ai_executable", "automated"},
        ),
        (HumanOversight, {"none", "review_recommended", "approval_required", "human_led"}),
        (FrequencyPeriod, {"day", "week", "month", "quarter", "year", "ad_hoc", "unknown"}),
    ],
)
def test_domain_enum_values_are_exact(enum_type: type[Enum], expected_values):
    assert {member.value for member in enum_type} == expected_values
    for value in expected_values:
        assert enum_type(value).value == value


@pytest.mark.parametrize(
    ("field_name", "enum_type"),
    [
        ("status", CapabilityStatus),
        ("current_maturity", CapabilityMaturity),
        ("target_maturity", CapabilityMaturity),
        ("human_oversight", HumanOversight),
        ("frequency_period", FrequencyPeriod),
    ],
)
def test_create_accepts_every_domain_enum_value(field_name, enum_type):
    for member in enum_type:
        overrides = {field_name: member.value}
        if field_name == "frequency_period" and member not in {FrequencyPeriod.AD_HOC, FrequencyPeriod.UNKNOWN}:
            overrides["frequency_value"] = 1
        capability = CapabilityCreate(**_minimal_create_payload(**overrides))
        assert getattr(capability, field_name) is member


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("status", "deleted"),
        ("current_maturity", "assisted"),
        ("target_maturity", "complete"),
        ("human_oversight", "mandatory"),
        ("frequency_period", "daily"),
    ],
)
def test_create_rejects_invalid_enum_values(field_name, invalid_value):
    with pytest.raises(ValidationError):
        CapabilityCreate(**_minimal_create_payload(**{field_name: invalid_value}))


@pytest.mark.parametrize(
    "period",
    [FrequencyPeriod.DAY, FrequencyPeriod.WEEK, FrequencyPeriod.MONTH, FrequencyPeriod.QUARTER, FrequencyPeriod.YEAR],
)
def test_create_accepts_fractional_frequency_for_calendar_periods(period):
    capability = CapabilityCreate(**_minimal_create_payload(frequency_period=period, frequency_value=2.5))
    assert capability.frequency_value == 2.5


@pytest.mark.parametrize("period", [FrequencyPeriod.AD_HOC, FrequencyPeriod.UNKNOWN])
def test_create_accepts_non_numeric_frequency_periods_with_null_value(period):
    capability = CapabilityCreate(**_minimal_create_payload(frequency_period=period, frequency_value=None))
    assert capability.frequency_value is None


@pytest.mark.parametrize(
    ("period", "value"),
    [
        (None, 1),
        (FrequencyPeriod.DAY, None),
        (FrequencyPeriod.AD_HOC, 1),
        (FrequencyPeriod.UNKNOWN, 1),
        (FrequencyPeriod.MONTH, 0),
        (FrequencyPeriod.MONTH, -1),
        (FrequencyPeriod.MONTH, float("nan")),
        (FrequencyPeriod.MONTH, float("inf")),
    ],
)
def test_create_rejects_invalid_frequency(period, value):
    with pytest.raises(ValidationError):
        CapabilityCreate(**_minimal_create_payload(frequency_period=period, frequency_value=value))


@pytest.mark.parametrize("value", [None, 0, 180])
def test_create_accepts_valid_effort(value):
    capability = CapabilityCreate(**_minimal_create_payload(baseline_human_effort_minutes_per_run=value))
    assert capability.baseline_human_effort_minutes_per_run == value


@pytest.mark.parametrize("value", [-1, 1.5, True, False, "1"])
def test_create_rejects_invalid_effort(value):
    with pytest.raises(ValidationError):
        CapabilityCreate(**_minimal_create_payload(baseline_human_effort_minutes_per_run=value))


@pytest.mark.parametrize("field_name", ["business_value", "ai_feasibility", "ai_execution_risk"])
@pytest.mark.parametrize("value", [None, 1, 5])
def test_create_accepts_valid_assessment_scores(field_name, value):
    capability = CapabilityCreate(**_minimal_create_payload(**{field_name: value}))
    assert getattr(capability, field_name) == value


@pytest.mark.parametrize("field_name", ["business_value", "ai_feasibility", "ai_execution_risk"])
@pytest.mark.parametrize("value", [0, 6, 1.5, True, False, "3"])
def test_create_rejects_invalid_assessment_scores(field_name, value):
    with pytest.raises(ValidationError):
        CapabilityCreate(**_minimal_create_payload(**{field_name: value}))


def test_create_normalizes_all_context_arrays():
    values = [" Client brief ", "Discovery notes", "Client brief"]
    capability = CapabilityCreate(**_minimal_create_payload(inputs=values, outputs=values, tools=values))
    expected = ["Client brief", "Discovery notes"]
    assert capability.inputs == expected
    assert capability.outputs == expected
    assert capability.tools == expected


@pytest.mark.parametrize("field_name", ["inputs", "outputs", "tools"])
@pytest.mark.parametrize("value", [[""], ["x" * 201], ["valid", 1], ["same"] * 51, None])
def test_create_rejects_invalid_context_arrays(field_name, value):
    with pytest.raises(ValidationError):
        CapabilityCreate(**_minimal_create_payload(**{field_name: value}))


def test_update_distinguishes_omitted_field_from_explicit_null():
    omitted = CapabilityUpdate()
    explicit_null = CapabilityUpdate(description=None)

    assert "description" not in omitted.model_fields_set
    assert omitted.model_dump(exclude_unset=True) == {}
    assert "description" in explicit_null.model_fields_set
    assert explicit_null.model_dump(exclude_unset=True) == {"description": None}


@pytest.mark.parametrize(
    "field_name",
    ["name", "functional_area", "status", "current_maturity", "inputs", "outputs", "tools"],
)
def test_update_rejects_explicit_null_for_required_fields_and_collections(field_name):
    with pytest.raises(ValidationError):
        CapabilityUpdate(**{field_name: None})


def test_update_validates_complete_supplied_frequency_pair():
    assert CapabilityUpdate(frequency_period=FrequencyPeriod.WEEK, frequency_value=0.5).frequency_value == 0.5
    with pytest.raises(ValidationError):
        CapabilityUpdate(frequency_period=FrequencyPeriod.AD_HOC, frequency_value=1)


def test_update_preserves_single_frequency_field_for_later_effective_state_validation():
    update = CapabilityUpdate(frequency_value=2.5)
    assert update.model_dump(exclude_unset=True) == {"frequency_value": 2.5}


@pytest.mark.parametrize("schema_type", [CapabilityCreate, CapabilityUpdate])
@pytest.mark.parametrize(
    "server_owned_field",
    ["id", "user_id", "workspace_id", "created_at", "updated_at", "assessed_at", "assessed_by"],
)
def test_write_schemas_do_not_expose_server_owned_fields(schema_type, server_owned_field):
    assert server_owned_field not in schema_type.model_fields
    payload = _minimal_create_payload() if schema_type is CapabilityCreate else {}
    payload[server_owned_field] = uuid4()
    with pytest.raises(ValidationError):
        schema_type(**payload)


def test_write_and_read_schema_field_sets_are_explicit():
    writable_fields = {
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
    }
    persisted_fields = writable_fields | {
        "id",
        "user_id",
        "workspace_id",
        "created_at",
        "updated_at",
        "assessed_at",
        "assessed_by",
    }

    assert set(CapabilityCreate.model_fields) == writable_fields
    assert set(CapabilityUpdate.model_fields) == writable_fields
    assert set(CapabilityRead.model_fields) == persisted_fields | {"primary_flow_link"}


def test_flow_link_availability_accepts_all_valid_states():
    flow = FlowLinkSummary(id=uuid4(), name="Proposal Flow")
    assert FlowLinkAvailability(status="not_linked", flow=None).status is FlowLinkAvailabilityStatus.NOT_LINKED
    assert FlowLinkAvailability(status="unavailable", flow=None).status is FlowLinkAvailabilityStatus.UNAVAILABLE
    available = FlowLinkAvailability(status="available", flow=flow)
    assert available.status is FlowLinkAvailabilityStatus.AVAILABLE
    assert available.flow == flow


@pytest.mark.parametrize(
    ("status", "flow"),
    [
        (FlowLinkAvailabilityStatus.AVAILABLE, None),
        (FlowLinkAvailabilityStatus.NOT_LINKED, {"id": uuid4(), "name": "Hidden"}),
        (FlowLinkAvailabilityStatus.UNAVAILABLE, {"id": uuid4(), "name": "Hidden"}),
    ],
)
def test_flow_link_availability_rejects_incoherent_states(status, flow):
    with pytest.raises(ValidationError):
        FlowLinkAvailability(status=status, flow=flow)


def test_capability_response_schemas_accept_uuid_and_nullable_fields():
    summary = CapabilitySummary(**_summary_payload())
    now = datetime.now(timezone.utc)
    capability = CapabilityRead(
        **summary.model_dump(),
        description=None,
        user_id=uuid4(),
        workspace_id=None,
        human_oversight=None,
        oversight_notes=None,
        frequency_value=None,
        frequency_period=None,
        baseline_human_effort_minutes_per_run=None,
        assessment_notes=None,
        assessed_at=None,
        assessed_by=None,
        inputs=[],
        outputs=[],
        tools=[],
        created_at=now,
        updated_at=now,
    )
    response = CapabilityListResponse(items=[summary], total=1, offset=0, limit=200)

    assert capability.id == summary.id
    assert capability.created_at.utcoffset() is not None
    assert response.items == [summary]


def test_response_schemas_reject_invalid_uuid_and_naive_datetimes():
    with pytest.raises(ValidationError):
        FlowLinkSummary(id="not-a-uuid", name="Proposal Flow")

    summary = CapabilitySummary(**_summary_payload())
    with pytest.raises(ValidationError):
        CapabilityRead(
            **summary.model_dump(),
            description=None,
            user_id=uuid4(),
            workspace_id=None,
            human_oversight=None,
            oversight_notes=None,
            frequency_value=None,
            frequency_period=None,
            baseline_human_effort_minutes_per_run=None,
            assessment_notes=None,
            assessed_at=None,
            assessed_by=None,
            inputs=[],
            outputs=[],
            tools=[],
            created_at=datetime.now(),  # noqa: DTZ005 - intentionally verifies naive datetime rejection
            updated_at=datetime.now(timezone.utc),
        )
