export type CapabilityStatus = "active" | "archived";

export type CapabilityMaturity =
  | "not_assessed"
  | "manual"
  | "ai_assisted"
  | "ai_executable"
  | "automated";

export type HumanOversight =
  | "none"
  | "review_recommended"
  | "approval_required"
  | "human_led";

export type FrequencyPeriod =
  | "day"
  | "week"
  | "month"
  | "quarter"
  | "year"
  | "ad_hoc"
  | "unknown";

export type FlowLinkAvailabilityStatus =
  | "not_linked"
  | "available"
  | "unavailable";

export type FlowLinkSummary = {
  id: string;
  name: string;
};

export type FlowLinkAvailability = {
  status: FlowLinkAvailabilityStatus;
  flow: FlowLinkSummary | null;
};

export type CapabilitySummary = {
  id: string;
  name: string;
  functional_area: string;
  parent_capability_id: string | null;
  status: CapabilityStatus;
  current_maturity: CapabilityMaturity;
  target_maturity: CapabilityMaturity | null;
  business_value: number | null;
  ai_feasibility: number | null;
  ai_execution_risk: number | null;
  primary_flow_id: string | null;
  primary_flow_link: FlowLinkAvailability;
};

export type CapabilityRead = CapabilitySummary & {
  description: string | null;
  user_id: string;
  workspace_id: string | null;
  human_oversight: HumanOversight | null;
  oversight_notes: string | null;
  frequency_value: number | null;
  frequency_period: FrequencyPeriod | null;
  baseline_human_effort_minutes_per_run: number | null;
  assessment_notes: string | null;
  assessed_at: string | null;
  assessed_by: string | null;
  inputs: string[];
  outputs: string[];
  tools: string[];
  created_at: string;
  updated_at: string;
};

export type CapabilityListResponse = {
  items: CapabilitySummary[];
  total: number;
  offset: number;
  limit: number;
};
