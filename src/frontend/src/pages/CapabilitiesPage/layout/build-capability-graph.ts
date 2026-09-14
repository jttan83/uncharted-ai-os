import { Position } from "@xyflow/react";
import type { CapabilitySummary } from "@/types/capabilities";
import type {
  CapabilityEdge,
  CapabilityGraph,
  CapabilityGraphDiagnostic,
  CapabilityMapNode,
  CapabilityNode,
  FunctionalAreaNode,
} from "../types";

export const CAPABILITY_MAP_ROOT_ID = "presentation:root";

export const toCapabilityNodeId = (id: string) => `capability:${id}`;

export const toFunctionalAreaNodeId = (functionalArea: string) =>
  `presentation:functional-area:${encodeURIComponent(functionalArea)}`;

const compareCodePoints = (left: string, right: string) =>
  left < right ? -1 : left > right ? 1 : 0;

export function comparePinnedLabels(left: string, right: string): number {
  const insensitive = compareCodePoints(
    left.toLowerCase(),
    right.toLowerCase(),
  );
  return insensitive || compareCodePoints(left, right);
}

function compareCapabilities(
  left: CapabilitySummary,
  right: CapabilitySummary,
): number {
  return (
    comparePinnedLabels(left.name, right.name) ||
    compareCodePoints(left.id, right.id)
  );
}

function relationCreatesCycle(
  capability: CapabilitySummary,
  capabilitiesById: Map<string, CapabilitySummary>,
): boolean {
  const visited = new Set<string>();
  let cursor = capability.parent_capability_id;

  while (cursor !== null) {
    if (cursor === capability.id) return true;
    if (visited.has(cursor)) return false;
    visited.add(cursor);
    cursor = capabilitiesById.get(cursor)?.parent_capability_id ?? null;
  }

  return false;
}

type Attachment = {
  source: string;
  kind: NonNullable<CapabilityEdge["data"]>["kind"];
};

function makeCapabilityNode(capability: CapabilitySummary): CapabilityNode {
  return {
    id: toCapabilityNodeId(capability.id),
    type: "capability",
    position: { x: 0, y: 0 },
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    data: { role: "capability", capability },
    draggable: false,
    connectable: false,
    deletable: false,
    selectable: true,
    focusable: false,
    ariaRole: "group",
  };
}

export function buildCapabilityGraph(
  records: readonly CapabilitySummary[],
  rootLabel: string,
): CapabilityGraph {
  const active = records
    .filter((capability) => capability.status === "active")
    .map((capability) => ({ ...capability }))
    .sort(compareCapabilities);
  const capabilitiesById = new Map(
    active.map((capability) => [capability.id, capability]),
  );
  const diagnostics: CapabilityGraphDiagnostic[] = [];
  const attachments = new Map<string, Attachment>();
  const groupedAreas = new Set<string>();

  for (const capability of active) {
    const parentId = capability.parent_capability_id;
    const parent =
      parentId === null ? undefined : capabilitiesById.get(parentId);
    const isCycle =
      parentId !== null && relationCreatesCycle(capability, capabilitiesById);

    if (parentId !== null && parent && !isCycle) {
      attachments.set(capability.id, {
        source: toCapabilityNodeId(parent.id),
        kind: "parent-capability",
      });
      continue;
    }

    const groupId = toFunctionalAreaNodeId(capability.functional_area);
    groupedAreas.add(capability.functional_area);
    attachments.set(capability.id, {
      source: groupId,
      kind: "group-capability",
    });

    if (parentId !== null) {
      diagnostics.push({
        capabilityId: capability.id,
        kind: isCycle ? "cycle" : "orphan",
        message: isCycle
          ? `Capability ${capability.id} was placed under its functional area because its hierarchy is cyclic.`
          : `Capability ${capability.id} was placed under its functional area because its parent is unavailable.`,
      });
    }
  }

  const areas = [...groupedAreas].sort(comparePinnedLabels);
  const nodes: CapabilityMapNode[] = [
    {
      id: CAPABILITY_MAP_ROOT_ID,
      type: "capabilityMapRoot",
      position: { x: 0, y: 0 },
      sourcePosition: Position.Bottom,
      data: { role: "root", label: rootLabel },
      draggable: false,
      connectable: false,
      deletable: false,
      selectable: false,
      focusable: false,
      ariaRole: "group",
    },
  ];
  const edges: CapabilityEdge[] = [];
  const childrenBySource = new Map<string, CapabilitySummary[]>();

  for (const capability of active) {
    const source = attachments.get(capability.id)?.source;
    if (!source) continue;
    const children = childrenBySource.get(source) ?? [];
    children.push(capability);
    childrenBySource.set(source, children);
  }

  const sourceQueue: string[] = [];
  for (const functionalArea of areas) {
    const groupId = toFunctionalAreaNodeId(functionalArea);
    const groupNode: FunctionalAreaNode = {
      id: groupId,
      type: "functionalArea",
      position: { x: 0, y: 0 },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      data: {
        role: "functional-area",
        label: functionalArea,
        functionalArea,
      },
      draggable: false,
      connectable: false,
      deletable: false,
      selectable: false,
      focusable: false,
      ariaRole: "group",
    };
    nodes.push(groupNode);
    edges.push({
      id: `edge:root:${groupId}`,
      type: "capabilityEdge",
      source: CAPABILITY_MAP_ROOT_ID,
      target: groupId,
      data: { kind: "root-group" },
      selectable: false,
      focusable: false,
      deletable: false,
      reconnectable: false,
    });
    sourceQueue.push(groupId);
  }

  for (let index = 0; index < sourceQueue.length; index += 1) {
    const source = sourceQueue[index];
    const children = (childrenBySource.get(source) ?? []).sort(
      compareCapabilities,
    );
    for (const capability of children) {
      const node = makeCapabilityNode(capability);
      nodes.push(node);
      const kind = attachments.get(capability.id)?.kind ?? "group-capability";
      edges.push({
        id:
          kind === "parent-capability"
            ? `edge:parent:${capability.parent_capability_id}:${capability.id}`
            : `edge:group:${source}:${capability.id}`,
        type: "capabilityEdge",
        source,
        target: node.id,
        data: { kind },
        selectable: false,
        focusable: false,
        deletable: false,
        reconnectable: false,
      });
      sourceQueue.push(node.id);
    }
  }

  return { nodes, edges, diagnostics };
}
