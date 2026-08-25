import { useQuery } from '@tanstack/react-query';
import type { TelemetryHistoryResponse } from '@/generated/zenoh';
import { zenohQuery } from '@/config/zenohClient';
import { getFirebaseIdToken } from '@/zenoh/UserLogin';

export const TELEMETRY_HISTORY_PAGE_SIZE = 60;

export function telemetryHistoryPath(mowerId: string, telemetryType: string) {
  return `mower/${mowerId}/telemetry/${telemetryType}/old`;
}

export function mowerTelemetryHistoryQueryKey(
  mowerId: string,
  telemetryType: string,
  cursor: string | null | undefined
) {
  return ['mower-telemetry-history', mowerId, telemetryType, cursor ?? null] as const;
}

interface UseMowerTelemetryHistoryOptions {
  mowerId: string;
  telemetryType: string;
  cursor?: string | null;
  enabled?: boolean;
}

/** Fetch one fixed-size historical graph page through the authenticated Zenoh session. */
export function useMowerTelemetryHistory({
  mowerId,
  telemetryType,
  cursor,
  enabled = true,
}: UseMowerTelemetryHistoryOptions) {
  const canFetch = enabled && Boolean(mowerId) && Boolean(telemetryType);

  const query = useQuery({
    queryKey: mowerTelemetryHistoryQueryKey(mowerId, telemetryType, cursor),
    enabled: canFetch,
    staleTime: 30_000,
    queryFn: async () => {
      const idToken = await getFirebaseIdToken();
      return zenohQuery<TelemetryHistoryResponse>(telemetryHistoryPath(mowerId, telemetryType), {
        id_token: idToken,
        cursor: cursor ?? null,
      });
    },
  });

  return { data: query.data ?? null, error: query.error, isFetching: query.isFetching };
}
