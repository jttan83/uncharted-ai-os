import type { Route } from "@playwright/test";
import { expect, test } from "../fixtures";
import { awaitBootstrapTest } from "../utils/await-bootstrap-test";

const summary = {
  id: "00000000-0000-4000-8000-000000000001",
  name: "Proposal Builder",
  functional_area: "Clients",
  parent_capability_id: null,
  status: "active",
  current_maturity: "ai_assisted",
  target_maturity: "ai_executable",
  business_value: 4,
  ai_feasibility: 4,
  ai_execution_risk: 3,
  primary_flow_id: null,
  primary_flow_link: { status: "not_linked", flow: null },
};

async function fulfillCapabilities(route: Route) {
  const isDetail = /\/capabilities\/[^/]+$/.test(
    new URL(route.request().url()).pathname,
  );
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(
      isDetail
        ? {
            ...summary,
            description: "Builds a tailored client proposal.",
            user_id: "00000000-0000-4000-8000-000000000099",
            workspace_id: null,
            human_oversight: "approval_required",
            oversight_notes: "A human approves every external proposal.",
            frequency_value: 2.5,
            frequency_period: "week",
            baseline_human_effort_minutes_per_run: 180,
            assessment_notes: "Directional assessment for prioritisation.",
            assessed_at: "2026-09-14T10:00:00Z",
            assessed_by: "00000000-0000-4000-8000-000000000099",
            inputs: ["Client brief"],
            outputs: ["Proposal draft"],
            tools: [],
            created_at: "2026-09-14T09:00:00Z",
            updated_at: "2026-09-14T10:00:00Z",
          }
        : { items: [summary], total: 1, offset: 0, limit: 200 },
    ),
  });
}

test(
  "Capability Map and read-only drawer meet the route accessibility baseline",
  { tag: ["@release", "@workspace"] },
  async ({ page }) => {
    await awaitBootstrapTest(page, {
      seedFlowIfEmpty: false,
      skipModal: true,
    });
    await page.route("**/api/v1/capabilities**", fulfillCapabilities);
    await page.goto("/capabilities");

    await expect(page.getByTestId("capability-skill-tree")).toBeVisible();
    await page.runA11yScan("capabilities-populated");

    const node = page.getByRole("button", { name: "Proposal Builder" });
    await node.focus();
    await node.press("Enter");
    await expect(
      page.getByRole("dialog", { name: "Proposal Builder" }),
    ).toBeVisible();
    await page.runA11yScan("capability-detail-drawer");
  },
);
