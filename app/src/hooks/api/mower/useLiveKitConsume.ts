import { useMutation } from '@tanstack/react-query';
import { zenohQuery } from '@/config/zenohClient';
import { LiveKitTokenResponse } from '@/generated/zenoh';
import { livekitConsumePath } from '@/generated/zenohPaths';
import { reportAppError } from '@/errors/reporter';
import { InputValidationError, isInputValidationError } from '@/errors/types';

/** Requests a short-lived, consumer-only LiveKit credential over the authenticated Zenoh session. */
export function useLiveKitConsume() {
  return useMutation({
    mutationFn: async (mowerId: string) => {
      const normalizedMowerId = mowerId.trim();
      if (!normalizedMowerId)
        throw new InputValidationError('A mower must be selected to view its livestream');

      return zenohQuery<LiveKitTokenResponse>(livekitConsumePath(normalizedMowerId), {});
    },
    retry: false,
    gcTime: 0,
    onError: (error, mowerId) => {
      if (!isInputValidationError(error)) {
        reportAppError('livestream.connection_failed', error, {
          dedupeKey: `livestream.connection_failed:${mowerId.trim()}`,
        });
      }
    },
  });
}
