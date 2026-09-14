import { renderHook } from "@testing-library/react";
import type {
  CapabilityListResponse,
  CapabilitySummary,
} from "@/types/capabilities";
import { api } from "../../../api";
import {
  CapabilityPaginationError,
  fetchAllActiveCapabilities,
  useGetCapabilities,
} from "../use-get-capabilities";

const mockQuery = jest.fn(
  (
    _key?: readonly unknown[],
    _queryFn?: (context: { signal: AbortSignal }) => Promise<unknown>,
    _options?: Record<string, unknown>,
  ) => ({}),
);
let mockAuthState = {
  isAuthenticated: true,
  userData: { id: "user-a" },
};

jest.mock("@/stores/authStore", () => ({
  __esModule: true,
  default: (selector: (state: typeof mockAuthState) => unknown) =>
    selector(mockAuthState),
}));

jest.mock("../../../api", () => ({
  api: { get: jest.fn() },
}));

jest.mock("../../../helpers/constants", () => ({
  getURL: jest.fn(() => "/api/v1/capabilities"),
}));

jest.mock("../../../services/request-processor", () => ({
  UseRequestProcessor: () => ({ query: mockQuery }),
}));

const mockApiGet = api.get as jest.Mock;

const summary = (index: number): CapabilitySummary => ({
  id: `00000000-0000-4000-8000-${index.toString().padStart(12, "0")}`,
  name: `Capability ${index}`,
  functional_area: "Operations",
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

const page = (
  items: CapabilitySummary[],
  total: number,
  offset: number,
): { data: CapabilityListResponse } => ({
  data: { items, total, offset, limit: 200 },
});

describe("fetchAllActiveCapabilities", () => {
  beforeEach(() => jest.clearAllMocks());

  it("loads every page sequentially and preserves API page order", async () => {
    const firstPage = Array.from({ length: 200 }, (_, index) => summary(index));
    const last = summary(200);
    mockApiGet
      .mockResolvedValueOnce(page(firstPage, 201, 0))
      .mockResolvedValueOnce(page([last], 201, 200));

    const result = await fetchAllActiveCapabilities();

    expect(result).toEqual([...firstPage, last]);
    expect(mockApiGet).toHaveBeenNthCalledWith(
      1,
      "/api/v1/capabilities",
      expect.objectContaining({
        params: { include_archived: false, offset: 0, limit: 200 },
      }),
    );
    expect(mockApiGet).toHaveBeenNthCalledWith(
      2,
      "/api/v1/capabilities",
      expect.objectContaining({
        params: { include_archived: false, offset: 200, limit: 200 },
      }),
    );
  });

  it("propagates a later-page failure instead of returning partial data", async () => {
    const failure = new Error("second page unavailable");
    mockApiGet
      .mockResolvedValueOnce(page([summary(0)], 2, 0))
      .mockRejectedValueOnce(failure);

    await expect(fetchAllActiveCapabilities()).rejects.toBe(failure);
  });

  it("rejects non-progressing pagination", async () => {
    mockApiGet.mockResolvedValueOnce(page([], 1, 0));

    await expect(fetchAllActiveCapabilities()).rejects.toBeInstanceOf(
      CapabilityPaginationError,
    );
  });

  it("rejects duplicate IDs across pages", async () => {
    const repeated = summary(0);
    mockApiGet
      .mockResolvedValueOnce(page([repeated], 2, 0))
      .mockResolvedValueOnce(page([repeated], 2, 1));

    await expect(fetchAllActiveCapabilities()).rejects.toThrow(
      "duplicate record",
    );
  });

  it("passes the cancellation signal to every request", async () => {
    const controller = new AbortController();
    mockApiGet.mockResolvedValueOnce(page([], 0, 0));

    await fetchAllActiveCapabilities(controller.signal);

    expect(mockApiGet).toHaveBeenCalledWith(
      "/api/v1/capabilities",
      expect.objectContaining({ signal: controller.signal }),
    );
  });
});

describe("useGetCapabilities", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthState = {
      isAuthenticated: true,
      userData: { id: "user-a" },
    };
  });

  it("scopes its cache key to the authenticated user", () => {
    const { rerender } = renderHook(() => useGetCapabilities());
    expect(mockQuery.mock.calls[0]![0]).toEqual([
      "capabilities",
      "list",
      "user-a",
      { includeArchived: false, pageSize: 200 },
    ]);

    mockAuthState = {
      isAuthenticated: true,
      userData: { id: "user-b" },
    };
    rerender();

    expect(mockQuery.mock.calls[1]![0]).toEqual([
      "capabilities",
      "list",
      "user-b",
      { includeArchived: false, pageSize: 200 },
    ]);
  });

  it("disables the query until authentication and user identity are ready", () => {
    mockAuthState = { isAuthenticated: false, userData: { id: "user-a" } };
    renderHook(() => useGetCapabilities());

    expect(mockQuery.mock.calls[0]![2]).toEqual(
      expect.objectContaining({ enabled: false }),
    );
  });
});
