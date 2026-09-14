import type { UseQueryResult } from "@tanstack/react-query";
import useAuthStore from "@/stores/authStore";
import type { CapabilityRead } from "@/types/capabilities";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";
import { CAPABILITIES_QUERY_KEY } from "./use-get-capabilities";

export function useGetCapability(
  capabilityId: string | null,
  enabled: boolean,
): UseQueryResult<CapabilityRead, Error> {
  const { query } = UseRequestProcessor();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const userId = useAuthStore((state) => state.userData?.id ?? null);
  const queryEnabled =
    enabled && capabilityId !== null && isAuthenticated && userId !== null;

  return query(
    [CAPABILITIES_QUERY_KEY, "detail", userId, capabilityId],
    async ({ signal }) => {
      if (capabilityId === null) {
        throw new Error("A Capability ID is required.");
      }
      const response = await api.get<CapabilityRead>(
        `${getURL("CAPABILITIES")}/${capabilityId}`,
        { signal },
      );
      return response.data;
    },
    {
      refetchOnMount: "always",
      enabled: queryEnabled,
    },
  ) as UseQueryResult<CapabilityRead, Error>;
}
