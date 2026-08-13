import { useEffect } from 'react';
import { MOWER_TELEMETRY_INTERVAL_MS } from '@/store/slices/mowerSlice';
import { useBoundStore } from '@/store/useBoundStore';

/**
 * Temporary local telemetry source. Replace this with the live mower subscription
 * when the API hooks are available.
 */
export function useMowerTelemetrySimulator() {
  const mowerIds = useBoundStore((state) => state.mowers);
  const appendFakeTelemetry = useBoundStore((state) => state.appendFakeTelemetry);

  useEffect(() => {
    if (mowerIds.length === 0) return;

    const interval = setInterval(() => {
      mowerIds.forEach(appendFakeTelemetry);
    }, MOWER_TELEMETRY_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [appendFakeTelemetry, mowerIds]);
}
