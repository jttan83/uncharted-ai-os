import { fireEvent, render, screen } from "@testing-library/react";
import { INITIAL_CAPABILITIES_FIXTURE } from "../__fixtures__/initial-capabilities";
import CapabilitiesPage from "../index";

const mockListRefetch = jest.fn();
const mockDetailRefetch = jest.fn();
const mockUseGetCapabilities = jest.fn();
const mockUseGetCapability = jest.fn();
let mockUserId = "user-a";

jest.mock("@/stores/authStore", () => ({
  __esModule: true,
  default: (selector: (state: { userData: { id: string } }) => unknown) =>
    selector({ userData: { id: mockUserId } }),
}));

jest.mock("@/controllers/API/queries/capabilities", () => ({
  useGetCapabilities: () => mockUseGetCapabilities(),
  useGetCapability: (id: string | null, enabled: boolean) =>
    mockUseGetCapability(id, enabled),
}));

jest.mock("../components/CapabilitySkillTree", () => ({
  CapabilitySkillTree: ({
    capabilities,
    onCapabilitySelect,
  }: {
    capabilities: typeof INITIAL_CAPABILITIES_FIXTURE;
    onCapabilitySelect: (id: string) => void;
  }) => (
    <button
      type="button"
      onClick={() => onCapabilitySelect(capabilities[0].id)}
    >
      Select {capabilities[0].name}
    </button>
  ),
}));

jest.mock("../components/CapabilityDetailDrawer", () => ({
  CapabilityDetailDrawer: ({
    open,
    capability,
  }: {
    open: boolean;
    capability?: { name: string; description?: string | null };
  }) =>
    open ? (
      <div data-testid="drawer">{capability?.name ?? "loading"}</div>
    ) : null,
}));

const listState = (overrides: Record<string, unknown> = {}) => ({
  data: INITIAL_CAPABILITIES_FIXTURE,
  isLoading: false,
  isFetching: false,
  isError: false,
  refetch: mockListRefetch,
  ...overrides,
});

const detailState = (overrides: Record<string, unknown> = {}) => ({
  data: undefined,
  isLoading: false,
  isFetching: false,
  isError: false,
  refetch: mockDetailRefetch,
  ...overrides,
});

describe("CapabilitiesPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUserId = "user-a";
    mockUseGetCapabilities.mockReturnValue(listState());
    mockUseGetCapability.mockReturnValue(detailState());
  });

  it("renders loading, empty, and error states without sample fallback", () => {
    mockUseGetCapabilities.mockReturnValue(listState({ isLoading: true }));
    const { rerender } = render(<CapabilitiesPage />);
    expect(screen.getByTestId("capability-map-loading")).toBeInTheDocument();

    mockUseGetCapabilities.mockReturnValue(listState({ data: [] }));
    rerender(<CapabilitiesPage />);
    expect(screen.getByTestId("capability-map-empty")).toBeInTheDocument();
    expect(screen.queryByText("Proposal Builder")).not.toBeInTheDocument();

    mockUseGetCapabilities.mockReturnValue(listState({ isError: true }));
    rerender(<CapabilitiesPage />);
    fireEvent.click(screen.getByTestId("capability-map-retry"));
    expect(mockListRefetch).toHaveBeenCalledTimes(1);
  });

  it("requests full detail only after a persisted Capability is selected", () => {
    render(<CapabilitiesPage />);
    expect(mockUseGetCapability).toHaveBeenLastCalledWith(null, false);

    fireEvent.click(
      screen.getByRole("button", { name: "Select Proposal Builder" }),
    );

    expect(mockUseGetCapability).toHaveBeenLastCalledWith(
      INITIAL_CAPABILITIES_FIXTURE[0].id,
      true,
    );
    expect(screen.getByTestId("drawer")).toHaveTextContent("loading");
  });

  it("clears selection when the authenticated account changes", () => {
    const { rerender } = render(<CapabilitiesPage />);
    fireEvent.click(
      screen.getByRole("button", { name: "Select Proposal Builder" }),
    );
    expect(screen.getByTestId("drawer")).toBeInTheDocument();

    mockUserId = "user-b";
    rerender(<CapabilitiesPage />);

    expect(screen.queryByTestId("drawer")).not.toBeInTheDocument();
    expect(mockUseGetCapability).toHaveBeenLastCalledWith(null, false);
  });
});
