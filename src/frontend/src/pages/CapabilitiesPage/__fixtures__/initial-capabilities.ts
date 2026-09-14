import type { CapabilitySummary } from "@/types/capabilities";

const createFixtureCapability = (
  id: string,
  name: string,
  functionalArea: string,
): CapabilitySummary => ({
  id,
  name,
  functional_area: functionalArea,
  parent_capability_id: null,
  status: "active",
  current_maturity: "not_assessed",
  target_maturity: null,
  business_value: null,
  ai_feasibility: null,
  ai_execution_risk: null,
  primary_flow_id: null,
  primary_flow_link: { status: "not_linked", flow: null },
});

export const INITIAL_CAPABILITIES_FIXTURE: CapabilitySummary[] = [
  createFixtureCapability(
    "00000000-0000-4000-8000-000000000001",
    "Proposal Builder",
    "Clients",
  ),
  createFixtureCapability(
    "00000000-0000-4000-8000-000000000002",
    "Workshop Architect",
    "Programmes",
  ),
  createFixtureCapability(
    "00000000-0000-4000-8000-000000000003",
    "Talking-Head Script Writer",
    "Marketing & Content",
  ),
  createFixtureCapability(
    "00000000-0000-4000-8000-000000000004",
    "Market Research",
    "Research",
  ),
  createFixtureCapability(
    "00000000-0000-4000-8000-000000000005",
    "Meeting Synthesiser",
    "Operations",
  ),
];
