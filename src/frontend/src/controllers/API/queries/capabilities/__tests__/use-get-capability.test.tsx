import { renderHook } from "@testing-library/react";
import { api } from "../../../api";
import { useGetCapability } from "../use-get-capability";

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

jest.mock("../../../api", () => ({ api: { get: jest.fn() } }));
jest.mock("../../../helpers/constants", () => ({
  getURL: jest.fn(() => "/api/v1/capabilities"),
}));
jest.mock("../../../services/request-processor", () => ({
  UseRequestProcessor: () => ({ query: mockQuery }),
}));

describe("useGetCapability", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthState = {
      isAuthenticated: true,
      userData: { id: "user-a" },
    };
  });

  it("uses an ID- and user-specific key and fetches full detail", async () => {
    renderHook(() => useGetCapability("capability-a", true));
    const [key, queryFn, options] = mockQuery.mock.calls[0]!;
    const signal = new AbortController().signal;
    (api.get as jest.Mock).mockResolvedValueOnce({
      data: { id: "capability-a" },
    });

    await queryFn?.({ signal });

    expect(key).toEqual(["capabilities", "detail", "user-a", "capability-a"]);
    expect(options).toEqual(
      expect.objectContaining({ enabled: true, refetchOnMount: "always" }),
    );
    expect(api.get).toHaveBeenCalledWith("/api/v1/capabilities/capability-a", {
      signal,
    });
  });

  it.each([
    [null, true],
    ["capability-a", false],
  ])("disables detail fetching for id=%s enabled=%s", (id, enabled) => {
    renderHook(() => useGetCapability(id, enabled));
    expect(mockQuery.mock.calls[0]![2]).toEqual(
      expect.objectContaining({ enabled: false }),
    );
  });

  it("separates cached details across account changes", () => {
    const { rerender } = renderHook(() =>
      useGetCapability("capability-a", true),
    );
    mockAuthState = {
      isAuthenticated: true,
      userData: { id: "user-b" },
    };
    rerender();

    expect(mockQuery.mock.calls[0]![0]?.[2]).toBe("user-a");
    expect(mockQuery.mock.calls[1]![0]?.[2]).toBe("user-b");
  });
});
