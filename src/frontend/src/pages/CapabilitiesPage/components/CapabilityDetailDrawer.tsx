import { useTranslation } from "react-i18next";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import type {
  CapabilityMaturity,
  CapabilityRead,
  FlowLinkAvailabilityStatus,
  FrequencyPeriod,
  HumanOversight,
} from "@/types/capabilities";
import { CapabilityMapErrorState } from "./CapabilityMapErrorState";
import { CapabilityMapLoadingState } from "./CapabilityMapLoadingState";

type CapabilityDetailDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  capability: CapabilityRead | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
};

type TranslationFunction = ReturnType<typeof useTranslation>["t"];

function DetailField({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="grid gap-1">
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="whitespace-pre-wrap break-words text-sm text-foreground">
        {value}
      </dd>
    </div>
  );
}

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="grid gap-4">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      <dl className="grid gap-4 sm:grid-cols-2">{children}</dl>
    </section>
  );
}

const maturityLabel = (t: TranslationFunction, value: CapabilityMaturity) =>
  t(`capabilities.maturity.${value}`);

const oversightLabel = (
  t: TranslationFunction,
  value: HumanOversight | null,
) => (value ? t(`capabilities.oversight.${value}`) : t("capabilities.notSet"));

const flowStatusLabel = (
  t: TranslationFunction,
  value: FlowLinkAvailabilityStatus,
) => t(`capabilities.flow.${value}`);

function formatFrequency(
  t: TranslationFunction,
  value: number | null,
  period: FrequencyPeriod | null,
) {
  if (period === null) return t("capabilities.notAssessed");
  if (period === "ad_hoc" || period === "unknown") {
    return t(`capabilities.frequency.${period}`);
  }
  if (value === null) return t("capabilities.notAssessed");
  return t("capabilities.frequency.value", {
    value,
    period: t(`capabilities.frequency.${period}`),
  });
}

function OrderedValues({ values, empty }: { values: string[]; empty: string }) {
  if (values.length === 0) return <span>{empty}</span>;
  return (
    <ol className="list-decimal space-y-1 pl-5">
      {values.map((value, index) => (
        <li key={`${index}:${value}`}>{value}</li>
      ))}
    </ol>
  );
}

export function CapabilityDetailDrawer({
  open,
  onOpenChange,
  capability,
  isLoading,
  isError,
  onRetry,
}: CapabilityDetailDrawerProps) {
  const { t } = useTranslation();
  const notSet = t("capabilities.notSet");
  const notAssessed = t("capabilities.notAssessed");

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent
        className="right-0 top-[3rem] h-[calc(100dvh-3rem)] w-full max-w-none rounded-l-xl rounded-r-none p-0 data-[state=closed]:slide-out-to-right-1/2 data-[state=open]:slide-in-from-right-1/2 sm:w-[32rem]"
        data-testid="capability-detail-drawer"
      >
        <DialogTitle className="sr-only">
          {capability?.name ?? t("capabilities.drawer.title")}
        </DialogTitle>
        <DialogDescription className="sr-only">
          {t("capabilities.drawer.description")}
        </DialogDescription>

        {isLoading ? (
          <CapabilityMapLoadingState />
        ) : isError ? (
          <CapabilityMapErrorState onRetry={onRetry} />
        ) : capability ? (
          <div className="flex h-full flex-col overflow-hidden">
            <header className="border-b border-border px-6 py-5 pr-12">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {t("capabilities.drawer.eyebrow")}
              </p>
              <h2 className="mt-1 text-xl font-semibold text-foreground">
                {capability.name}
              </h2>
            </header>
            <div className="flex-1 space-y-6 overflow-y-auto px-6 py-5">
              <DetailSection title={t("capabilities.sections.identity")}>
                <DetailField
                  label={t("capabilities.fields.name")}
                  value={capability.name}
                />
                <DetailField
                  label={t("capabilities.fields.functionalArea")}
                  value={capability.functional_area}
                />
                <DetailField
                  label={t("capabilities.fields.status")}
                  value={t(`capabilities.status.${capability.status}`)}
                />
                <DetailField
                  label={t("capabilities.fields.description")}
                  value={capability.description ?? notSet}
                />
              </DetailSection>
              <Separator />
              <DetailSection title={t("capabilities.sections.transformation")}>
                <DetailField
                  label={t("capabilities.fields.currentMaturity")}
                  value={maturityLabel(t, capability.current_maturity)}
                />
                <DetailField
                  label={t("capabilities.fields.targetMaturity")}
                  value={
                    capability.target_maturity
                      ? maturityLabel(t, capability.target_maturity)
                      : notSet
                  }
                />
                <DetailField
                  label={t("capabilities.fields.humanOversight")}
                  value={oversightLabel(t, capability.human_oversight)}
                />
                <DetailField
                  label={t("capabilities.fields.oversightNotes")}
                  value={capability.oversight_notes ?? notSet}
                />
              </DetailSection>
              <Separator />
              <DetailSection title={t("capabilities.sections.economics")}>
                <DetailField
                  label={t("capabilities.fields.frequency")}
                  value={formatFrequency(
                    t,
                    capability.frequency_value,
                    capability.frequency_period,
                  )}
                />
                <DetailField
                  label={t("capabilities.fields.baselineEffort")}
                  value={
                    capability.baseline_human_effort_minutes_per_run === null
                      ? notSet
                      : t("capabilities.effort.minutes", {
                          minutes:
                            capability.baseline_human_effort_minutes_per_run,
                        })
                  }
                />
              </DetailSection>
              <Separator />
              <DetailSection title={t("capabilities.sections.assessment")}>
                {(
                  [
                    ["businessValue", capability.business_value],
                    ["aiFeasibility", capability.ai_feasibility],
                    ["aiExecutionRisk", capability.ai_execution_risk],
                  ] as const
                ).map(([field, score]) => (
                  <DetailField
                    key={field}
                    label={t(`capabilities.fields.${field}`)}
                    value={
                      score === null
                        ? notAssessed
                        : t("capabilities.assessment.score", { score })
                    }
                  />
                ))}
                <DetailField
                  label={t("capabilities.fields.assessmentNotes")}
                  value={capability.assessment_notes ?? notSet}
                />
              </DetailSection>
              <Separator />
              <DetailSection title={t("capabilities.sections.context")}>
                {(
                  [
                    ["inputs", capability.inputs],
                    ["outputs", capability.outputs],
                    ["tools", capability.tools],
                  ] as const
                ).map(([field, values]) => (
                  <DetailField
                    key={field}
                    label={t(`capabilities.fields.${field}`)}
                    value={
                      <OrderedValues
                        empty={t("capabilities.emptyList")}
                        values={values}
                      />
                    }
                  />
                ))}
              </DetailSection>
              <Separator />
              <DetailSection title={t("capabilities.sections.langflow")}>
                <DetailField
                  label={t("capabilities.fields.primaryFlowId")}
                  value={capability.primary_flow_id ?? notSet}
                />
                <DetailField
                  label={t("capabilities.fields.flowStatus")}
                  value={flowStatusLabel(
                    t,
                    capability.primary_flow_link.status,
                  )}
                />
                {capability.primary_flow_link.status === "available" &&
                  capability.primary_flow_link.flow && (
                    <DetailField
                      label={t("capabilities.fields.flowName")}
                      value={capability.primary_flow_link.flow.name}
                    />
                  )}
              </DetailSection>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
