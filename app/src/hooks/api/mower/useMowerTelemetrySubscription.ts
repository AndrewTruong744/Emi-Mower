import { useEffect, useRef } from 'react';
import { useBoundStore } from '@/store/useBoundStore';
import { subscribeToMowerTelemetry } from '@/zenoh/mowerTelemetry';
import { ACTIVE_TELEMETRY_FLUSH_MS, TelemetryBuffer } from '@/hooks/mowers/telemetryBuffer';

/** Owns the single authenticated mower telemetry subscription for the app. */
export function useMowerTelemetrySubscription() {
  const idToken = useBoundStore((state) => state.idToken);
  const mowerIds = useBoundStore((state) => state.mowers);
  const selectedMowerUuid = useBoundStore((state) => state.selectedMowerUuid);
  const appendTelemetryBatch = useBoundStore((state) => state.appendTelemetryBatch);
  const reportError = useBoundStore((state) => state.reportError);
  const bufferRef = useRef(new TelemetryBuffer());
  const selectedMowerRef = useRef(selectedMowerUuid);
  const mowerIdsRef = useRef(new Set(mowerIds));

  useEffect(() => {
    selectedMowerRef.current = selectedMowerUuid;
  }, [selectedMowerUuid]);

  useEffect(() => {
    mowerIdsRef.current = new Set(mowerIds);
  }, [mowerIds]);

  useEffect(() => {
    if (!idToken || mowerIds.length === 0) {
      bufferRef.current.clear();
      return;
    }

    let disposed = false;
    let unsubscribe: (() => Promise<void>) | undefined;
    void subscribeToMowerTelemetry(
      (messages) => {
        if (disposed) return;
        for (const { mowerId, sample } of messages) {
          if (!mowerIdsRef.current.has(mowerId)) continue;
          if (bufferRef.current.enqueue(mowerId, sample)) {
            reportError(new Error(`Telemetry queue reached its limit for mower ${mowerId}`), {
              source: 'zenoh',
              title: 'Telemetry delayed',
            });
          }
        }
      },
      (error) => reportError(error, { source: 'zenoh', title: 'Invalid telemetry received' })
    ).then((cleanup) => {
      if (disposed) void cleanup();
      else unsubscribe = cleanup;
    }).catch(() => undefined);

    const interval = setInterval(() => {
      const batch = bufferRef.current.flush(selectedMowerRef.current, Date.now());
      if (Object.keys(batch).length > 0) appendTelemetryBatch(batch);
    }, ACTIVE_TELEMETRY_FLUSH_MS);

    return () => {
      disposed = true;
      clearInterval(interval);
      bufferRef.current.clear();
      if (unsubscribe) void unsubscribe();
    };
  }, [appendTelemetryBatch, idToken, mowerIds.length, reportError]);
}
