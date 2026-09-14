import { Handle, type NodeProps, Position } from "@xyflow/react";
import type { CapabilityMapRootNode as CapabilityMapRootNodeType } from "../../types";

export function CapabilityMapRootNode({
  data,
}: NodeProps<CapabilityMapRootNodeType>) {
  return (
    <div
      className="flex h-full w-full items-center justify-center rounded-2xl border border-primary/30 bg-primary px-5 text-center text-base font-semibold text-primary-foreground shadow-md"
      data-testid="capability-map-root-node"
    >
      {data.label}
      <Handle
        aria-hidden="true"
        className="pointer-events-none !h-2 !w-2 !border-0 !bg-primary-foreground/70"
        isConnectable={false}
        position={Position.Bottom}
        type="source"
      />
    </div>
  );
}
