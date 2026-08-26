import { useQuery } from '@tanstack/react-query';
import type { TelemetryHistoryResponse } from '@/generated/zenoh';
import { mowerTelemetryHistoryPath } from '@/generated/zenohPaths';
import { getFirebaseIdToken } from '@/config/firebase';
import { zenohQuery } from '@/config/zenohClient';

export const TELEMETRY_HISTORY_PAGE_SIZE = 60;

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
      return zenohQuery<TelemetryHistoryResponse>(mowerTelemetryHistoryPath(mowerId, telemetryType), {
        id_token: idToken,
        cursor: cursor ?? null,
      });
    },
  });

  return { data: query.data ?? null, error: query.error, isFetching: query.isFetching };
}
