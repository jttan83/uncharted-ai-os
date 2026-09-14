import { INITIAL_CAPABILITIES_FIXTURE } from "../../__fixtures__/initial-capabilities";
import { buildCapabilityGraph } from "../build-capability-graph";
import {
  CAPABILITY_NODE_DIMENSIONS,
  createLayoutRequestCoordinator,
  layoutCapabilityTree,
} from "../layout-capability-tree";

const overlaps = (
  left: { position: { x: number; y: number }; width?: number; height?: number },
  right: {
    position: { x: number; y: number };
    width?: number;
    height?: number;
  },
) =>
  left.position.x < right.position.x + (right.width ?? 0) &&
  left.position.x + (left.width ?? 0) > right.position.x &&
  left.position.y < right.position.y + (right.height ?? 0) &&
  left.position.y + (left.height ?? 0) > right.position.y;

describe("layoutCapabilityTree", () => {
  it("lays the hierarchy top-down with fixed, non-overlapping dimensions", async () => {
    const graph = buildCapabilityGraph(INITIAL_CAPABILITIES_FIXTURE, "Map");
    const before = JSON.parse(JSON.stringify(graph.nodes));
    const nodes = await layoutCapabilityTree(graph.nodes, graph.edges);
    const byId = new Map(nodes.map((node) => [node.id, node]));

    for (const edge of graph.edges) {
      const source = byId.get(edge.source);
      const target = byId.get(edge.target);
      expect(source).toBeDefined();
      expect(target).toBeDefined();
      expect((source?.position.y ?? 0) + (source?.height ?? 0)).toBeLessThan(
        target?.position.y ?? 0,
      );
    }

    for (let left = 0; left < nodes.length; left += 1) {
      expect(nodes[left].width).toBe(
        CAPABILITY_NODE_DIMENSIONS[nodes[left].type].width,
      );
      expect(nodes[left].height).toBe(
        CAPABILITY_NODE_DIMENSIONS[nodes[left].type].height,
      );
      for (let right = left + 1; right < nodes.length; right += 1) {
        expect(overlaps(nodes[left], nodes[right])).toBe(false);
      }
    }
    expect(graph.nodes).toEqual(before);
  });

  it("produces stable positions for shuffled source records", async () => {
    const forward = buildCapabilityGraph(INITIAL_CAPABILITIES_FIXTURE, "Map");
    const reverse = buildCapabilityGraph(
      [...INITIAL_CAPABILITIES_FIXTURE].reverse(),
      "Map",
    );
    const [first, second] = await Promise.all([
      layoutCapabilityTree(forward.nodes, forward.edges),
      layoutCapabilityTree(reverse.nodes, reverse.edges),
    ]);

    expect(second.map(({ id, position }) => ({ id, position }))).toEqual(
      first.map(({ id, position }) => ({ id, position })),
    );
  });
});

describe("createLayoutRequestCoordinator", () => {
  it("rejects stale asynchronous layout generations", () => {
    const coordinator = createLayoutRequestCoordinator();
    const first = coordinator.begin();
    const second = coordinator.begin();

    expect(coordinator.isCurrent(first)).toBe(false);
    expect(coordinator.isCurrent(second)).toBe(true);
    coordinator.invalidate();
    expect(coordinator.isCurrent(second)).toBe(false);
  });
});
