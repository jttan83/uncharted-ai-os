import { BaseEdge, type EdgeProps, getSmoothStepPath } from "@xyflow/react";
import type { CapabilityEdge as CapabilityEdgeType } from "../types";

export function CapabilityEdge({
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
  markerEnd,
}: EdgeProps<CapabilityEdgeType>) {
  const [path] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 12,
  });

  return (
    <g
      ref={(group) =>
        group?.ownerSVGElement?.setAttribute("aria-hidden", "true")
      }
    >
      <BaseEdge
        aria-hidden="true"
        markerEnd={markerEnd}
        path={path}
        style={{ stroke: "hsl(var(--border))", strokeWidth: 1.5 }}
      />
    </g>
  );
}
