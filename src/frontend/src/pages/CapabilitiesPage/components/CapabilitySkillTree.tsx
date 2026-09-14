import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  type NodeTypes,
} from "@xyflow/react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { CapabilitySummary } from "@/types/capabilities";
import type {
  CapabilityEdge as CapabilityEdgeType,
  CapabilityMapNode,
  CapabilityNode as CapabilityGraphNode,
} from "../types";
import { buildCapabilityGraph } from "../layout/build-capability-graph";
import {
  createLayoutRequestCoordinator,
  layoutCapabilityTree,
  type LayoutRequestCoordinator,
} from "../layout/layout-capability-tree";
import { CapabilityEdge } from "./CapabilityEdge";
import { CapabilityMapErrorState } from "./CapabilityMapErrorState";
import { CapabilityMapLoadingState } from "./CapabilityMapLoadingState";
import { CapabilityNode } from "./nodes/CapabilityNode";
import { CapabilityMapRootNode } from "./nodes/CapabilityMapRootNode";
import { FunctionalAreaNode } from "./nodes/FunctionalAreaNode";

const nodeTypes: NodeTypes = {
  capabilityMapRoot: CapabilityMapRootNode,
  functionalArea: FunctionalAreaNode,
  capability: CapabilityNode,
};

const edgeTypes = { capabilityEdge: CapabilityEdge };

const isCapabilityNode = (
  node: CapabilityMapNode,
): node is CapabilityGraphNode => node.type === "capability";

type CompleteLayout = {
  scopeKey: string;
  signature: string;
  nodes: CapabilityMapNode[];
  edges: CapabilityEdgeType[];
};

export type CapabilitySkillTreeProps = {
  capabilities: readonly CapabilitySummary[];
  scopeKey: string;
  onCapabilitySelect: (capabilityId: string) => void;
  layoutGraph?: typeof layoutCapabilityTree;
};

export function CapabilitySkillTree({
  capabilities,
  scopeKey,
  onCapabilitySelect,
  layoutGraph = layoutCapabilityTree,
}: CapabilitySkillTreeProps) {
  const { t } = useTranslation();
  const graph = useMemo(
    () => buildCapabilityGraph(capabilities, t("capabilities.map.rootLabel")),
    [capabilities, t],
  );
  const signature = useMemo(
    () =>
      JSON.stringify({
        nodes: graph.nodes.map((node) => [node.id, node.data]),
        edges: graph.edges.map((edge) => [edge.id, edge.source, edge.target]),
      }),
    [graph],
  );
  const coordinatorRef = useRef<LayoutRequestCoordinator | null>(null);
  if (coordinatorRef.current === null) {
    coordinatorRef.current = createLayoutRequestCoordinator();
  }
  const [retryGeneration, setRetryGeneration] = useState(0);
  const [completeLayout, setCompleteLayout] = useState<CompleteLayout | null>(
    null,
  );
  const [layoutError, setLayoutError] = useState<Error | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    for (const diagnostic of graph.diagnostics) {
      console.warn(`[Capability Map] ${diagnostic.message}`);
    }
  }, [graph.diagnostics]);

  useEffect(() => {
    const coordinator = coordinatorRef.current;
    if (!coordinator) return;
    const requestId = coordinator.begin();
    setLayoutError(null);

    layoutGraph(graph.nodes, graph.edges)
      .then((nodes) => {
        if (!coordinator.isCurrent(requestId)) return;
        setCompleteLayout({
          scopeKey,
          signature,
          nodes,
          edges: graph.edges,
        });
      })
      .catch((error: unknown) => {
        if (!coordinator.isCurrent(requestId)) return;
        setLayoutError(
          error instanceof Error
            ? error
            : new Error("Capability layout failed"),
        );
      });

    return () => coordinator.invalidate();
  }, [
    graph.edges,
    graph.nodes,
    layoutGraph,
    retryGeneration,
    scopeKey,
    signature,
  ]);

  const visibleLayout =
    completeLayout?.scopeKey === scopeKey ? completeLayout : null;
  const currentLayout =
    visibleLayout?.signature === signature ? visibleLayout : null;

  const interactiveNodes = useMemo(
    () =>
      currentLayout?.nodes.map(
        (node): CapabilityMapNode =>
          isCapabilityNode(node)
            ? {
                ...node,
                data: { ...node.data, onSelect: onCapabilitySelect },
              }
            : node,
      ) ?? [],
    [currentLayout, onCapabilitySelect],
  );

  useLayoutEffect(() => {
    if (!currentLayout) return;
    const decorativeGraphics = canvasRef.current?.querySelectorAll(
      ".react-flow__edges > svg, .react-flow__background",
    );
    decorativeGraphics?.forEach((graphic) =>
      graphic.setAttribute("aria-hidden", "true"),
    );
    canvasRef.current
      ?.querySelector(".react-flow__controls")
      ?.setAttribute("role", "group");
  }, [currentLayout]);

  if (layoutError && !currentLayout) {
    return (
      <CapabilityMapErrorState
        onRetry={() => setRetryGeneration((value) => value + 1)}
      />
    );
  }

  if (!currentLayout) {
    return <CapabilityMapLoadingState />;
  }

  return (
    <div
      ref={canvasRef}
      aria-busy={visibleLayout?.signature !== signature}
      className="h-full min-h-[28rem] w-full overflow-hidden rounded-xl border border-border bg-background"
      data-testid="capability-skill-tree"
    >
      <ReactFlowProvider>
        <ReactFlow<CapabilityMapNode, CapabilityEdgeType>
          aria-label={t("capabilities.map.canvasAriaLabel")}
          connectOnClick={false}
          deleteKeyCode={null}
          edges={currentLayout.edges}
          edgesFocusable={false}
          edgesReconnectable={false}
          edgeTypes={edgeTypes}
          elementsSelectable
          fitView
          fitViewOptions={{ padding: 0.16 }}
          maxZoom={1.5}
          minZoom={0.2}
          nodes={interactiveNodes}
          nodesConnectable={false}
          nodesDraggable={false}
          nodesFocusable
          nodeTypes={nodeTypes}
          panOnDrag
          proOptions={{ hideAttribution: true }}
          zoomOnDoubleClick={false}
        >
          <Background gap={24} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
