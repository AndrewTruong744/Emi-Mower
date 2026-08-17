import { useMutation } from '@tanstack/react-query';
import { zenohQuery } from '@/config/zenohClient';
import { LiveKitTokenResponse } from '@/generated/zenoh';

export function liveKitConsumePath(mowerId: string) {
  return `mower/${mowerId}/livekit/consume`;
}

/** Requests a short-lived, consumer-only LiveKit credential over the authenticated Zenoh session. */
export function useLiveKitConsume() {
  return useMutation({
    mutationFn: async (mowerId: string) => {
      const normalizedMowerId = mowerId.trim();
      if (!normalizedMowerId) throw new Error('A mower must be selected to view its livestream');

      return zenohQuery<LiveKitTokenResponse>(liveKitConsumePath(normalizedMowerId), {});
    },
  });
}
