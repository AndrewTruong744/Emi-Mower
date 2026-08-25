import { reportAppError } from '@/errors/reporter';
import { ACTIVE_TELEMETRY_FLUSH_MS, TelemetryBuffer } from '@/hooks/mowers/telemetryBuffer';
import { useBoundStore } from '@/store/useBoundStore';
import { subscribeToMowerTelemetry } from './mowerTelemetry';

function isCurrentAuthGeneration(authGeneration: number): boolean {
  const { authGeneration: currentGeneration, zenohEnabled } = useBoundStore.getState();
  return zenohEnabled && currentGeneration === authGeneration;
}

/**
 * Establishes the app's required mower telemetry stream for one authenticated
 * Zenoh session. Auth bootstrap awaits this before exposing authenticated routes.
 */
export async function initializeMowerTelemetrySubscription(authGeneration: number): Promise<void> {
  if (useBoundStore.getState().mowers.length === 0) return;

  const buffer = new TelemetryBuffer();
  let flushInterval: ReturnType<typeof setInterval> | undefined;
  const stopBuffer = () => {
    if (flushInterval) clearInterval(flushInterval);
    flushInterval = undefined;
    buffer.clear();
  };

  const unsubscribe = await subscribeToMowerTelemetry(
    (messages) => {
      if (!isCurrentAuthGeneration(authGeneration)) return;

      const { mowers } = useBoundStore.getState();
      const mowerIds = new Set(mowers);
      for (const { mowerId, sample } of messages) {
        if (!mowerIds.has(mowerId)) continue;
        if (buffer.enqueue(mowerId, sample)) {
          reportAppError(
            'telemetry.delayed',
            new Error(`Telemetry queue reached its limit for mower ${mowerId}`),
            { dedupeKey: `telemetry.delayed:${mowerId}` }
          );
        }
      }
    },
    (error) => reportAppError('telemetry.invalid_payload', error),
    stopBuffer
  );

  if (!isCurrentAuthGeneration(authGeneration)) {
    await unsubscribe();
    return;
  }

  flushInterval = setInterval(() => {
    if (!isCurrentAuthGeneration(authGeneration)) {
      stopBuffer();
      return;
    }

    const { appendTelemetryBatch, selectedMowerUuid } = useBoundStore.getState();
    const batch = buffer.flush(selectedMowerUuid, Date.now());
    if (Object.keys(batch).length > 0) appendTelemetryBatch(batch);
  }, ACTIVE_TELEMETRY_FLUSH_MS);
}
