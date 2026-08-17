import { useQuery } from '@tanstack/react-query';
import { TelemetryHistoryResponse } from '@/generated/zenoh';
import { zenohQuery } from '@/config/zenohClient';
import { getFirebaseIdToken } from '@/zenoh/UserLogin';

export const TELEMETRY_HISTORY_PAGE_SIZE = 60;

export function mowerTelemetryHistoryKey(mowerId: string, telemetryType: string, cursor?: string | null) {
  return ['mower', mowerId, 'telemetry', telemetryType, 'old', cursor ?? null] as const;
}

export function telemetryHistoryPath(mowerId: string, telemetryType: string) {
  return `mower/${mowerId}/telemetry/${telemetryType}/old`;
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
  return useQuery({
    queryKey: mowerTelemetryHistoryKey(mowerId, telemetryType, cursor),
    enabled: enabled && Boolean(mowerId) && Boolean(telemetryType),
    queryFn: async () => {
      const idToken = await getFirebaseIdToken();
      return zenohQuery<TelemetryHistoryResponse>(telemetryHistoryPath(mowerId, telemetryType), {
        id_token: idToken,
        cursor: cursor ?? null,
      });
    },
  });
}
