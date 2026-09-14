import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useGetCapabilities,
  useGetCapability,
} from "@/controllers/API/queries/capabilities";
import useAuthStore from "@/stores/authStore";
import { CapabilityDetailDrawer } from "./components/CapabilityDetailDrawer";
import { CapabilityMapEmptyState } from "./components/CapabilityMapEmptyState";
import { CapabilityMapErrorState } from "./components/CapabilityMapErrorState";
import { CapabilityMapLoadingState } from "./components/CapabilityMapLoadingState";
import { CapabilitySkillTree } from "./components/CapabilitySkillTree";

export default function CapabilitiesPage() {
  const { t } = useTranslation();
  const userId = useAuthStore((state) => state.userData?.id ?? null);
  const [selectedCapabilityId, setSelectedCapabilityId] = useState<
    string | null
  >(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const capabilitiesQuery = useGetCapabilities();
  const detailQuery = useGetCapability(
    selectedCapabilityId,
    drawerOpen && selectedCapabilityId !== null,
  );
  const selectedCapability =
    detailQuery.data?.id === selectedCapabilityId
      ? detailQuery.data
      : undefined;

  useEffect(() => {
    setSelectedCapabilityId(null);
    setDrawerOpen(false);
  }, [userId]);

  const handleCapabilitySelect = (capabilityId: string) => {
    setSelectedCapabilityId(capabilityId);
    setDrawerOpen(true);
  };

  const handleDrawerOpenChange = (open: boolean) => {
    setDrawerOpen(open);
    if (!open) setSelectedCapabilityId(null);
  };

  return (
    <main
      aria-busy={capabilitiesQuery.isLoading || capabilitiesQuery.isFetching}
      className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-background"
      data-testid="capabilities-page"
    >
      <header className="shrink-0 border-b border-border px-6 py-4">
        <h1 className="text-xl font-semibold text-foreground">
          {t("capabilities.page.title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("capabilities.page.description")}
        </p>
      </header>
      <div className="min-h-0 flex-1 p-4 md:p-6">
        {capabilitiesQuery.isLoading ? (
          <CapabilityMapLoadingState />
        ) : capabilitiesQuery.isError ? (
          <CapabilityMapErrorState
            onRetry={() => void capabilitiesQuery.refetch()}
          />
        ) : capabilitiesQuery.data?.length ? (
          <CapabilitySkillTree
            capabilities={capabilitiesQuery.data}
            onCapabilitySelect={handleCapabilitySelect}
            scopeKey={userId ?? "anonymous"}
          />
        ) : (
          <CapabilityMapEmptyState />
        )}
      </div>
      <CapabilityDetailDrawer
        capability={selectedCapability}
        isError={detailQuery.isError}
        isLoading={detailQuery.isLoading || detailQuery.isFetching}
        onOpenChange={handleDrawerOpenChange}
        onRetry={() => void detailQuery.refetch()}
        open={drawerOpen}
      />
    </main>
  );
}
