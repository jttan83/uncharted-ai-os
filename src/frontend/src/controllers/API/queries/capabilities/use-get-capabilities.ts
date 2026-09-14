import type { UseQueryResult } from "@tanstack/react-query";
import useAuthStore from "@/stores/authStore";
import type {
  CapabilityListResponse,
  CapabilitySummary,
} from "@/types/capabilities";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const CAPABILITY_PAGE_SIZE = 200;
export const CAPABILITIES_QUERY_KEY = "capabilities";

export class CapabilityPaginationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CapabilityPaginationError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export async function fetchAllActiveCapabilities(
  signal?: AbortSignal,
): Promise<CapabilitySummary[]> {
  const items: CapabilitySummary[] = [];
  const seenIds = new Set<string>();
  let expectedTotal: number | null = null;
  let offset = 0;

  while (expectedTotal === null || offset < expectedTotal) {
    const response = await api.get<CapabilityListResponse>(
      getURL("CAPABILITIES"),
      {
        params: {
          include_archived: false,
          offset,
          limit: CAPABILITY_PAGE_SIZE,
        },
        signal,
      },
    );
    const page = response.data;

    if (!Number.isInteger(page.total) || page.total < 0) {
      throw new CapabilityPaginationError(
        "The Capability API returned an invalid total.",
      );
    }
    if (page.offset !== offset) {
      throw new CapabilityPaginationError(
        "The Capability API returned an inconsistent offset.",
      );
    }
    if (expectedTotal === null) {
      expectedTotal = page.total;
    } else if (page.total !== expectedTotal) {
      throw new CapabilityPaginationError(
        "The Capability collection changed while it was being loaded.",
      );
    }
    if (page.items.length === 0 && offset < expectedTotal) {
      throw new CapabilityPaginationError(
        "Capability pagination stopped before the collection was complete.",
      );
    }
    if (page.items.length > CAPABILITY_PAGE_SIZE) {
      throw new CapabilityPaginationError(
        "The Capability API returned more records than requested.",
      );
    }

    for (const capability of page.items) {
      if (seenIds.has(capability.id)) {
        throw new CapabilityPaginationError(
          "The Capability API returned a duplicate record while paging.",
        );
      }
      seenIds.add(capability.id);
      items.push(capability);
    }

    offset += page.items.length;
    if (offset > expectedTotal) {
      throw new CapabilityPaginationError(
        "The Capability API returned an inconsistent page size.",
      );
    }
  }

  return items;
}

export function useGetCapabilities(): UseQueryResult<
  CapabilitySummary[],
  Error
> {
  const { query } = UseRequestProcessor();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const userId = useAuthStore((state) => state.userData?.id ?? null);
  const enabled = isAuthenticated && userId !== null;

  return query(
    [
      CAPABILITIES_QUERY_KEY,
      "list",
      userId,
      { includeArchived: false, pageSize: CAPABILITY_PAGE_SIZE },
    ],
    ({ signal }) => fetchAllActiveCapabilities(signal),
    {
      refetchOnWindowFocus: false,
      enabled,
    },
  ) as UseQueryResult<CapabilitySummary[], Error>;
}
