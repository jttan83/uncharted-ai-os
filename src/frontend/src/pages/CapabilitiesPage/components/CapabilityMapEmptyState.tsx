import { useTranslation } from "react-i18next";

export function CapabilityMapEmptyState() {
  const { t } = useTranslation();

  return (
    <section
      className="flex h-full min-h-[28rem] items-center justify-center rounded-xl border border-dashed border-border bg-muted/20 px-6 text-center"
      data-testid="capability-map-empty"
    >
      <div className="max-w-lg">
        <h2 className="text-lg font-semibold text-foreground">
          {t("capabilities.empty.title")}
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {t("capabilities.empty.description")}
        </p>
      </div>
    </section>
  );
}
