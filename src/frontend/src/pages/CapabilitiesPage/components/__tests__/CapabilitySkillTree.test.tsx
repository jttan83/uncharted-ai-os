import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { INITIAL_CAPABILITIES_FIXTURE } from "../../__fixtures__/initial-capabilities";
import type { CapabilityMapNode } from "../../types";
import { CapabilitySkillTree } from "../CapabilitySkillTree";

let capturedReactFlowProps: Record<string, unknown> | null = null;

jest.mock("@xyflow/react", () => {
  const React = require("react");
  return {
    ReactFlowProvider: ({ children }: { children: React.ReactNode }) =>
      children,
    ReactFlow: (props: {
      nodes: Array<{
        id: string;
        selectable?: boolean;
        data: {
          role: string;
          capability?: { id: string; name: string };
          onSelect?: (id: string) => void;
        };
      }>;
    }) => {
      capturedReactFlowProps = props;
      return React.createElement(
        "div",
        { "data-testid": "react-flow-mock" },
        props.nodes.map((node) =>
          React.createElement(
            "button",
            {
              "aria-label": node.data.capability?.name ?? node.id,
              disabled: !node.selectable,
              key: node.id,
              onClick: () =>
                node.data.capability &&
                node.data.onSelect?.(node.data.capability.id),
              type: "button",
            },
            node.id,
          ),
        ),
      );
    },
    Background: () => null,
    Controls: () => null,
    Handle: () => null,
    BaseEdge: () => null,
    Position: { Top: "top", Bottom: "bottom" },
    getSmoothStepPath: () => ["M0 0"],
  };
});

const immediateLayout = async <T,>(nodes: readonly T[]) => [...nodes];

describe("CapabilitySkillTree", () => {
  beforeEach(() => {
    capturedReactFlowProps = null;
  });

  it("is read-only and keyboard-selects only persisted Capability nodes", async () => {
    const user = userEvent.setup();
    const onCapabilitySelect = jest.fn();
    render(
      <CapabilitySkillTree
        capabilities={INITIAL_CAPABILITIES_FIXTURE}
        layoutGraph={immediateLayout}
        onCapabilitySelect={onCapabilitySelect}
        scopeKey="user-a"
      />,
    );

    const capabilityButton = await screen.findByRole("button", {
      name: "Proposal Builder",
    });
    capabilityButton.focus();
    await user.keyboard("{Enter}");

    expect(onCapabilitySelect).toHaveBeenCalledWith(
      INITIAL_CAPABILITIES_FIXTURE[0].id,
    );
    expect(
      screen.getByRole("button", { name: "presentation:root" }),
    ).toBeDisabled();
    expect(capturedReactFlowProps).toEqual(
      expect.objectContaining({
        connectOnClick: false,
        deleteKeyCode: null,
        edgesReconnectable: false,
        nodesConnectable: false,
        nodesDraggable: false,
      }),
    );
    expect(capturedReactFlowProps).not.toHaveProperty("onNodesChange");
    expect(capturedReactFlowProps).not.toHaveProperty("onConnect");
    expect(capturedReactFlowProps).not.toHaveProperty("onEdgesChange");
  });

  it("does not let a stale layout overwrite newer data", async () => {
    const resolvers: Array<(nodes: CapabilityMapNode[]) => void> = [];
    const layoutGraph = jest.fn(
      (_nodes: readonly CapabilityMapNode[]) =>
        new Promise<CapabilityMapNode[]>((resolve) => {
          resolvers.push(resolve);
        }),
    );
    const { rerender } = render(
      <CapabilitySkillTree
        capabilities={[INITIAL_CAPABILITIES_FIXTURE[0]]}
        layoutGraph={layoutGraph as never}
        onCapabilitySelect={jest.fn()}
        scopeKey="user-a"
      />,
    );
    rerender(
      <CapabilitySkillTree
        capabilities={[INITIAL_CAPABILITIES_FIXTURE[1]]}
        layoutGraph={layoutGraph as never}
        onCapabilitySelect={jest.fn()}
        scopeKey="user-a"
      />,
    );

    await waitFor(() => expect(resolvers).toHaveLength(2));
    await act(async () => {
      resolvers[1]([...layoutGraph.mock.calls[1]![0]]);
    });
    await screen.findByTestId("react-flow-mock");
    await act(async () => {
      resolvers[0]([...layoutGraph.mock.calls[0]![0]]);
    });

    expect(
      screen.getByRole("button", { name: "Workshop Architect" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Proposal Builder" }),
    ).not.toBeInTheDocument();
  });
});
