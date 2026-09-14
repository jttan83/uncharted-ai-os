import type { Edge, Node } from "@xyflow/react";
import type { CapabilitySummary } from "@/types/capabilities";

export type CapabilityMapRootNodeData = Record<string, unknown> & {
  role: "root";
  label: string;
};

export type FunctionalAreaNodeData = Record<string, unknown> & {
  role: "functional-area";
  label: string;
  functionalArea: string;
};

export type CapabilityNodeData = Record<string, unknown> & {
  role: "capability";
  capability: CapabilitySummary;
  onSelect?: (capabilityId: string) => void;
};

export type CapabilityMapRootNode = Node<
  CapabilityMapRootNodeData,
  "capabilityMapRoot"
>;

export type FunctionalAreaNode = Node<FunctionalAreaNodeData, "functionalArea">;

export type CapabilityNode = Node<CapabilityNodeData, "capability">;

export type CapabilityMapNode =
  | CapabilityMapRootNode
  | FunctionalAreaNode
  | CapabilityNode;

export type CapabilityEdgeData = Record<string, unknown> & {
  kind: "root-group" | "group-capability" | "parent-capability";
};

export type CapabilityEdge = Edge<CapabilityEdgeData, "capabilityEdge">;

export type CapabilityGraphDiagnostic = {
  capabilityId: string;
  kind: "orphan" | "cycle";
  message: string;
};

export type CapabilityGraph = {
  nodes: CapabilityMapNode[];
  edges: CapabilityEdge[];
  diagnostics: CapabilityGraphDiagnostic[];
};
