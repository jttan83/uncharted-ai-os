import type { Route } from "@playwright/test";
import { expect, test } from "../../fixtures";
import { awaitBootstrapTest } from "../../utils/await-bootstrap-test";
import { mockAutoLoginDisabled } from "../../utils/auth/mock-auto-login-disabled";

const capabilitySummaries = [
  ["00000000-0000-4000-8000-000000000001", "Proposal Builder", "Clients"],
  ["00000000-0000-4000-8000-000000000002", "Workshop Architect", "Programmes"],
  [
    "00000000-0000-4000-8000-000000000003",
    "Talking-Head Script Writer",
    "Marketing & Content",
  ],
  ["00000000-0000-4000-8000-000000000004", "Market Research", "Research"],
  ["00000000-0000-4000-8000-000000000005", "Meeting Synthesiser", "Operations"],
].map(([id, name, functionalArea]) => ({
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
}));

const capabilityDetail = {
  ...capabilitySummaries[0],
  description: "Builds a tailored client proposal.",
  user_id: "00000000-0000-4000-8000-000000000099",
  workspace_id: null,
  human_oversight: "approval_required",
  oversight_notes: "A human approves every external proposal.",
  frequency_value: 2.5,
  frequency_period: "week",
  baseline_human_effort_minutes_per_run: 180,
  assessment_notes: null,
  assessed_at: null,
  assessed_by: null,
  inputs: ["Client brief"],
  outputs: ["Proposal draft"],
  tools: [],
  created_at: "2026-09-14T09:00:00Z",
  updated_at: "2026-09-14T09:00:00Z",
};

async function fulfillCapabilities(route: Route) {
  const url = new URL(route.request().url());
  const id = url.pathname.match(/\/capabilities\/([^/]+)$/)?.[1];
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(
      id
        ? {
            ...capabilityDetail,
            id,
            name:
              capabilitySummaries.find((item) => item.id === id)?.name ??
              "Capability",
          }
        : {
            items: capabilitySummaries,
            total: capabilitySummaries.length,
            offset: 0,
            limit: 200,
          },
    ),
  });
}

test(
  "protected Capability Map renders the five-record preview and opens full detail",
  { tag: ["@release", "@api"] },
  async ({ page }) => {
    await awaitBootstrapTest(page, {
      seedFlowIfEmpty: false,
      skipModal: true,
    });
    await page.route("**/api/v1/capabilities**", fulfillCapabilities);

    await page.goto("/capabilities");

    await expect(page).toHaveURL(/\/capabilities\/?$/);
    await expect(page.getByTestId("app-header")).toBeVisible();
    await expect(page.getByTestId("capabilities-page")).toBeVisible();
    for (const capability of capabilitySummaries) {
      await expect(
        page.getByRole("button", { name: capability.name }),
      ).toBeVisible();
    }

    const proposal = page.getByRole("button", { name: "Proposal Builder" });
    await proposal.focus();
    await proposal.press("Enter");
    await expect(
      page.getByRole("dialog", { name: "Proposal Builder" }),
    ).toBeVisible();
    await expect(
      page.getByText("Builds a tailored client proposal."),
    ).toBeVisible();
    await expect(
      page.getByText("180 total human minutes per run"),
    ).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(proposal).toBeFocused();

    await page.goto("/flows");
    await expect(page.getByTestId("mainpage_title")).toBeVisible();
  },
);

test(
  "unauthenticated direct Capability Map access uses existing login protection",
  { tag: ["@release", "@api"] },
  async ({ page }) => {
    await awaitBootstrapTest(page, {
      seedFlowIfEmpty: false,
      skipModal: true,
    });
    await mockAutoLoginDisabled(page);
    await page.context().clearCookies();
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    await page.goto("/capabilities");

    await expect(page).toHaveURL(/\/login\/?$/);
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
    await expect(page.getByTestId("capabilities-page")).not.toBeVisible();
  },
);
