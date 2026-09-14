import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import type { CapabilityRead } from "@/types/capabilities";
import { axe } from "@/utils/a11y-test";
import { CapabilityDetailDrawer } from "../CapabilityDetailDrawer";

const detail = (overrides: Partial<CapabilityRead> = {}): CapabilityRead => ({
  id: "00000000-0000-4000-8000-000000000001",
  name: "Proposal Builder",
  description: null,
  functional_area: "Clients",
  parent_capability_id: null,
  status: "active",
  user_id: "00000000-0000-4000-8000-000000000099",
  workspace_id: null,
  current_maturity: "ai_assisted",
  target_maturity: "ai_executable",
  human_oversight: "approval_required",
  oversight_notes: null,
  frequency_value: 2.5,
  frequency_period: "week",
  baseline_human_effort_minutes_per_run: 180,
  business_value: 4,
  ai_feasibility: null,
  ai_execution_risk: 3,
  assessment_notes: null,
  assessed_at: "2026-09-14T10:00:00Z",
  assessed_by: "00000000-0000-4000-8000-000000000099",
  inputs: ["Client brief", "Discovery notes"],
  outputs: [],
  tools: [],
  primary_flow_id: "00000000-0000-4000-8000-000000000050",
  primary_flow_link: { status: "unavailable", flow: null },
  created_at: "2026-09-14T09:00:00Z",
  updated_at: "2026-09-14T10:00:00Z",
  ...overrides,
});

describe("CapabilityDetailDrawer", () => {
  it("shows full detail, preserves an unavailable stored Flow ID, and leaks no Flow name", async () => {
    const capability = detail();
    render(
      <CapabilityDetailDrawer
        capability={capability}
        isError={false}
        isLoading={false}
        onOpenChange={jest.fn()}
        onRetry={jest.fn()}
        open
      />,
    );

    expect(
      screen.getByRole("dialog", { name: capability.name }),
    ).toBeInTheDocument();
    expect(screen.getByText("AI assisted")).toBeInTheDocument();
    expect(screen.getByText("AI executable")).toBeInTheDocument();
    expect(screen.getByText("2.5 times per week")).toBeInTheDocument();
    expect(
      screen.getByText("180 total human minutes per run"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(capability.primary_flow_id as string),
    ).toBeInTheDocument();
    expect(screen.getByText("Flow unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Restricted Flow Name")).not.toBeInTheDocument();
    expect(screen.getAllByText("Not assessed").length).toBeGreaterThan(0);
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("shows only authorized Flow summary data for an available link", () => {
    render(
      <CapabilityDetailDrawer
        capability={detail({
          primary_flow_link: {
            status: "available",
            flow: {
              id: "00000000-0000-4000-8000-000000000050",
              name: "Proposal Workflow",
            },
          },
        })}
        isError={false}
        isLoading={false}
        onOpenChange={jest.fn()}
        onRetry={jest.fn()}
        open
      />,
    );

    expect(screen.getByText("Proposal Workflow")).toBeInTheDocument();
    expect(screen.queryByText("Flow data")).not.toBeInTheDocument();
  });

  it("closes on Escape and restores focus to the selecting control", async () => {
    const user = userEvent.setup();

    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            Proposal Builder
          </button>
          <CapabilityDetailDrawer
            capability={detail()}
            isError={false}
            isLoading={false}
            onOpenChange={setOpen}
            onRetry={jest.fn()}
            open={open}
          />
        </>
      );
    }

    render(<Harness />);
    const opener = screen.getByRole("button", { name: "Proposal Builder" });
    await user.click(opener);
    await screen.findByRole("dialog");
    await user.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(opener).toHaveFocus();
  });
});
