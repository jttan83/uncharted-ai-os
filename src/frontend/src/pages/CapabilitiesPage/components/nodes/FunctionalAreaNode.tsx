import { Handle, type NodeProps, Position } from "@xyflow/react";
import type { FunctionalAreaNode as FunctionalAreaNodeType } from "../../types";

export function FunctionalAreaNode({
  data,
}: NodeProps<FunctionalAreaNodeType>) {
  return (
    <div
      className="flex h-full w-full items-center justify-center rounded-xl border border-border bg-muted px-4 text-center text-sm font-semibold uppercase tracking-wide text-foreground shadow-sm"
      data-testid={`functional-area-node-${encodeURIComponent(data.functionalArea)}`}
    >
      <Handle
        aria-hidden="true"
        className="pointer-events-none !h-2 !w-2 !border-0 !bg-border"
        isConnectable={false}
        position={Position.Top}
        type="target"
      />
      {data.label}
      <Handle
        aria-hidden="true"
        className="pointer-events-none !h-2 !w-2 !border-0 !bg-border"
        isConnectable={false}
        position={Position.Bottom}
        type="source"
      />
    </div>
  );
}
