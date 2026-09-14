import { useTranslation } from "react-i18next";
import { Skeleton } from "@/components/ui/skeleton";

export function CapabilityMapLoadingState() {
  const { t } = useTranslation();

  return (
    <div
      aria-live="polite"
      className="flex h-full min-h-[28rem] w-full flex-col items-center gap-10 overflow-hidden rounded-xl border border-border bg-background p-8"
      data-testid="capability-map-loading"
      role="status"
    >
      <span className="sr-only">{t("capabilities.loading")}</span>
      <Skeleton className="h-16 w-60 rounded-2xl" />
      <div className="flex w-full max-w-5xl justify-around gap-8">
        {[0, 1, 2].map((column) => (
          <div className="flex w-72 flex-col items-center gap-8" key={column}>
            <Skeleton className="h-14 w-60 rounded-xl" />
            <Skeleton className="h-28 w-72 rounded-xl" />
          </div>
        ))}
      </div>
    </div>
  );
}
