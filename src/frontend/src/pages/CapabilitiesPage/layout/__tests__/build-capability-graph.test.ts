import type { CapabilitySummary } from "@/types/capabilities";
import { INITIAL_CAPABILITIES_FIXTURE } from "../../__fixtures__/initial-capabilities";
import {
  buildCapabilityGraph,
  CAPABILITY_MAP_ROOT_ID,
  toCapabilityNodeId,
  toFunctionalAreaNodeId,
} from "../build-capability-graph";

const makeCapability = (
  id: string,
  name: string,
  functionalArea: string,
  parentCapabilityId: string | null = null,
): CapabilitySummary => ({
  ...INITIAL_CAPABILITIES_FIXTURE[0],
  id,
  name,
  functional_area: functionalArea,
  parent_capability_id: parentCapabilityId,
});

describe("buildCapabilityGraph", () => {
  it("builds one presentation root and the five fixture branches", () => {
    const graph = buildCapabilityGraph(
      INITIAL_CAPABILITIES_FIXTURE,
      "My Capability Map",
    );

    expect(
      graph.nodes.filter((node) => node.data.role === "root"),
    ).toHaveLength(1);
    expect(
      graph.nodes.filter((node) => node.data.role === "functional-area"),
    ).toHaveLength(5);
    expect(
      graph.nodes.filter((node) => node.data.role === "capability"),
    ).toHaveLength(5);
    expect(graph.edges).toHaveLength(10);
    expect(graph.nodes[0].id).toBe(CAPABILITY_MAP_ROOT_ID);

    for (const capability of INITIAL_CAPABILITIES_FIXTURE) {
      expect(graph.edges).toContainEqual(
        expect.objectContaining({
          source: toFunctionalAreaNodeId(capability.functional_area),
          target: toCapabilityNodeId(capability.id),
        }),
      );
    }
  });

  it("keeps descendants beneath persisted parents across functional areas", () => {
    const parent = makeCapability("parent", "Proposal Development", "Clients");
    const child = makeCapability(
      "child",
      "Proposal Builder",
      "Research",
      parent.id,
    );
    const graph = buildCapabilityGraph([child, parent], "Map");

    expect(graph.edges).toContainEqual(
      expect.objectContaining({
        source: toCapabilityNodeId(parent.id),
        target: toCapabilityNodeId(child.id),
      }),
    );
    expect(
      graph.nodes.some(
        (node) => node.id === toFunctionalAreaNodeId("Research"),
      ),
    ).toBe(false);
  });

  it("falls an orphan back to its own area without mutating the record", () => {
    const orphan = makeCapability("orphan", "Orphan", "Operations", "missing");
    const before = JSON.parse(JSON.stringify(orphan));
    const graph = buildCapabilityGraph([orphan], "Map");

    expect(graph.edges).toContainEqual(
      expect.objectContaining({
        source: toFunctionalAreaNodeId("Operations"),
        target: toCapabilityNodeId(orphan.id),
      }),
    );
    expect(graph.diagnostics).toEqual([
      expect.objectContaining({ capabilityId: orphan.id, kind: "orphan" }),
    ]);
    expect(orphan).toEqual(before);
  });

  it("contains malformed cycles without recursing indefinitely", () => {
    const first = makeCapability("a", "A", "Clients", "b");
    const second = makeCapability("b", "B", "Clients", "a");
    const descendant = makeCapability("c", "C", "Research", "a");
    const graph = buildCapabilityGraph([first, second, descendant], "Map");

    expect(
      graph.nodes.filter((node) => node.data.role === "capability"),
    ).toHaveLength(3);
    expect(
      graph.diagnostics.map(({ capabilityId }) => capabilityId).sort(),
    ).toEqual(["a", "b"]);
    expect(graph.edges).toContainEqual(
      expect.objectContaining({
        source: toCapabilityNodeId("a"),
        target: toCapabilityNodeId("c"),
      }),
    );
  });

  it("is deterministic for shuffled input and uses only Capability nodes as selectable", () => {
    const forward = buildCapabilityGraph(INITIAL_CAPABILITIES_FIXTURE, "Map");
    const reverse = buildCapabilityGraph(
      [...INITIAL_CAPABILITIES_FIXTURE].reverse(),
      "Map",
    );

    expect(reverse).toEqual(forward);
    for (const node of forward.nodes) {
      expect(node.selectable).toBe(node.data.role === "capability");
    }
  });
});
