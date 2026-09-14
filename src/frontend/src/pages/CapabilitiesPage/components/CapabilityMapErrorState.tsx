import { useTranslation } from "react-i18next";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export function CapabilityMapErrorState({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();

  return (
    <div className="flex h-full min-h-[28rem] items-center justify-center px-6">
      <Alert className="max-w-xl" variant="destructive">
        <AlertTitle>{t("capabilities.error.title")}</AlertTitle>
        <AlertDescription>
          <p>{t("capabilities.error.description")}</p>
          <Button
            className="mt-4"
            data-testid="capability-map-retry"
            onClick={onRetry}
            size="sm"
            variant="outline"
          >
            {t("capabilities.error.retry")}
          </Button>
        </AlertDescription>
      </Alert>
    </div>
  );
}
