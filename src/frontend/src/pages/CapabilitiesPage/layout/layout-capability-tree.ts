import ELK, { type ElkNode } from "elkjs/lib/elk.bundled.js";
import type { CapabilityEdge, CapabilityMapNode } from "../types";

export const CAPABILITY_NODE_DIMENSIONS = {
  capabilityMapRoot: { width: 240, height: 64 },
  functionalArea: { width: 240, height: 56 },
  capability: { width: 280, height: 120 },
} as const;

const LAYOUT_OPTIONS = {
  "elk.algorithm": "layered",
  "elk.direction": "DOWN",
  "elk.layered.spacing.nodeNodeBetweenLayers": "72",
  "elk.spacing.nodeNode": "48",
  "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
  "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
  "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
} as const;

type ElkLayoutEngine = {
  layout(graph: ElkNode): Promise<ElkNode>;
};

const elk = new ELK();

export async function layoutCapabilityTree(
  nodes: readonly CapabilityMapNode[],
  edges: readonly CapabilityEdge[],
  engine: ElkLayoutEngine = elk,
): Promise<CapabilityMapNode[]> {
  const graph: ElkNode = {
    id: "capability-map-layout",
    layoutOptions: LAYOUT_OPTIONS,
    children: nodes.map((node) => ({
      id: node.id,
      ...CAPABILITY_NODE_DIMENSIONS[node.type],
    })),
    edges: edges.map((edge) => ({
      id: edge.id,
      sources: [edge.source],
      targets: [edge.target],
    })),
  };
  const layoutedGraph = await engine.layout(graph);
  const positions = new Map(
    layoutedGraph.children?.map((node) => [node.id, node]) ?? [],
  );

  return nodes.map((node) => {
    const layouted = positions.get(node.id);
    if (layouted?.x === undefined || layouted.y === undefined) {
      throw new Error(`ELK did not position Capability node ${node.id}.`);
    }
    const dimensions = CAPABILITY_NODE_DIMENSIONS[node.type];
    return {
      ...node,
      position: { x: layouted.x, y: layouted.y },
      width: dimensions.width,
      height: dimensions.height,
      style: { ...node.style, ...dimensions },
    };
  });
}

export type LayoutRequestCoordinator = {
  begin: () => number;
  isCurrent: (requestId: number) => boolean;
  invalidate: () => void;
};

export function createLayoutRequestCoordinator(): LayoutRequestCoordinator {
  let generation = 0;
  return {
    begin: () => {
      generation += 1;
      return generation;
    },
    isCurrent: (requestId) => requestId === generation,
    invalidate: () => {
      generation += 1;
    },
  };
}
