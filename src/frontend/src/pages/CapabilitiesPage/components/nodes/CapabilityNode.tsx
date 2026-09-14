import { Handle, type NodeProps, Position } from "@xyflow/react";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/utils";
import type { CapabilityNode as CapabilityNodeType } from "../../types";

const maturityClasses = {
  not_assessed: "border-border bg-muted text-muted-foreground",
  manual: "border-muted-foreground/30 bg-background text-foreground",
  ai_assisted:
    "border-accent-blue-foreground/30 bg-accent-blue text-accent-blue-foreground",
  ai_executable:
    "border-accent-purple-muted-foreground/30 bg-accent-purple-muted text-accent-purple-muted-foreground",
  automated:
    "border-accent-amber-foreground/40 bg-accent-amber text-accent-amber-foreground",
} as const;

export function CapabilityNode({
  data,
  selected,
}: NodeProps<CapabilityNodeType>) {
  const { t } = useTranslation();
  const { capability } = data;

  return (
    <div
      className={cn(
        "h-full w-full rounded-xl border bg-background shadow-sm transition-shadow",
        selected
          ? "border-primary ring-2 ring-primary/25"
          : "border-border hover:shadow-md",
      )}
      data-testid={`capability-node-${capability.id}`}
    >
      <Handle
        aria-hidden="true"
        className="pointer-events-none !h-2 !w-2 !border-0 !bg-border"
        isConnectable={false}
        position={Position.Top}
        type="target"
      />
      <button
        className="nodrag nopan flex h-full w-full flex-col rounded-xl p-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
        onClick={() => data.onSelect?.(capability.id)}
        type="button"
      >
        <span className="line-clamp-2 min-h-10 text-sm font-semibold leading-5 text-foreground">
          {capability.name}
        </span>
        <span className="mt-2 flex min-w-0 items-center gap-2">
          <Badge
            className={cn(
              "max-w-full border px-2 py-0.5 text-[11px] leading-4",
              maturityClasses[capability.current_maturity],
            )}
            size="tag"
            variant="outline"
          >
            {t(`capabilities.maturity.${capability.current_maturity}`)}
          </Badge>
        </span>
        <span className="mt-auto flex min-w-0 items-center justify-between gap-2 pt-2 text-[11px] text-muted-foreground">
          <span className="truncate">
            {capability.target_maturity
              ? t("capabilities.node.target", {
                  maturity: t(
                    `capabilities.maturity.${capability.target_maturity}`,
                  ),
                })
              : t("capabilities.node.noTarget")}
          </span>
          <span className="shrink-0">
            {t(`capabilities.flow.${capability.primary_flow_link.status}`)}
          </span>
        </span>
      </button>
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
